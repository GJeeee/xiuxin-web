"""命盘 → 修心建议（凤仪系行为指导，长者口吻文案）。"""
from __future__ import annotations

import datetime
from dataclasses import dataclass, field

from paipan import (
    WUXING_GAN,
    BirthInfo,
    Chart,
    _day_pillar,
    _month_branch,
    _month_pillar,
    _shishen,
    _year_pillar,
    build_chart,
)

# 地支六冲、六害、六合
LIU_CHONG = {("子", "午"), ("丑", "未"), ("寅", "申"), ("卯", "酉"), ("辰", "戌"), ("巳", "亥")}
LIU_HAI = {("子", "未"), ("丑", "午"), ("寅", "巳"), ("卯", "辰"), ("申", "亥"), ("酉", "戌")}
LIU_HE = {("子", "丑"), ("寅", "亥"), ("卯", "戌"), ("辰", "酉"), ("巳", "申"), ("午", "未")}


def _pair(a: str, b: str) -> tuple[str, str]:
    return tuple(sorted((a, b)))


def branch_relation(a: str, b: str) -> str | None:
    if a == b:
        return "伏吟"
    p = _pair(a, b)
    for x in LIU_CHONG:
        if _pair(x[0], x[1]) == p:
            return "冲"
    for x in LIU_HAI:
        if _pair(x[0], x[1]) == p:
            return "害"
    for x in LIU_HE:
        if _pair(x[0], x[1]) == p:
            return "合"
    return None


@dataclass
class AdviceBlock:
    title: str
    level: str  # 平 / 留意 / 加紧
    summary: str
    body: str
    action: str


@dataclass
class XiuxingReport:
    gender: str
    pillars: str
    day_master: str
    day_master_wx: str
    pattern: str
    true_solar_note: str
    reference_date: str
    current_dayun: str
    current_liunian: str
    current_liuyue: str
    current_day: str
    daily: AdviceBlock
    monthly: AdviceBlock
    yearly: AdviceBlock
    dayun_block: AdviceBlock
    health: AdviceBlock
    morning_motto: str
    traits: list[str] = field(default_factory=list)


def _detect_clashes(chart: Chart) -> list[str]:
    branches = [chart.year[1], chart.month[1], chart.day[1], chart.hour[1]]
    names = ["年", "月", "日", "时"]
    out = []
    for i in range(4):
        for j in range(i + 1, 4):
            r = branch_relation(branches[i], branches[j])
            if r == "冲":
                out.append(f"{names[i]}{branches[i]}↔{names[j]}{branches[j]}")
    return out


def _pattern_hint(chart: Chart) -> str:
    month_ss = chart.shishen.get("月", "")
    hour_ss = chart.shishen.get("时", "")
    parts = []
    if month_ss in ("七杀", "正官"):
        if hour_ss in ("正印", "偏印") or any("印" in x for x in chart.canggan.get("时", [])):
            parts.append("官杀有印，能担事、可成")
        else:
            parts.append("官杀透月，压力常伴，宜知退")
    elif month_ss in ("正印", "偏印"):
        parts.append("印绶为要，宜学习、养德")
    elif month_ss in ("食神", "伤官"):
        parts.append("食伤泄秀，宜表达而不争口舌")
    else:
        parts.append("凭日主本色立身，宜诚意待人")
    clashes = _detect_clashes(chart)
    if clashes:
        parts.append(f"盘中{'、'.join(clashes)}，一生多动象、宜事坏人不坏")
    return "；".join(parts)


def _health_traits(chart: Chart) -> tuple[list[str], str, str]:
    """病理倾向（非医学诊断）→ 禀性功课。"""
    dm = chart.day_master
    wx = WUXING_GAN[dm]
    traits: list[str] = []
    branches = chart.year + chart.month + chart.day + chart.hour
    wx_count = {k: 0 for k in "木火土金水"}
    for c in branches:
        if c in WUXING_GAN:
            wx_count[WUXING_GAN[c]] += 1
        # 支藏本气略计
    for br in [chart.year[1], chart.month[1], chart.day[1], chart.hour[1]]:
        from paipan import ZHI_CANG

        if ZHI_CANG[br]:
            wx_count[WUXING_GAN[ZHI_CANG[br][0]]] += 0.5

    month_ss = chart.shishen.get("月", "")
    if month_ss in ("七杀", "正官"):
        traits.append("杀气易引动：怒、顶人、争理（木火五毒）")
    if wx_count.get("水", 0) >= 2.5:
        traits.append("水偏旺：烦、多思、睡前易搅（伤肾倾向）")
    if wx_count.get("火", 0) >= 2.5:
        traits.append("火偏旺：恨、争理、心浮（伤心倾向）")
    if wx_count.get("土", 0) >= 2.5:
        traits.append("土偏重：怨、反复、闷（伤脾倾向）")
    if _detect_clashes(chart):
        traits.append("冲多：环境变动中情绪易起，宜认不是、不怨人")

    # 调候粗判
    month_br = chart.month[1]
    cold_months = "亥子丑"
    hot_months = "巳午未"
    if month_br in cold_months and wx == "火":
        traits.append("寒月火日：宜暖心，少怨、早眠")
    if month_br in hot_months and wx == "水":
        traits.append("热月水日：宜静心，少争、意回根")

    if not traits:
        traits.append("结构尚平：仍守不怨人、找好处、认不是")

    summary = "；".join(traits[:3])
    body = (
        "咱们把「病」说宽一点——不一定是身病，往往是心上有结、性上有偏。"
        "你的盘里" + summary + "。"
        "这不是判你「一定有什么病」，是提醒你：这类倾向来了，别硬扛，先化性。"
    )
    action = (
        "日常：遇烦→达全体；遇怒→认不是；遇怨→尽本分；睡前不存「他不对」过夜。"
        "健康的事该看医生还得看医生，这里说的是修心养性的路子。"
    )
    return traits, body, action


def _level_from_relations(relations: list[str]) -> str:
    if any(r in ("冲", "伏吟") for r in relations):
        return "加紧"
    if any(r in ("害",) for r in relations):
        return "留意"
    return "平"


def _elder_wrap(level: str, context: str, advice: str, action: str) -> str:
    tone = {
        "加紧": "这阵子弦绷得紧些，咱们心里先有数，不必自己吓自己。",
        "留意": "不算大凶，但宜多一分细心，少一分较劲。",
        "平": "相对宽一些，该做的做，该尽的尽。",
    }[level]
    return f"{tone}{context}{advice}"


def _daily_advice(chart: Chart, ref: datetime.date, dayun_z: str, hour_z: str) -> AdviceBlock:
    day_gz = _day_pillar(ref)
    day_z = day_gz[1]
    rels = []
    notes = []
    for label, z in [("大运", dayun_z), ("时", hour_z)]:
        r = branch_relation(day_z, z)
        if r:
            rels.append(r)
            notes.append(f"日{day_z}与{label}{z}{r}")
    level = _level_from_relations(rels)
    ctx = f"今日日柱{day_gz}。" + ("；".join(notes) + "。" if notes else "与运、时无硬冲合。")
    advice = _elder_wrap(
        level,
        ctx,
        "一日之计在于晨：心里带一句「不争理，先认不是」。",
        "遇事停半拍；就打着人家不对，我这一气算我对吗？",
    )
    return AdviceBlock("今日修心", level, ctx, advice, "STOP → 认不是 → 找一处好处")


def _monthly_advice(chart: Chart, ref: datetime.date, dayun_z: str, hour_z: str) -> AdviceBlock:
    yg = _year_pillar(datetime.datetime(ref.year, ref.month, ref.day))
    mb = _month_branch(datetime.datetime(ref.year, ref.month, ref.day))
    mgz = _month_pillar(yg[0], mb)
    mz = mgz[1]
    rels, notes = [], []
    for label, z in [("大运", dayun_z), ("时", hour_z)]:
        r = branch_relation(mz, z)
        if r:
            rels.append(r)
            notes.append(f"月{mz}与{label}{z}{r}")
    level = _level_from_relations(rels)
    ctx = f"本月流月{mgz}（{ref.year}年{ref.month}月）。" + ("；".join(notes) + "。" if notes else "")
    extra = ""
    if level == "加紧":
        extra = "这月少开新仗，重大决定多一审；能道过的关系先道过。"
    elif level == "留意":
        extra = "有磨合正常，别存 overnight 之怨；找好处比赢理要紧。"
    else:
        extra = "可推进事务，仍守「事坏人不坏」。"
    advice = _elder_wrap(level, ctx, extra, "睡前查：今日是否「半好人」——外忍内阴最耗人。")
    return AdviceBlock("本月修心", level, ctx, advice, "月干引动：尽伦常，不顶撞式争理")


def _yearly_advice(chart: Chart, ref: datetime.date, dayun_z: str) -> AdviceBlock:
    yg = _year_pillar(datetime.datetime(ref.year, 6, 15))
    yz = yg[1]
    r = branch_relation(yz, dayun_z)
    rels = [r] if r else []
    level = _level_from_relations(rels)
    ctx = f"{ref.year}流年{yg}，大运{dayun_z}。" + (f"岁运{yz}与运{dayun_z}{r}。" if r else "岁运无直接硬冲。")
    if r == "冲":
        extra = "动而承压之年，不是躺平年，也不是拼命争赢年；守心、守伦，人不丢。"
    elif r == "合":
        extra = "有合有缓，仍忌贪高争功；合作看好处，不看输赢。"
    else:
        extra = "按平常心过日子，底色仍看大运十年。"
    advice = _elder_wrap(level, ctx, extra, "全年纲领：不怨人、找好处、认不是。")
    return AdviceBlock("流年修心", level, ctx, advice, "动年守志，不丢人")


def _dayun_advice(chart: Chart, dayun_gz: str) -> AdviceBlock:
    dz = dayun_gz[1]
    branches = [chart.year[1], chart.month[1], chart.day[1], chart.hour[1]]
    rels, notes = [], []
    for i, b in enumerate(branches):
        r = branch_relation(dz, b)
        if r:
            rels.append(r)
            notes.append(f"运{dz}与{'年月日时'[i]}{b}{r}")
    level = _level_from_relations(rels) if rels else "平"
    ctx = f"当前大运{dayun_gz}。" + ("；".join(notes[:2]) + "。" if notes else "与原局无显著硬冲。")
    month_ss = chart.shishen.get("月", "")
    if month_ss in ("七杀", "正官"):
        theme = "杀印之运：宜资质、跟对人；知进退比硬顶聪明。"
    else:
        theme = "这步运宜守本分、诚意待人，大事用志、小事用意。"
    advice = _elder_wrap(level, ctx, theme, "运末之年顾后一运；穷不变志，富不动心。")
    return AdviceBlock("大运修心", level, ctx, advice, "十年一句：事坏人不坏")


def build_xiuxing_report(birth: BirthInfo, reference: datetime.date | None = None) -> XiuxingReport:
    ref = reference or datetime.date.today()
    birth_copy = BirthInfo(
        birth.year, birth.month, birth.day, birth.hour, birth.minute,
        birth.gender, birth.place, birth.use_true_solar, birth.longitude,
    )
    chart = build_chart(birth_copy)
    if chart.dayun:
        chart.dayun.reference_date = ref
        chart.dayun.current = None
        for s in chart.dayun.steps:
            if s.start_date <= ref < s.end_date:
                chart.dayun.current = s
                break
        if chart.dayun.current is None and chart.dayun.steps and ref >= chart.dayun.steps[-1].start_date:
            chart.dayun.current = chart.dayun.steps[-1]

    dayun_gz = chart.dayun.current.ganzhi if chart.dayun and chart.dayun.current else "—"
    dayun_z = dayun_gz[1] if len(dayun_gz) == 2 else "子"
    hour_z = chart.hour[1]

    yg = _year_pillar(datetime.datetime(ref.year, ref.month, ref.day))
    mb = _month_branch(datetime.datetime(ref.year, ref.month, ref.day))
    mgz = _month_pillar(yg[0], mb)
    day_gz = _day_pillar(ref)

    traits, health_body, health_action = _health_traits(chart)
    pattern = _pattern_hint(chart)

    daily = _daily_advice(chart, ref, dayun_z, hour_z)
    monthly = _monthly_advice(chart, ref, dayun_z, hour_z)
    yearly = _yearly_advice(chart, ref, dayun_z)
    dayun_block = _dayun_advice(chart, dayun_gz)

    level_order = {"加紧": 0, "留意": 1, "平": 2}
    worst = min([daily, monthly, yearly, dayun_block], key=lambda x: level_order.get(x.level, 9))
    motto_map = {
        "加紧": "今日不争理，只认不是；动中守志，不丢人。",
        "留意": "今日找一处好处，存一分宽。",
        "平": "今日尽本分，心不怨人。",
    }
    morning = motto_map.get(worst.level, motto_map["平"])

    return XiuxingReport(
        gender=chart.gender,
        pillars=f"{chart.year} {chart.month} {chart.day} {chart.hour}",
        day_master=chart.day_master,
        day_master_wx=WUXING_GAN[chart.day_master],
        pattern=pattern,
        true_solar_note=chart.true_solar_note,
        reference_date=ref.isoformat(),
        current_dayun=dayun_gz,
        current_liunian=yg,
        current_liuyue=mgz,
        current_day=day_gz,
        daily=daily,
        monthly=monthly,
        yearly=yearly,
        dayun_block=dayun_block,
        health=AdviceBlock(
            "性理与健康倾向",
            "留意" if len(traits) > 2 else "平",
            "；".join(traits),
            health_body,
            health_action,
        ),
        morning_motto=morning,
        traits=traits,
    )


def report_to_dict(r: XiuxingReport) -> dict:
    def block(b: AdviceBlock) -> dict:
        return {"title": b.title, "level": b.level, "summary": b.summary, "body": b.body, "action": b.action}

    return {
        "gender": r.gender,
        "pillars": r.pillars,
        "day_master": r.day_master,
        "day_master_wx": r.day_master_wx,
        "pattern": r.pattern,
        "true_solar_note": r.true_solar_note,
        "reference_date": r.reference_date,
        "current_dayun": r.current_dayun,
        "current_liunian": r.current_liunian,
        "current_liuyue": r.current_liuyue,
        "current_day": r.current_day,
        "morning_motto": r.morning_motto,
        "traits": r.traits,
        "daily": block(r.daily),
        "monthly": block(r.monthly),
        "yearly": block(r.yearly),
        "dayun": block(r.dayun_block),
        "health": block(r.health),
    }
