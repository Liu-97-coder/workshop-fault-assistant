# -*- coding: utf-8 -*-
"""
车间设备故障问答助手 —— 问答引擎（多步追问状态机）

每次收到用户的话，按这个顺序判断：
  1. 能识别出新的故障     -> 给出处理步骤，并从第 0 步开始追问
  2. 用户直接说出具体现象  -> 快捷分诊，直接给建议
  3. 匹配当前这一步的回答  -> 给出建议，并推进到下一步（对话有进展，不重复）
  4. 用户反馈"试了/还是不行" -> 引导补充现象
  5. 都没匹配             -> 用"当前这一步"的问题引导，而不是每次都问同一个问题

关键改进：助手记住走到哪一步，兜底引导也跟随进展，
所以"听不懂"时不再每次都问一模一样的第一个问题。
"""
from fault_kb import find_case, triage, _hit

FALLBACK_FIRST = (
    "我还没听明白。你能说一下是哪种设备、出现了什么现象吗？\n"
    "比如：主轴异响、液压压力上不去、电机过载、机床不启动、导轨卡滞、冷却液泄漏。"
)
GENERIC_TEMPLATE = (
    "按上面给的步骤检查后，把结果告诉我（比如灯亮不亮、有没有声音、油位够不够），"
    "我就能帮你定位到具体是哪里的问题。"
)
DONE_MESSAGE = "针对「{name}」的排查建议我已经给完了。你可以按上面的步骤检查，或换个故障继续问我。"


class FaultAssistant:
    def __init__(self):
        # session_id -> {"case": 当前案例, "step": 走到第几步(-1 表示已给完建议)}
        self.sessions = {}

    def ask(self, question, session_id="default"):
        # 1) 能识别出新故障 -> 开启/切换主题，从第 0 步开始
        case = find_case(question)
        if case is not None:
            self.sessions[session_id] = {"case": case, "step": 0}
            return case["answer"] + "\n\n" + self._question(case, 0)

        sess = self.sessions.get(session_id)
        if sess is None:
            return FALLBACK_FIRST

        case = sess["case"]
        steps = case.get("steps") or []

        # 2) 用户没等问就直接说具体现象 -> 快捷分诊（直接给建议，结束）
        t = triage(case, question)
        if t:
            sess["step"] = t["goto"]
            return t["advice"]

        # 3) 匹配当前这一步的回答 -> 给建议并推进
        if 0 <= sess["step"] < len(steps):
            for branch in steps[sess["step"]]["branches"]:
                if _hit(question, branch["keywords"]):
                    goto = branch.get("goto", -1)
                    sess["step"] = goto
                    reply = branch["advice"]
                    # 若还有下一步，顺带把下一个问题带上，让对话连贯
                    nxt = self._question(case, goto)
                    return reply + ("\n\n" + nxt if nxt else "")
            # 当前步没匹配上，也没推进，就落到兜底

        # 4) 用户反馈"试了/还是不行"
        if any(w in question for w in ["试了", "试过", "还是", "没用", "不行", "没有用", "怎么办", "怎么处理"]):
            return GENERIC_TEMPLATE

        # 5) 兜底：引用用户刚说的话 + 当前排查进度，避免每次都回同一句
        if sess["step"] == -1:
            return DONE_MESSAGE.format(name=case["name"])
        q_now = self._question(case, sess["step"]) or "直接描述一下故障现象"
        return (
            f"你说的「{question}」我还没对上号。我现在想确认：{q_now}\n"
            f"直接回 有/没有 或 是/不是，或者补设备型号/具体现象；要是换了故障，直接说故障名就行。"
        )

    @staticmethod
    def _question(case, step):
        """取第 step 步的问题文本；step 无效返回空串。"""
        steps = case.get("steps") or []
        if 0 <= step < len(steps):
            return steps[step]["question"]
        return ""
