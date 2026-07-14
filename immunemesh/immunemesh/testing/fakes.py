"""
Demo-only fake models.

Every demo and benchmark in this project runs against fake/local models —
never a real LLM provider API — on purpose. See README.md "Responsible
use" for the reasoning (unauthorized-access law, data-protection law, and
third-party API terms of service all point the same direction: don't run
adversarial test payloads against a real commercial provider).
"""

from __future__ import annotations

from langchain.messages import AIMessage
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.outputs import ChatGeneration, ChatResult

from immunemesh.signals.embeddings import extract_text


class LeakySystemPromptModel(BaseChatModel):
    """Simulates a COMPROMISED agent: instead of answering normally, it
    echoes its full system prompt (canary token included) back as its
    response. Stands in for what a real prompt-injection attack tries to
    trigger in a real LLM. Only functional against itself — not a
    general-purpose attack tool.
    """

    def _generate(self, messages, stop=None, run_manager=None, **kwargs) -> ChatResult:
        leaked_content = "\n".join(extract_text(m) for m in messages if extract_text(m))
        return ChatResult(generations=[ChatGeneration(message=AIMessage(content=leaked_content))])

    @property
    def _llm_type(self) -> str:
        return "leaky-fake-chat-model"
