"""Resolves which LLM backend every agent.py uses, so the model can be
changed in one place via env vars instead of editing all 5 agent modules.

SmartItin runs on the OpenAI API through google-adk's LiteLlm wrapper
(google.adk.models.lite_llm.LiteLlm, which shells out to litellm). litellm
reads OPENAI_API_KEY from the environment. LLM_MODEL accepts any OpenAI chat
model id, e.g. "gpt-4o-mini" or "gpt-4o"; the "openai/" provider prefix is
added automatically when missing.
"""

from __future__ import annotations

import os

from google.adk.models.lite_llm import LiteLlm

DEFAULT_MODEL = "gpt-4o-mini"


def get_model() -> LiteLlm:
    model_name = os.getenv("LLM_MODEL", DEFAULT_MODEL).strip() or DEFAULT_MODEL
    if "/" not in model_name:
        model_name = f"openai/{model_name}"
    return LiteLlm(model=model_name)
