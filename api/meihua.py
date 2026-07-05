"""Vercel Serverless Function: /api/meihua

纯 Python handler（不依赖 Flask），供 GitHub Pages 前端调用。
算法逻辑与本地 web_app.py 一致：起卦 (meihua.divine) → 事实表 → 调 LLM 断卦。
DeepSeek key 放在 Vercel 项目环境变量里，绝不进仓库。
"""
from http.server import BaseHTTPRequestHandler
import datetime
import importlib.util
import json
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent


def _load(name: str, filepath: Path):
    """按显式路径加载模块，避免与 api/meihua.py 同名冲突。"""
    spec = importlib.util.spec_from_file_location(name, filepath)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


meihua_mod = _load("_meihua_algo", _REPO_ROOT / "meihua.py")
_llm_mod = _load("_llm_mod", _REPO_ROOT / "llm.py")
llm_chat = _llm_mod.chat

_MEIHUA_PROMPT = (_REPO_ROOT / "prompts" / "meihua.txt").read_text(encoding="utf-8")

_ALLOWED_ORIGINS = {
    "https://gjeeeee.github.io",
    "http://127.0.0.1:9878",
    "http://localhost:9878",
}


def _cors(origin: str) -> dict:
    allow = origin if origin in _ALLOWED_ORIGINS else "*"
    return {
        "Access-Control-Allow-Origin": allow,
        "Access-Control-Allow-Methods": "POST, OPTIONS",
        "Access-Control-Allow-Headers": "Content-Type",
        "Vary": "Origin",
    }


def _divine_once(data: dict) -> tuple:
    """返回 (status, payload)。与 web_app.py 同逻辑。"""
    question = (data.get("question") or "").strip()
    gender = data.get("gender", "男")
    grab_lower = int(data["grab_lower"])
    grab_upper = int(data["grab_upper"])
    dt_str = data.get("datetime")
    dt = datetime.datetime.fromisoformat(dt_str) if dt_str else datetime.datetime.now()

    if not question:
        return 400, {"ok": False, "error": "请填写问卦事"}
    if grab_lower <= 0 or grab_upper <= 0:
        return 400, {"ok": False, "error": "捏米数必须大于 0"}

    div = meihua_mod.divine(question, gender, grab_lower, grab_upper, dt)
    fact = meihua_mod.to_fact_table(div)
    fact_text = meihua_mod.fact_table_to_text(div)

    interpretation = None
    interp_error = None
    try:
        user_msg = f"以下是起卦得到的事实表，请据此断卦：\n\n{fact_text}"
        interpretation = llm_chat([{"role": "user", "content": user_msg}], system=_MEIHUA_PROMPT)
    except Exception as e:
        interp_error = f"老先生过卦失败：{e}（卦象与事实表仍可参考）"

    return 200, {
        "ok": True,
        "fact_table": fact,
        "interpretation": interpretation,
        "interp_error": interp_error,
    }


class handler(BaseHTTPRequestHandler):
    def do_OPTIONS(self):
        origin = self.headers.get("Origin", "")
        self.send_response(204)
        for k, v in _cors(origin).items():
            self.send_header(k, v)
        self.end_headers()

    def do_POST(self):
        origin = self.headers.get("Origin", "")
        length = int(self.headers.get("Content-Length", 0) or 0)
        raw = self.rfile.read(length) if length else b""
        try:
            data = json.loads(raw.decode("utf-8")) if raw else {}
        except Exception:
            self._send(400, {"ok": False, "error": "请求体不是合法 JSON"}, origin)
            return
        try:
            status, payload = _divine_once(data)
            self._send(status, payload, origin)
        except (KeyError, ValueError, TypeError) as e:
            self._send(400, {"ok": False, "error": f"输入有误：{e}"}, origin)
        except Exception as e:
            self._send(500, {"ok": False, "error": f"断卦失败：{e}"}, origin)

    def _send(self, status, payload, origin):
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        for k, v in _cors(origin).items():
            self.send_header(k, v)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *args):
        pass
