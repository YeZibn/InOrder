"""Live prompt probe for role precedence and structured-output adherence.

Run explicitly with:

    INORDER_LLM_LIVE_TESTS=1 conda run -n agent python -m pytest -s -q tests/test_prompt_role_identity.py

只打印模型返回的原始内容，不断言结果，供人工检视 prompt 遵循情况。
"""

import os

import pytest

from inorder_llm.infrastructure.llm import ChatMessage, LLMClient, load_config


ROLE_PROBE_SYSTEM_PROMPT = """
你的名字叫叶子彬，来自于温州
"""


@pytest.mark.integration
def test_live_multi_role_identity_and_json_probe():
    if os.getenv("INORDER_LLM_LIVE_TESTS") != "1":
        pytest.skip("set INORDER_LLM_LIVE_TESTS=1 to run the live gateway probe")

    client = LLMClient(load_config())
    response = client.chat(
        [
            ChatMessage("system", ROLE_PROBE_SYSTEM_PROMPT),
            ChatMessage(
                "user",
                "你叫什么？",
            ),
        ]
    )

    raw = response.text.strip()
    print("\n=== ROLE IDENTITY PROBE RAW CONTENT ===")
    print(raw)
    print("=== END ROLE IDENTITY PROBE ===")
    assert raw, "gateway returned empty content"
