#!/usr/bin/env python3
"""修心 SOP 网页服务。"""
from __future__ import annotations

import datetime
import os
from pathlib import Path

from flask import Flask, jsonify, redirect, send_from_directory, request

from paipan import BirthInfo
from xiuxing_engine import build_xiuxing_report, report_to_dict

import meihua as meihua_mod
from llm import chat as llm_chat

MEIHUA_PROMPT_PATH = Path(__file__).parent / "prompts" / "meihua.txt"

APP = Flask(__name__, static_folder="web/static")
STATIC_DIR = Path(__file__).parent / "web" / "static"

CITY_LONGITUDE = {
    "北京": 116.4,
    "上海": 121.5,
    "广州": 113.3,
    "深圳": 114.1,
    "成都": 104.1,
    "乌鲁木齐": 87.6,
    "伊宁": 81.28,
    "拉萨": 91.1,
    "哈尔滨": 126.6,
}


def _longitude(place: str) -> float:
    place = (place or "").strip()
    for k, v in CITY_LONGITUDE.items():
        if k in place:
            return v
    if "新疆" in place:
        return 81.28
    return 116.4


@APP.route("/")
@APP.route("/index.html")
def index():
    return send_from_directory(str(STATIC_DIR), "index.html")


@APP.route("/meihua")
@APP.route("/meihua.html")
def meihua_page():
    return send_from_directory(str(STATIC_DIR), "meihua.html")


@APP.route("/result")
def result_page():
    return redirect("/")


@APP.route("/favicon.ico")
def favicon():
    return ("", 204)


@APP.errorhandler(404)
def not_found(_e):
    """未知路径（非 API）回首页，避免 Flask 默认 404 页。"""
    if request.path.startswith("/api/"):
        return jsonify({"ok": False, "error": "接口不存在"}), 404
    return redirect("/")


@APP.route("/api/analyze", methods=["POST"])
def analyze():
    data = request.get_json(force=True)
    try:
        gender = data.get("gender", "女")
        y = int(data["year"])
        mo = int(data["month"])
        d = int(data["day"])
        h = int(data.get("hour", 12))
        mi = int(data.get("minute", 0))
        place = data.get("place", "")
        ref_str = data.get("reference_date")
        ref = datetime.date.fromisoformat(ref_str) if ref_str else datetime.date.today()
        use_solar = data.get("use_true_solar", True)
        lon = float(data["longitude"]) if data.get("longitude") else _longitude(place)

        birth = BirthInfo(y, mo, d, h, mi, gender, place, use_solar, lon)
        report = build_xiuxing_report(birth, ref)
        return jsonify({"ok": True, "data": report_to_dict(report)})
    except (KeyError, ValueError, TypeError) as e:
        return jsonify({"ok": False, "error": f"输入有误：{e}"}), 400


@APP.route("/health")
def health():
    return jsonify({"status": "ok"})


@APP.route("/api/meihua", methods=["POST"])
def meihua_divine():
    """梅花心易起卦 + LLM 解读。

    入参：{question, gender, grab_lower, grab_upper, datetime?(ISO)}
    出参：{ok, fact_table, interpretation}
    """
    data = request.get_json(force=True)
    try:
        question = (data.get("question") or "").strip()
        gender = data.get("gender", "男")
        grab_lower = int(data["grab_lower"])
        grab_upper = int(data["grab_upper"])
        dt_str = data.get("datetime")
        if dt_str:
            dt = datetime.datetime.fromisoformat(dt_str)
        else:
            dt = datetime.datetime.now()

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
            system = MEIHUA_PROMPT_PATH.read_text(encoding="utf-8")
            user_msg = f"以下是起卦得到的事实表，请据此断卦：\n\n{fact_text}"
            interpretation = llm_chat([{"role": "user", "content": user_msg}], system=system)
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


if __name__ == "__main__":
    import os

    port = int(os.environ.get("PORT", os.environ.get("WEB_PORT", "8765")))
    debug = os.environ.get("FLASK_DEBUG", "").lower() in ("1", "true", "yes")
    print(f"修心 SOP 网页：http://127.0.0.1:{port}")
    APP.run(host="0.0.0.0", port=port, debug=debug)
