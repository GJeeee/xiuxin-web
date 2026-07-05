"""调用 OpenAI 兼容 API（默认 DeepSeek）。"""
from __future__ import annotations

import os
from pathlib import Path

import httpx

PROMPTS_DIR = Path(__file__).parent / "prompts"
RULES_DIR = Path(__file__).parent / ".cursor" / "rules"
PROMPT_PATH = PROMPTS_DIR / "liangpai.txt"
SOP_PATH = PROMPTS_DIR / "liangpai-sop.md"

# 主栈见 butaohao.mdc；叠加行为指导见 xiuxing-xingwei-sop.mdc
RULE_FILES = (
    "liang-xiangrun-ziping-sop.mdc",
    "sijiao-quanliu-xingchong-sop.mdc",
    "sijiao+xipi.mdc",
    "xiuxing-xingwei-sop.mdc",
)


def _strip_frontmatter(text: str) -> str:
    if text.startswith("---"):
        end = text.find("---", 3)
        if end != -1:
            return text[end + 3 :].lstrip("\n")
    return text


def load_rule_docs() -> str:
    parts: list[str] = []
    for name in RULE_FILES:
        path = RULES_DIR / name
        if path.is_file():
            parts.append(_strip_frontmatter(path.read_text(encoding="utf-8")))
    return "\n\n---\n\n".join(parts)


def load_system_prompt() -> str:
    """飞书机器人 system prompt = 导师人设 + 摘要 + 完整 SOP 规则栈。"""
    base = PROMPT_PATH.read_text(encoding="utf-8")
    summary_path = PROMPTS_DIR / "sijiao-stack-summary.txt"
    summary = summary_path.read_text(encoding="utf-8") if summary_path.is_file() else ""
    rules = load_rule_docs()
    parts = [base]
    if summary:
        parts.append(f"# 规则栈摘要（先读此节把握顺序）\n\n{summary}")
    if rules:
        parts.append(
            "# 完整 SOP 规则栈（与上文同等效力，必须严格执行）\n\n"
            "执行顺序：Phase 0–3（双体系）→ Q0–Q8（四角方阵全流）→ D/L/Y/M（细批终身）→ Phase 4–8 → 命理报告；"
            "有档案时追加 §行为执导（xiuxing-xingwei-sop，读 Phase3+Q8 凶吉，先冲突检测）。\n\n"
            + rules
        )
    elif SOP_PATH.is_file():
        sop = SOP_PATH.read_text(encoding="utf-8")
        parts.append(f"# 完整 SOP 规则\n\n{sop}")
    return "\n\n---\n\n".join(parts)


def chat(messages: list[dict], system: str | None = None) -> str:
    api_key = os.environ["LLM_API_KEY"]
    base_url = os.environ.get("LLM_BASE_URL", "https://api.deepseek.com/v1").rstrip("/")
    model = os.environ.get("LLM_MODEL", "deepseek-chat")

    payload = {
        "model": model,
        "messages": [{"role": "system", "content": system or load_system_prompt()}] + messages,
        "temperature": float(os.environ.get("LLM_TEMPERATURE", "0.35")),
        "max_tokens": 4096,
    }
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}

    with httpx.Client(timeout=120.0) as client:
        r = client.post(f"{base_url}/chat/completions", json=payload, headers=headers)
        if r.status_code != 200:
            # 把 DeepSeek 返回的具体错误原因带出来（余额不足/key无效/未激活等）
            try:
                err_body = r.json()
                err_msg = err_body.get("error", {}).get("message") or r.text[:300]
            except Exception:
                err_msg = r.text[:300]
            raise RuntimeError(f"LLM API {r.status_code}: {err_msg}")
        data = r.json()
        return data["choices"][0]["message"]["content"].strip()
