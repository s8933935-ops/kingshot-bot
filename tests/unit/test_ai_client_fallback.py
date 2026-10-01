"""Regression tests for the Claude-to-fast-AI fallback contract."""

import sys
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from src.bot.ai_client import generate_rag_answer


def test_claude_bridge_exception_fallback_returns_answer_and_model():
    with (
        patch("src.bot.ai_client._run_bridge_with_file", side_effect=RuntimeError("bridge down")),
        patch(
            "src.bot.ai_client.call_fast_ai",
            return_value=("GPT fallback answer", "GPT-4o-mini (OpenAI)"),
        ),
    ):
        answer, model = generate_rag_answer(
            "工場の配置について教えて", {}, use_claude=True
        )

    assert answer == "GPT fallback answer"
    assert model == "GPT-4o-mini (OpenAI)"


def test_claude_bridge_error_return_fallback_returns_answer_and_model():
    with (
        patch(
            "src.bot.ai_client._run_bridge_with_file",
            return_value=(1, "", "bridge returned error"),
        ),
        patch(
            "src.bot.ai_client.call_fast_ai",
            return_value=("Local fallback answer", "Local Qwen 14B"),
        ),
    ):
        answer, model = generate_rag_answer(
            "工場の配置について教えて", {}, use_claude=True
        )

    assert answer == "Local fallback answer"
    assert model == "Local Qwen 14B"


if __name__ == "__main__":
    for test in (
        test_claude_bridge_exception_fallback_returns_answer_and_model,
        test_claude_bridge_error_return_fallback_returns_answer_and_model,
    ):
        test()
        print(f"PASS: {test.__name__}")
