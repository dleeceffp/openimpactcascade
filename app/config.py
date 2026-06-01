import os

# Anthropic Claude model selection (env-overridable; do not hardcode elsewhere).
OIC_MODEL       = os.getenv("OIC_MODEL", "claude-sonnet-4-6")     # default workhorse
OIC_MODEL_FAST  = os.getenv("OIC_MODEL_FAST", "claude-haiku-4-5") # cheap subtasks
OIC_MODEL_DEEP  = os.getenv("OIC_MODEL_DEEP", "claude-opus-4-7")  # premium deep analysis

# Prompt caching toggle (on by default; lets us disable for debugging).
ENABLE_PROMPT_CACHE = os.getenv("OIC_PROMPT_CACHE", "1") == "1"

def build_system(system_prompt: str, cache: bool = True) -> list[dict]:
    """Return the `system` argument as a content-block list, with prompt caching
    enabled by default. Caching a static system prompt bills cached input at ~10%."""
    block = {"type": "text", "text": system_prompt}
    if cache and ENABLE_PROMPT_CACHE:
        block["cache_control"] = {"type": "ephemeral"}
    return [block]
