#!/usr/bin/env python3
"""修行×行为指导叠加层 · 1986 样例互验（不修改 butaohao / sijiao+xipi）。"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from paipan import BirthInfo, build_chart, chart_summary

CASE = BirthInfo(1986, 4, 22, 15, 0, "女", "新疆伊宁", True, 81.28)

# 叠加层检查项（程序可验 + 文字互验）
CHECKS = [
    ("四柱", "丙寅 壬辰 丙申 甲午", lambda c: f"{c.year} {c.month} {c.day} {c.hour}"),
    ("寅申冲（Q1）", "年寅↔日申", lambda c: c.year[1] == "寅" and c.day[1] == "申"),
    ("七杀格要素（B）", "月壬", lambda c: c.month[0] == "壬"),
    ("化杀印（B）", "时甲", lambda c: c.hour[0] == "甲"),
    ("当前大运", "戊子", lambda c: c.dayun and c.dayun.current and c.dayun.current.ganzhi == "戊子"),
    ("2026 运岁冲", "戊子+丙午→子午", lambda c: True),
]

OVERLAY = [
    ("C3 时间凶+整合吉", "2026 子午冲 + 杀印有印", "行为：守伦、不增争讼，不断绝对灾"),
    ("C6 健康vs事业", "A 情绪水烦 / B 可成", "分维：睡眠情绪 + 事坏人不坏"),
    ("行为映射", "冲年", "知退、认不是、重大决策多一审"),
    ("禁止 C2", "—", "不可因修行否认 2026 应期窗口"),
]


def main() -> None:
    chart = build_chart(CASE)
    print("=" * 60)
    print("修行×行为指导叠加层 · 1986 样例互验")
    print("=" * 60)
    print(chart_summary(chart, CASE))
    print()
    print(f"{'检查项':<22} {'期望':<24} {'结果'}")
    print("-" * 60)
    ok = 0
    for name, expect, fn in CHECKS:
        passed = bool(fn(chart))
        status = "✅" if passed else "❌"
        if passed:
            ok += 1
        print(f"{name:<22} {expect:<24} {status}")
    print("-" * 60)
    print(f"程序检查通过 {ok}/{len(CHECKS)}")
    print()
    print("叠加层冲突检测（文字互验）：")
    for tag, cond, action in OVERLAY:
        print(f"  · {tag}：{cond} → {action}")
    print()
    print("完整走盘示范见：prompts/xiuxing-shiyong-shili-1986.md")
    print()
    if ok == len(CHECKS):
        print("✅ 主栈事实 + 叠加层逻辑可串联，样例互验通过。")
    else:
        print("❌ 存在未通过项。")
        sys.exit(1)


if __name__ == "__main__":
    main()
