"""
self-healing/heal.py
1. attempt_heal() — logs when a fallback selector successfully rescued a step.
2. propose_new_selector() — last resort: asks Claude for a new selector from
   the live DOM when even fallbacks fail.
"""
from typing import Optional
import os
from datetime import datetime, timezone
import anthropic

MODEL = "claude-sonnet-4-6"


def attempt_heal(original_selector: str, healed_selector: str, action: str, success: bool) -> dict:
    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "action": action,
        "original_selector": original_selector,
        "healed_selector": healed_selector,
        "success": success,
    }


def propose_new_selector(page, original_selector: str, intent: str) -> Optional[str]:
    """
    Last-resort healing: original selector AND all known fallbacks failed.
    A human should review proposals before trusting them automatically —
    don't auto-apply this on a new client's site without a review gate.
    """
    try:
        dom_snippet = page.content()[:6000]
    except Exception:
        return None

    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

    prompt = f"""A test step failed because this selector no longer matches anything:
"{original_selector}"

The step's intent was: {intent}

Here is a trimmed snapshot of the current page HTML:
{dom_snippet}

Respond with ONLY a single CSS selector (or accessible role-based locator) that
best matches the described intent in the current HTML. If you cannot find a
confident match, respond with exactly: NONE"""

    response = client.messages.create(
        model=MODEL,
        max_tokens=200,
        messages=[{"role": "user", "content": prompt}],
    )

    text = "".join(b.text for b in response.content if b.type == "text").strip()
    return None if text == "NONE" else text