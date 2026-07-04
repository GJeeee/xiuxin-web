"""简易四柱排盘（梁派教学用，含节气换月、五虎五鼠遁、大运起运）。"""
from __future__ import annotations

import datetime
from dataclasses import dataclass, field

TIAN_GAN = list("甲乙丙丁戊己庚辛壬癸")
DI_ZHI = list("子丑寅卯辰巳午未申酉戌亥")

# 1984 甲子年为基准
BASE_YEAR = 1984

WUXING_GAN = {
    "甲": "木", "乙": "木", "丙": "火", "丁": "火", "戊": "土",
    "己": "土", "庚": "金", "辛": "金", "壬": "水", "癸": "水",
}

# 支藏天干（本气优先）
ZHI_CANG = {
    "子": ["癸"], "丑": ["己", "癸", "辛"], "寅": ["甲", "丙", "戊"],
    "卯": ["乙"], "辰": ["戊", "乙", "癸"], "巳": ["丙", "庚", "戊"],
    "午": ["丁", "己"], "未": ["己", "丁", "乙"], "申": ["庚", "壬", "戊"],
    "酉": ["辛"], "戌": ["戊", "辛", "丁"], "亥": ["壬", "甲"],
}

# 五虎遁：年干 -> 正月天干序号偏移
WU_HU = {
    "甲": 2, "己": 2, "乙": 4, "庚": 4, "丙": 6, "辛": 6,
    "丁": 8, "壬": 8, "戊": 0, "癸": 0,
}

# 五鼠遁：日干 -> 子时天干序号
WU_SHU = {
    "甲": 0, "己": 0, "乙": 2, "庚": 2, "丙": 4, "辛": 4,
    "丁": 6, "壬": 6, "戊": 8, "癸": 8,
}

# 1980-2035 立春（近似，排盘够用）
LI_CHUN = {
    y: datetime.datetime(y, 2, 4 if y % 4 else 3, 4, 0)
    for y in range(1980, 2036)
}

JIE_QI_MONTH = [
    (2, 4, "寅"), (3, 6, "卯"), (4, 5, "辰"), (5, 6, "巳"),
    (6, 6, "午"), (7, 7, "未"), (8, 8, "申"), (9, 8, "酉"),
    (10, 8, "戌"), (11, 7, "亥"), (12, 7, "子"), (1, 6, "丑"),
]

# 十二「节」（起运用；不含中气）。近似日，与 JIE_QI_MONTH 月支对应。
# (月, 日, 名称)
JIE_TERMS = [
    (1, 6, "小寒"), (2, 4, "立春"), (3, 6, "惊蛰"), (4, 5, "清明"),
    (5, 6, "立夏"), (6, 6, "芒种"), (7, 7, "小暑"), (8, 8, "立秋"),
    (9, 8, "白露"), (10, 8, "寒露"), (11, 7, "立冬"), (12, 7, "大雪"),
]

# 2000-01-01 = 戊午日
BASE_DAY = datetime.date(2000, 1, 1)
BASE_DAY_IDX = 54


@dataclass
class BirthInfo:
    year: int
    month: int
    day: int
    hour: int
    minute: int = 0
    gender: str = "女"
    place: str = ""
    use_true_solar: bool = True
    longitude: float = 81.28  # 伊宁默认


@dataclass
class DayunStep:
    """一步大运（十年）。"""
    index: int  # 1-based
    ganzhi: str
    start_date: datetime.date
    end_date: datetime.date
    start_age: float  # 虚岁近似（足岁 + 1 的常用教学口径可再标注）


@dataclass
class DayunInfo:
    direction: str  # 顺行 / 逆行
    qiyun_years: int
    qiyun_months: int
    qiyun_days: int
    qiyun_date: datetime.date
    steps: list[DayunStep] = field(default_factory=list)
    current: DayunStep | None = None
    reference_date: datetime.date = field(default_factory=datetime.date.today)


@dataclass
class Chart:
    year: str
    month: str
    day: str
    hour: str
    day_master: str
    gender: str
    true_solar_note: str
    shishen: dict
    canggan: dict
    dayun: DayunInfo | None = None
    birth_datetime: datetime.datetime | None = None


def _gz(idx: int) -> str:
    idx %= 60
    return TIAN_GAN[idx % 10] + DI_ZHI[idx % 12]


def _year_pillar(dt: datetime.datetime) -> str:
    y = dt.year
    if dt < LI_CHUN.get(y, datetime.datetime(y, 2, 4)):
        y -= 1
    return _gz(y - BASE_YEAR)


def _month_branch(dt: datetime.datetime) -> str:
    y, m, d = dt.year, dt.month, dt.day
    # 简化节气边界
    boundaries = [
        (y, 1, 6, "丑"), (y, 2, 4, "寅"), (y, 3, 6, "卯"), (y, 4, 5, "辰"),
        (y, 5, 6, "巳"), (y, 6, 6, "午"), (y, 7, 7, "未"), (y, 8, 8, "申"),
        (y, 9, 8, "酉"), (y, 10, 8, "戌"), (y, 11, 7, "亥"), (y, 12, 7, "子"),
    ]
    cur = datetime.datetime(y, m, d, dt.hour, dt.minute)
    branch = "丑"
    for by, bm, bd, br in boundaries:
        if cur >= datetime.datetime(by, bm, bd, 0, 0):
            branch = br
    return branch


def _month_pillar(year_gan: str, month_branch: str) -> str:
    start = WU_HU[year_gan]
    offset = (DI_ZHI.index(month_branch) - DI_ZHI.index("寅")) % 12
    idx = (start + offset) % 10
    return TIAN_GAN[idx] + month_branch


def _day_pillar(dt: datetime.date) -> str:
    delta = (dt - BASE_DAY).days
    return _gz(BASE_DAY_IDX + delta)


def _hour_branch(hour: int, minute: int) -> str:
    t = hour + minute / 60
    if t >= 23 or t < 1:
        return "子"
    if t < 3:
        return "丑"
    if t < 5:
        return "寅"
    if t < 7:
        return "卯"
    if t < 9:
        return "辰"
    if t < 11:
        return "巳"
    if t < 13:
        return "午"
    if t < 15:
        return "未"
    if t < 17:
        return "申"
    if t < 19:
        return "酉"
    if t < 21:
        return "戌"
    return "亥"


def _hour_pillar(day_gan: str, hour_branch: str) -> str:
    start = WU_SHU[day_gan]
    idx = (start + DI_ZHI.index(hour_branch)) % 10
    return TIAN_GAN[idx] + hour_branch


def _shishen(day_gan: str, other_gan: str) -> str:
    dm = day_gan
    og = other_gan
    dm_wx = WUXING_GAN[dm]
    og_wx = WUXING_GAN[og]
    same_yin_yang = (TIAN_GAN.index(dm) % 2) == (TIAN_GAN.index(og) % 2)
    order = ["木", "火", "土", "金", "水"]
    dm_i, og_i = order.index(dm_wx), order.index(og_wx)

    if dm_wx == og_wx:
        return "比肩" if same_yin_yang else "劫财"
    if (og_i - dm_i) % 5 == 1:
        return "食神" if same_yin_yang else "伤官"
    if (og_i - dm_i) % 5 == 2:
        return "偏财" if same_yin_yang else "正财"
    if (og_i - dm_i) % 5 == 4:
        return "偏印" if same_yin_yang else "正印"
    if (og_i - dm_i) % 5 == 3:
        return "七杀" if same_yin_yang else "正官"
    return "?"


def apply_true_solar(dt: datetime.datetime, longitude: float) -> tuple[datetime.datetime, str]:
    corr_min = (longitude - 120) * 4
    true_dt = dt + datetime.timedelta(minutes=corr_min)
    note = (
        f"北京时间 {dt.strftime('%Y-%m-%d %H:%M')}，"
        f"真太阳时 {true_dt.strftime('%Y-%m-%d %H:%M')}（经度修正 {corr_min:.0f} 分钟）"
    )
    return true_dt, note


def _gz_index(gz: str) -> int:
    gi, zi = TIAN_GAN.index(gz[0]), DI_ZHI.index(gz[1])
    for n in range(60):
        if n % 10 == gi and n % 12 == zi:
            return n
    raise ValueError(f"invalid ganzhi: {gz}")


def _is_yang_gan(gan: str) -> bool:
    return TIAN_GAN.index(gan) % 2 == 0


def _dayun_forward(gender: str, year_gan: str) -> bool:
    """阳男阴女顺行，阴男阳女逆行。"""
    yang_year = _is_yang_gan(year_gan)
    male = gender == "男"
    return (male and yang_year) or (not male and not yang_year)


def _jie_datetime(year: int, month: int, day: int) -> datetime.datetime:
    return datetime.datetime(year, month, day, 0, 0)


def _iter_jie_near(birth: datetime.datetime, span_years: int = 1) -> list[datetime.datetime]:
    """出生年前后各 span_years 内的全部「节」时刻（升序）。"""
    out: list[datetime.datetime] = []
    for y in range(birth.year - span_years, birth.year + span_years + 1):
        for mo, d, _ in JIE_TERMS:
            try:
                out.append(_jie_datetime(y, mo, d))
            except ValueError:
                continue
    out.sort()
    return out


def _days_to_qiyun(birth: datetime.datetime, forward: bool) -> float:
    """出生到顺/逆方向最近「节」的天数（含小数）。"""
    jies = _iter_jie_near(birth)
    if forward:
        for j in jies:
            if j > birth:
                return (j - birth).total_seconds() / 86400
    else:
        for j in reversed(jies):
            if j < birth:
                return (birth - j).total_seconds() / 86400
    return 0.0


def _qiyun_age_parts(days: float) -> tuple[int, int, int]:
    """3天=1岁，1天=4个月；返回 (年, 月, 日余)。"""
    whole = int(days)
    years = whole // 3
    rem = whole % 3
    months = rem * 4
    frac_days = int(round((days - whole) * 30))  # 余数小时折算成日，仅用于展示
    return years, months, frac_days


def _add_years_months(d: datetime.date, years: int, months: int) -> datetime.date:
    m = d.month - 1 + months
    y = d.year + years + m // 12
    m = m % 12 + 1
    day = min(d.day, [31, 29 if y % 4 == 0 and (y % 100 != 0 or y % 400 == 0) else 28,
                      31, 30, 31, 30, 31, 31, 30, 31, 30, 31][m - 1])
    return datetime.date(y, m, day)


def compute_dayun(
    birth: datetime.datetime,
    month_pillar: str,
    year_pillar: str,
    gender: str,
    *,
    reference: datetime.date | None = None,
    count: int = 8,
) -> DayunInfo:
    """排大运：起运岁数 + 各步起止日期 + 当前大运。"""
    forward = _dayun_forward(gender, year_pillar[0])
    days = _days_to_qiyun(birth, forward)
    qy, qm, qd = _qiyun_age_parts(days)
    qiyun_date = _add_years_months(birth.date(), qy, qm)

    direction = "顺行" if forward else "逆行"
    step_delta = 1 if forward else -1
    start_idx = _gz_index(month_pillar) + step_delta

    ref = reference or datetime.date.today()
    steps: list[DayunStep] = []
    cur_start = qiyun_date
    start_age_years = qy + qm / 12.0

    for i in range(count):
        gz = _gz(start_idx + i * step_delta)
        end = _add_years_months(cur_start, 10, 0)
        age_at_start = start_age_years + i * 10
        steps.append(
            DayunStep(
                index=i + 1,
                ganzhi=gz,
                start_date=cur_start,
                end_date=end,
                start_age=round(age_at_start, 1),
            )
        )
        cur_start = end

    current = None
    for s in steps:
        if s.start_date <= ref < s.end_date:
            current = s
            break
    if current is None and steps and ref >= steps[-1].start_date:
        current = steps[-1]

    return DayunInfo(
        direction=direction,
        qiyun_years=qy,
        qiyun_months=qm,
        qiyun_days=qd,
        qiyun_date=qiyun_date,
        steps=steps,
        current=current,
        reference_date=ref,
    )


def dayun_summary(dayun: DayunInfo) -> str:
    lines = [
        f"大运：{dayun.direction}（程序计算，分析时不得自行改算年份）",
        f"起运：{dayun.qiyun_years}岁{dayun.qiyun_months}个月，交运日 {dayun.qiyun_date.isoformat()}",
        "大运列表（起年≈交运年，每步十年）：",
    ]
    for s in dayun.steps:
        flag = " ← 当前" if dayun.current and s.index == dayun.current.index else ""
        lines.append(
            f"  {s.index}. {s.ganzhi}：{s.start_date.year}–{s.end_date.year - 1} "
            f"（{s.start_date.isoformat()} 起，约 {s.start_age:.0f} 岁起）{flag}"
        )
    if dayun.current:
        c = dayun.current
        lines.append(
            f"当前大运（截至 {dayun.reference_date.isoformat()}）：{c.ganzhi}，"
            f"{c.start_date.year}–{c.end_date.year - 1}"
        )
    return "\n".join(lines)


def build_chart(birth: BirthInfo) -> Chart:
    dt = datetime.datetime(birth.year, birth.month, birth.day, birth.hour, birth.minute)
    note = "未启用真太阳时校正"
    if birth.use_true_solar and birth.longitude:
        dt, note = apply_true_solar(dt, birth.longitude)

    year = _year_pillar(dt)
    mb = _month_branch(dt)
    month = _month_pillar(year[0], mb)
    day = _day_pillar(dt.date())
    hb = _hour_branch(dt.hour, dt.minute)
    hour = _hour_pillar(day[0], hb)
    dm = day[0]

    pillars = {"年": year, "月": month, "日": day, "时": hour}
    shishen = {k: _shishen(dm, v[0]) for k, v in pillars.items()}
    canggan = {}
    for k, v in pillars.items():
        canggan[k] = [f"{g}({_shishen(dm, g)})" for g in ZHI_CANG[v[1]]]

    dayun = compute_dayun(dt, month, year, birth.gender)

    return Chart(
        year=year,
        month=month,
        day=day,
        hour=hour,
        day_master=dm,
        gender=birth.gender,
        true_solar_note=note,
        shishen=shishen,
        canggan=canggan,
        dayun=dayun,
        birth_datetime=dt,
    )


def chart_summary(chart: Chart, birth: BirthInfo) -> str:
    lines = [
        f"性别：{chart.gender}",
        f"出生地：{birth.place or '未填'}",
        chart.true_solar_note,
        f"四柱：{chart.year} {chart.month} {chart.day} {chart.hour}",
        f"日主：{chart.day_master}（{WUXING_GAN[chart.day_master]}）",
        "天干十神：" + " | ".join(f"{k}{chart.shishen[k]}" for k in "年月日"),
        "支藏：" + " | ".join(f"{k}[{', '.join(chart.canggan[k])}]" for k in "年月日时"),
    ]
    if chart.dayun:
        lines.append("")
        lines.append(dayun_summary(chart.dayun))
    return "\n".join(lines)


def parse_birth_command(text: str) -> BirthInfo | None:
    """解析：档案 女 1986-04-22 15:00 新疆伊宁"""
    import re

    m = re.search(
        r"档案\s*(男|女)\s*(\d{4})[-/年](\d{1,2})[-/月](\d{1,2})日?\s*(\d{1,2})[:：时](\d{0,2})?\s*(.*)?",
        text.strip(),
    )
    if not m:
        return None
    gender, y, mo, d, h, mi, place = m.groups()
    return BirthInfo(
        year=int(y),
        month=int(mo),
        day=int(d),
        hour=int(h),
        minute=int(mi or 0),
        gender=gender,
        place=(place or "").strip(),
        use_true_solar=True,
        longitude=81.28 if "伊宁" in (place or "") or "新疆" in (place or "") else 116.4,
    )
