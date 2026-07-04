#!/usr/bin/env python3
"""修心 SOP 网页服务。"""
from __future__ import annotations

import datetime
from pathlib import Path

from flask import Flask, jsonify, redirect, send_from_directory, request

from paipan import BirthInfo
from xiuxing_engine import build_xiuxing_report, report_to_dict

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


if __name__ == "__main__":
    import os

    port = int(os.environ.get("PORT", os.environ.get("WEB_PORT", "8765")))
    debug = os.environ.get("FLASK_DEBUG", "").lower() in ("1", "true", "yes")
    print(f"修心 SOP 网页：http://127.0.0.1:{port}")
    APP.run(host="0.0.0.0", port=port, debug=debug)
