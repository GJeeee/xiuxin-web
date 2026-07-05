"""梅花心易卦象算法（依梁湘润《梅花心易实战详解》）.

纯算法模块，不依赖 LLM。负责把"两个数 + 一个时辰"换算成完整的
卦象事实表：本卦 / 互卦 / 变卦 / 体用 / 五行生克 / 月令 / 应期月 / 方位。

核心规则（原书 p13–22）：
  - 先天八卦配洛书数：1乾 2兑 3离 4震 5巽 6坎 7艮 8坤；数 >8 取余。
  - 第一捏 → 下卦，第二捏 → 上卦。
  - 动爻 = (上卦数 + 下卦数 + 时辰数) % 6，余 0 当 6。
  - 动爻在哪一卦，哪一卦就是"用"；另一卦是"体"。
  - 互卦：下互 = 本卦 2,3,4 爻；上互 = 本卦 3,4,5 爻。
  - 变卦：本卦动爻阴阳互换。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Tuple

# ──────────────── 八卦静态表 ────────────────

# 先天八卦配洛书数 → 卦名
NUM_TO_NAME: dict[int, str] = {
    1: "乾", 2: "兑", 3: "离", 4: "震", 5: "巽", 6: "坎", 7: "艮", 8: "坤",
}

# 卦 → 五行
GUA_WUXING: dict[str, str] = {
    "乾": "金", "兑": "金", "离": "火", "震": "木",
    "巽": "木", "坎": "水", "艮": "土", "坤": "土",
}

# 卦 → 方位（后天八卦）
GUA_DIRECTION: dict[str, str] = {
    "坎": "北", "艮": "东北", "震": "东", "巽": "东南",
    "离": "南", "坤": "西南", "兑": "西", "乾": "西北",
}

# 卦 → 家庭角色
GUA_FAMILY: dict[str, str] = {
    "乾": "父", "坤": "母", "震": "长男", "坎": "中男", "艮": "少男",
    "巽": "长女", "离": "中女", "兑": "少女",
}

# 单卦三爻（自下而上，True=阳爻，False=阴爻）
GUA_YAO: dict[str, List[bool]] = {
    "乾": [True, True, True],     # ☰
    "兑": [True, True, False],    # ☱
    "离": [True, False, True],    # ☲
    "震": [True, False, False],   # ☳
    "巽": [False, True, True],    # ☴
    "坎": [False, True, False],   # ☵
    "艮": [False, False, True],   # ☶
    "坤": [False, False, False],  # ☷
}

# 卦符号
GUA_SYMBOL: dict[str, str] = {
    "乾": "☰", "兑": "☱", "离": "☲", "震": "☳",
    "巽": "☴", "坎": "☵", "艮": "☶", "坤": "☷",
}

# ──────────────── 64 卦名表 ────────────────
# 索引：HEX_NAMES[上卦数][下卦数] → 卦名（卦名前字=上卦象，后字=下卦象）
HEX_NAMES: dict[int, dict[int, str]] = {
    # 上乾(1)
    1: {1: "乾为天", 2: "天泽履", 3: "天火同人", 4: "天雷无妄", 5: "天风姤", 6: "天水讼", 7: "天山遁", 8: "天地否"},
    # 上兑(2)
    2: {1: "泽天夬", 2: "兑为泽", 3: "泽火革", 4: "泽雷随", 5: "泽风大过", 6: "泽水困", 7: "泽山咸", 8: "泽地萃"},
    # 上离(3)
    3: {1: "火天大有", 2: "火泽睽", 3: "离为火", 4: "火雷噬嗑", 5: "火风鼎", 6: "火水未济", 7: "火山旅", 8: "火地晋"},
    # 上震(4)
    4: {1: "雷天大壮", 2: "雷泽归妹", 3: "雷火丰", 4: "震为雷", 5: "雷风恒", 6: "雷水解", 7: "雷山小过", 8: "雷地豫"},
    # 上巽(5)
    5: {1: "风天小畜", 2: "风泽中孚", 3: "风火家人", 4: "风雷益", 5: "巽为风", 6: "风水涣", 7: "风山渐", 8: "风地观"},
    # 上坎(6)
    6: {1: "水天需", 2: "水泽节", 3: "水火既济", 4: "水雷屯", 5: "水风井", 6: "坎为水", 7: "水山蹇", 8: "水地比"},
    # 上艮(7)
    7: {1: "山天大畜", 2: "山泽损", 3: "山火贲", 4: "山雷颐", 5: "山风蛊", 6: "山水蒙", 7: "艮为山", 8: "山地剥"},
    # 上坤(8)
    8: {1: "地天泰", 2: "地泽临", 3: "地火明夷", 4: "地雷复", 5: "地风升", 6: "地水师", 7: "地山谦", 8: "坤为地"},
}

# ──────────────── 时间五行 ────────────────

# 十二时辰 → 数（原书 p17）
HOUR_TO_NUM: list[int] = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12]
HOUR_NAMES: list[str] = ["子", "丑", "寅", "卯", "辰", "巳", "午", "未", "申", "酉", "戌", "亥"]

# 地支 → 五行
BRANCH_WUXING: dict[str, str] = {
    "寅": "木", "卯": "木",
    "巳": "火", "午": "火",
    "辰": "土", "戌": "土", "丑": "土", "未": "土",
    "申": "金", "酉": "金",
    "亥": "水", "子": "水",
}

# 月份地支（农历正月建寅）
MONTH_BRANCHES: list[str] = ["寅", "卯", "辰", "巳", "午", "未", "申", "酉", "戌", "亥", "子", "丑"]

# 五行 → 旺月地支
WUXING_WANG_MONTHS: dict[str, list[str]] = {
    "木": ["寅", "卯"],
    "火": ["巳", "午"],
    "土": ["辰", "戌", "丑", "未"],
    "金": ["申", "酉"],
    "水": ["亥", "子"],
}

# 五行生克
def wuxing_relation(a: str, b: str) -> str:
    """a 对 b 的关系：a生b / a克b / b生a / b克a / 比和。"""
    if a == b:
        return "比和"
    sheng = {("木", "火"), ("火", "土"), ("土", "金"), ("金", "水"), ("水", "木")}
    ke = {("木", "土"), ("土", "水"), ("水", "火"), ("火", "金"), ("金", "木")}
    if (a, b) in sheng:
        return "生"
    if (a, b) in ke:
        return "克"
    if (b, a) in sheng:
        return "被生"
    if (b, a) in ke:
        return "被克"
    return "比和"


# ──────────────── 卦象构造 ────────────────

def num_to_gua(n: int) -> str:
    """1–8 直接对应；>8 取余（余 0 当 8）。"""
    n = n % 8
    if n == 0:
        n = 8
    return NUM_TO_NAME[n]


def hour_branch(dt: datetime) -> Tuple[str, int]:
    """根据 datetime 返回 (时辰地支, 时辰数)。以 23 点换日无需在此处理。"""
    h = dt.hour
    idx = ((h + 1) // 2) % 12  # 23-1→0(子), 1-3→1(丑)...
    return HOUR_NAMES[idx], HOUR_TO_NUM[idx]


def month_branch(dt: datetime) -> str:
    """按节气近似：以公历月份对应农历月支（近似，够用）。

    立春≈2/4, 惊蛰≈3/6, 清明≈4/5, 立夏≈5/6, 芒种≈6/6, 小暑≈7/7,
    立秋≈8/7, 白露≈9/7, 寒露≈10/8, 立冬≈11/7, 大雪≈12/7, 小寒≈1/6。
    简化：以每月 6 日为分界。
    """
    m = dt.month
    d = dt.day
    # 月支偏移：公历月 - 1 ≈ 月支序（寅=1月）
    idx = (m - 2) % 12  # 2月→寅(0)
    if d < 6:
        idx = (idx - 1) % 12
    return MONTH_BRANCHES[idx]


@dataclass
class SingleGua:
    name: str
    num: int
    wuxing: str
    direction: str
    family: str
    symbol: str
    yaos: List[bool]  # 自下而上三爻


@dataclass
class Hexagram:
    name: str               # 64卦名
    upper: SingleGua        # 上卦
    lower: SingleGua        # 下卦
    yaos: List[bool]        # 六爻自下而上（1-6）

    def yao_at(self, pos: int) -> bool:
        """pos 1-6, 自下而上。"""
        return self.yaos[pos - 1]

    def symbol(self) -> str:
        """六爻符号串（自上而下显示）。"""
        return "".join("▬" if y else "▯" for y in reversed(self.yaos))


@dataclass
class Divination:
    # 输入
    question: str
    gender: str
    grab_lower: int         # 第一捏（下卦数）
    grab_upper: int         # 第二捏（上卦数）
    dt: datetime
    # 派生
    hour_branch: str
    hour_num: int
    month_branch: str
    month_wuxing: str
    moving_line: int        # 1-6
    ben: Hexagram           # 本卦
    hu: Hexagram            # 互卦
    bian: Hexagram          # 变卦
    ti: SingleGua           # 体卦
    yong: SingleGua         # 用卦
    ti_yong_relation: str   # 体用关系（用对体：生/克/比和/被生/被克）
    ti_yong_verdict: str    # 大吉/吉/小凶/大凶/吉有力
    month_to_ti: str        # 月令对体卦关系
    aiji_joyous_months: list[str] = field(default_factory=list)  # 生体之行→旺月=转机
    aiji_bad_months: list[str] = field(default_factory=list)     # 克体之行→旺月=应凶
    lucky_directions: list[str] = field(default_factory=list)    # 生体之行所在方
    unlucky_directions: list[str] = field(default_factory=list)  # 克体之行所在方


# ──────────────── 核心 ────────────────

def _single(num: int) -> SingleGua:
    name = num_to_gua(num)
    return SingleGua(
        name=name, num=num % 8 or 8,
        wuxing=GUA_WUXING[name],
        direction=GUA_DIRECTION[name],
        family=GUA_FAMILY[name],
        symbol=GUA_SYMBOL[name],
        yaos=list(GUA_YAO[name]),
    )


def _hexagram(upper: SingleGua, lower: SingleGua) -> Hexagram:
    name = HEX_NAMES[upper.num][lower.num]
    yaos = list(lower.yaos) + list(upper.yaos)  # 自下而上 1-6
    return Hexagram(name=name, upper=upper, lower=lower, yaos=yaos)


def _hu_hexagram(ben: Hexagram) -> Hexagram:
    """互卦：下互=本卦2,3,4爻；上互=本卦3,4,5爻。"""
    y = ben.yaos  # index 0-5 对应爻 1-6
    lower_yaos = [y[1], y[2], y[3]]  # 爻2,3,4
    upper_yaos = [y[2], y[3], y[4]]  # 爻3,4,5
    lower_name = _name_from_yaos(lower_yaos)
    upper_name = _name_from_yaos(upper_yaos)
    lower = SingleGua(lower_name, _num_from_name(lower_name), GUA_WUXING[lower_name],
                      GUA_DIRECTION[lower_name], GUA_FAMILY[lower_name],
                      GUA_SYMBOL[lower_name], lower_yaos)
    upper = SingleGua(upper_name, _num_from_name(upper_name), GUA_WUXING[upper_name],
                      GUA_DIRECTION[upper_name], GUA_FAMILY[upper_name],
                      GUA_SYMBOL[upper_name], upper_yaos)
    return _hexagram(upper, lower)


def _bian_hexagram(ben: Hexagram, moving: int) -> Hexagram:
    """变卦：动爻阴阳互换。"""
    new_yaos = list(ben.yaos)
    new_yaos[moving - 1] = not new_yaos[moving - 1]
    lower_yaos = new_yaos[:3]
    upper_yaos = new_yaos[3:]
    lower_name = _name_from_yaos(lower_yaos)
    upper_name = _name_from_yaos(upper_yaos)
    lower = SingleGua(lower_name, _num_from_name(lower_name), GUA_WUXING[lower_name],
                      GUA_DIRECTION[lower_name], GUA_FAMILY[lower_name],
                      GUA_SYMBOL[lower_name], lower_yaos)
    upper = SingleGua(upper_name, _num_from_name(upper_name), GUA_WUXING[upper_name],
                      GUA_DIRECTION[upper_name], GUA_FAMILY[upper_name],
                      GUA_SYMBOL[upper_name], upper_yaos)
    return _hexagram(upper, lower)


_YAO_TO_NAME: dict[tuple, str] = {
    tuple(GUA_YAO[k]): k for k in GUA_YAO
}


def _name_from_yaos(yaos: List[bool]) -> str:
    return _YAO_TO_NAME[tuple(yaos)]


def _num_from_name(name: str) -> int:
    for n, nm in NUM_TO_NAME.items():
        if nm == name:
            return n
    return 0


# 体用生克五类断语
_TI_YONG_VERDICT = {
    "比和": "吉，有力（顺势、有人助）",
    "被生": "大吉（用生体，易成、事半功倍）",  # 用生体 → 体被生
    "克": "吉（体克用，能成但费大力、多阻）",  # 体克用
    "生": "小凶（体生用，耗泄、劳多获少）",   # 体生用
    "被克": "大凶（用克体，失败、灾祸、大损）",  # 用克体
}


def divine(question: str, gender: str, grab_lower: int, grab_upper: int,
           dt: datetime | None = None) -> Divination:
    """主入口：根据两个捏数 + 当前时间起卦。"""
    if dt is None:
        dt = datetime.now()

    hb, hn = hour_branch(dt)
    mb = month_branch(dt)
    mw = BRANCH_WUXING[mb]

    # 动爻
    total = (grab_upper % 8 or 8) + (grab_lower % 8 or 8) + hn
    moving = total % 6
    if moving == 0:
        moving = 6

    upper = _single(grab_upper)
    lower = _single(grab_lower)
    ben = _hexagram(upper, lower)
    hu = _hu_hexagram(ben)
    bian = _bian_hexagram(ben, moving)

    # 体用：动爻在哪一卦，哪一卦是用
    if moving <= 3:
        # 动爻在下卦 → 下卦是用、上卦是体
        yong, ti = lower, upper
    else:
        yong, ti = upper, lower

    # 体用关系：用对体
    rel = wuxing_relation(yong.wuxing, ti.wuxing)
    # wuxing_relation(a,b) 返回 a 对 b；这里 a=用, b=体
    # 我们要"用对体"：用生体→被生(从体视角), 用克体→被克, 体克用→克, 体生用→生, 同→比和
    # wuxing_relation(用,体): "生"=用生体, "克"=用克体, "被生"=体生用, "被克"=体克用, "比和"
    # 重新映射到体视角的断语
    if rel == "生":
        ti_yong_relation = "用生体"
        verdict = _TI_YONG_VERDICT["被生"]
    elif rel == "克":
        ti_yong_relation = "用克体"
        verdict = _TI_YONG_VERDICT["被克"]
    elif rel == "被生":
        ti_yong_relation = "体生用"
        verdict = _TI_YONG_VERDICT["生"]
    elif rel == "被克":
        ti_yong_relation = "体克用"
        verdict = _TI_YONG_VERDICT["克"]
    else:
        ti_yong_relation = "比和"
        verdict = _TI_YONG_VERDICT["比和"]

    # 月令对体
    m_rel = wuxing_relation(mw, ti.wuxing)
    if m_rel == "生":
        month_to_ti = "月令生体（体旺，吉上加吉）"
    elif m_rel == "克":
        month_to_ti = "月令克体（体衰，原本吉也打折）"
    elif m_rel == "被生":
        month_to_ti = "月令泄体（体被耗）"
    elif m_rel == "被克":
        month_to_ti = "月令受体克（月令不助体）"
    else:
        month_to_ti = "月令与体比和（体当令）"

    # 应期月：找生体之行与克体之行
    sheng_ti_xing = _find_xing_sheng(ti.wuxing)
    ke_ti_xing = _find_xing_ke(ti.wuxing)
    aiji_joyous = WUXING_WANG_MONTHS.get(sheng_ti_xing, [])
    aiji_bad = WUXING_WANG_MONTHS.get(ke_ti_xing, [])

    # 方位：生体之行所在方=吉方；克体之行所在方=凶方
    lucky_dirs = [d for g, d in GUA_DIRECTION.items() if GUA_WUXING[g] == sheng_ti_xing]
    unlucky_dirs = [d for g, d in GUA_DIRECTION.items() if GUA_WUXING[g] == ke_ti_xing]

    return Divination(
        question=question, gender=gender,
        grab_lower=grab_lower, grab_upper=grab_upper, dt=dt,
        hour_branch=hb, hour_num=hn,
        month_branch=mb, month_wuxing=mw,
        moving_line=moving,
        ben=ben, hu=hu, bian=bian,
        ti=ti, yong=yong,
        ti_yong_relation=ti_yong_relation,
        ti_yong_verdict=verdict,
        month_to_ti=month_to_ti,
        aiji_joyous_months=aiji_joyous,
        aiji_bad_months=aiji_bad,
        lucky_directions=lucky_dirs,
        unlucky_directions=unlucky_dirs,
    )


_SHENG_MAP = {"木": "火", "火": "土", "土": "金", "金": "水", "水": "木"}  # 生者→被生者
_KE_MAP = {"木": "土", "土": "水", "水": "火", "火": "金", "金": "木"}      # 克者→被克者


def _find_xing_sheng(ti_xing: str) -> str:
    """谁生体。"""
    for x, target in _SHENG_MAP.items():
        if target == ti_xing:
            return x
    return ""


def _find_xing_ke(ti_xing: str) -> str:
    """谁克体。"""
    for x, target in _KE_MAP.items():
        if target == ti_xing:
            return x
    return ""


# ──────────────── 序列化给前端/LLM ────────────────

def to_fact_table(d: Divination) -> dict:
    """结构化事实表，给前端展示 + 喂给 LLM。"""
    def sg(s: SingleGua) -> dict:
        return {"name": s.name, "num": s.num, "wuxing": s.wuxing,
                "direction": s.direction, "family": s.family, "symbol": s.symbol}
    return {
        "question": d.question,
        "gender": d.gender,
        "grab_lower": d.grab_lower,
        "grab_upper": d.grab_upper,
        "datetime": d.dt.strftime("%Y-%m-%d %H:%M"),
        "hour_branch": d.hour_branch,
        "hour_num": d.hour_num,
        "month_branch": d.month_branch,
        "month_wuxing": d.month_wuxing,
        "moving_line": d.moving_line,
        "ben": {"name": d.ben.name, "upper": sg(d.ben.upper), "lower": sg(d.ben.lower),
                "yaos": d.ben.yaos, "symbol": d.ben.symbol()},
        "hu": {"name": d.hu.name, "upper": sg(d.hu.upper), "lower": sg(d.hu.lower),
               "yaos": d.hu.yaos, "symbol": d.hu.symbol()},
        "bian": {"name": d.bian.name, "upper": sg(d.bian.upper), "lower": sg(d.bian.lower),
                 "yaos": d.bian.yaos, "symbol": d.bian.symbol()},
        "ti": sg(d.ti),
        "yong": sg(d.yong),
        "ti_yong_relation": d.ti_yong_relation,
        "ti_yong_verdict": d.ti_yong_verdict,
        "month_to_ti": d.month_to_ti,
        "aiji_joyous_months": d.aiji_joyous_months,
        "aiji_bad_months": d.aiji_bad_months,
        "lucky_directions": d.lucky_directions,
        "unlucky_directions": d.unlucky_directions,
    }


def fact_table_to_text(d: Divination) -> str:
    """给 LLM 用的纯文本事实表。"""
    f = to_fact_table(d)
    lines = [
        f"【问卦事】{f['question']}",
        f"【问卦人】{f['gender']}",
        f"【起卦时间】{f['datetime']}（{f['hour_branch']}时 / {f['month_branch']}月 {f['month_wuxing']}）",
        f"【捏米】第一捏 {f['grab_lower']} 粒 → 下卦 {f['ben']['lower']['name']}({f['ben']['lower']['wuxing']})",
        f"        第二捏 {f['grab_upper']} 粒 → 上卦 {f['ben']['upper']['name']}({f['ben']['upper']['wuxing']})",
        f"【动爻】第 {f['moving_line']} 爻动",
        f"【本卦】{f['ben']['name']}（上{f['ben']['upper']['name']}{f['ben']['upper']['wuxing']} 下{f['ben']['lower']['name']}{f['ben']['lower']['wuxing']}）",
        f"【互卦】{f['hu']['name']}（上{f['hu']['upper']['name']}{f['hu']['upper']['wuxing']} 下{f['hu']['lower']['name']}{f['hu']['lower']['wuxing']}）",
        f"【变卦】{f['bian']['name']}（上{f['bian']['upper']['name']}{f['bian']['upper']['wuxing']} 下{f['bian']['lower']['name']}{f['bian']['lower']['wuxing']}）",
        f"【体卦】{f['ti']['name']}({f['ti']['wuxing']})  代表求测者本人",
        f"【用卦】{f['yong']['name']}({f['yong']['wuxing']})  代表所问之事",
        f"【体用关系】{f['ti_yong_relation']} → {f['ti_yong_verdict']}",
        f"【月令对体】{f['month_to_ti']}",
        f"【应期·转机月】{('、'.join(f['aiji_joyous_months'])) or '无明显转机月'}",
        f"【应期·应凶月】{('、'.join(f['aiji_bad_months'])) or '无明显应凶月'}",
        f"【吉方】{'、'.join(f['lucky_directions']) or '无'}",
        f"【凶方】{'、'.join(f['unlucky_directions']) or '无'}",
    ]
    return "\n".join(lines)


# ──────────────── 自测 ────────────────

if __name__ == "__main__":
    # 用原书案例一·张先生验证：第一捏8(坤) 第二捏3(离) 午时(7) → 火地晋，上爻动
    dt = datetime(2026, 7, 5, 12, 30)  # 午时
    d = divine("测试升迁", "男", grab_lower=8, grab_upper=3, dt=dt)
    print(fact_table_to_text(d))
    print()
    assert d.ben.name == "火地晋", f"本卦错: {d.ben.name}"
    assert d.moving_line == 6, f"动爻错: {d.moving_line}"
    assert d.ti.name == "坤" and d.yong.name == "离", f"体用错: 体={d.ti.name} 用={d.yong.name}"
    assert d.ti_yong_relation == "用生体", f"体用关系错: {d.ti_yong_relation}"
    assert d.bian.name == "雷地豫", f"变卦错: {d.bian.name}"
    print("✓ 原书案例一·张先生 验证通过")
