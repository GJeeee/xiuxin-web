"""Vercel Flask 入口：/api/meihua

作为 Vercel 的 Flask entrypoint 部署。算法逻辑与本地 web_app.py 一致：
起卦 (meihua.divine) → 事实表 → 调 LLM 断卦 (llm.chat) → 返回 JSON。

DeepSeek key 放在 Vercel 项目环境变量里，绝不进仓库。
"""
import datetime
import importlib.util
import os
import sys
from pathlib import Path

from flask import Flask, jsonify, request

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

# 允许的前端来源（GitHub Pages + 本地调试）
_ALLOWED_ORIGINS = {
    "https://gjeeeee.github.io",
    "http://127.0.0.1:9878",
    "http://localhost:9878",
}

app = Flask(__name__)


@app.after_request
def add_cors(resp):
    origin = request.headers.get("Origin", "")
    allow = origin if origin in _ALLOWED_ORIGINS else "*"
    resp.headers["Access-Control-Allow-Origin"] = allow
    resp.headers["Access-Control-Allow-Methods"] = "POST, OPTIONS"
    resp.headers["Access-Control-Allow-Headers"] = "Content-Type"
    resp.headers["Vary"] = "Origin"
    return resp


@app.route("/api/meihua", methods=["POST", "OPTIONS"])
def meihua_api():
    if request.method == "OPTIONS":
        return ("", 204)

    data = request.get_json(force=True, silent=True) or {}
    try:
        question = (data.get("question") or "").strip()
        gender = data.get("gender", "男")
        grab_lower = int(data["grab_lower"])
        grab_upper = int(data["grab_upper"])
        dt_str = data.get("datetime")
        dt = datetime.datetime.fromisoformat(dt_str) if dt_str else datetime.datetime.now()

        if not question:
            return jsonify({"ok": False, "error": "请填写问卦事"}), 400
        if grab_lower <= 0 or grab_upper <= 0:
            return jsonify({"ok": False, "error": "捏米数必须大于 0"}), 400

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

        return jsonify({
            "ok": True,
            "fact_table": fact,
            "interpretation": interpretation,
            "interp_error": interp_error,
        })
    except (KeyError, ValueError, TypeError) as e:
        return jsonify({"ok": False, "error": f"输入有误：{e}"}), 400
    except Exception as e:
        return jsonify({"ok": False, "error": f"断卦失败：{e}"}), 500


@app.route("/", methods=["GET"])
def health():
    return jsonify({"status": "ok", "service": "meihua-api"})


if __name__ == "__main__":
    app.run()
