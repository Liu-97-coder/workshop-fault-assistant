# -*- coding: utf-8 -*-
"""
车间设备故障问答助手 —— 网页服务

运行：  python app.py
然后浏览器打开  http://localhost:8000  即可使用。

用 Python 自带库实现，不需要装 Flask 等任何东西。
"""
import json
import os
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from qa import FaultAssistant

WEB_ROOT = os.path.join(os.path.dirname(__file__), "static")
assistant = FaultAssistant()  # 全局唯一的问答引擎（跨请求共享会话）

PORT = 8000


class Handler(BaseHTTPRequestHandler):
    # ---- 页面 ----
    def do_GET(self):
        if self.path in ("/", "/index.html"):
            self._send_file("index.html")
        else:
            self.send_error(404)

    # ---- 问答接口 ----
    def do_POST(self):
        if self.path == "/api/ask":
            length = int(self.headers.get("Content-Length", 0))
            body = json.loads(self.rfile.read(length) or b"{}")
            question = (body.get("question") or "").strip()
            session_id = body.get("session_id") or "default"

            answer = assistant.ask(question, session_id)
            self._send_json({"answer": answer, "session_id": session_id})
        else:
            self.send_error(404)

    # ---- 工具 ----
    def _send_file(self, name):
        path = os.path.join(WEB_ROOT, name)
        with open(path, "rb") as f:
            data = f.read()
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _send_json(self, obj):
        data = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, *args):
        pass  # 安静一点，不刷屏


def main():
    server = ThreadingHTTPServer(("0.0.0.0", PORT), Handler)
    print("车间设备故障问答助手已启动")
    print(f"在浏览器打开：  http://localhost:{PORT}")
    print("按 Ctrl+C 停止")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n已停止")


if __name__ == "__main__":
    main()
