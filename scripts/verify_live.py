#
# Copyright (c) 2026, Jayanng
#
# SPDX-License-Identifier: BSD 2-Clause License
#

"""Live verification harness for GmicloudLLMService.

Runs the service end to end in a Pipecat pipeline against the live GMI
Cloud API and prints the streamed reply, the thought frames, and the
token usage. Also runs a direct streaming call with the same settings so
the exact token counts and cost are on record.

The API key is resolved the same way as the live tests: from
``GMI_CLOUD_API_KEY`` when set, otherwise from the registered
``custom.gmi-cloud`` credential at runtime. The key is never printed.

Usage:

    $ GMI_CLOUD_LIVE=1 python scripts/verify_live.py
    $ GMI_CLOUD_LIVE=1 python scripts/verify_live.py deepseek-ai/deepseek-v4.1-flash-1017
"""

import asyncio
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "tests"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from pipecat.frames.frames import (
    LLMContextFrame,
    LLMTextFrame,
    LLMThoughtTextFrame,
)
from pipecat.processors.aggregators.llm_context import LLMContext
from pipecat.tests.utils import run_test

from pipecat_gmicloud_llm import GmicloudLLMService
from live_key import resolve_live_api_key

# GMI list prices, per 1M tokens (GMI model library; promotional rates
# were $0.075/$0.25 at last check, 2026-11-18). Kept here only to turn
# the usage the API reports into a dollar figure.
LIST_PRICE = {
    "zai-org/GLM-5.3-Flash": (0.15, 0.50),
    "deepseek-ai/deepseek-v4.1-flash-1017": (None, None),
}


async def main() -> int:
    model = sys.argv[1] if len(sys.argv) > 1 else "zai-org/GLM-5.3-Flash"
    api_key = resolve_live_api_key()
    if not api_key:
        print("ERROR: no live GMI Cloud key available", file=sys.stderr)
        return 2

    question = "Say hello in one short sentence."
    llm = GmicloudLLMService(
        api_key=api_key,
        settings=GmicloudLLMService.Settings(model=model),
    )

    # 1. Service-class pipeline run.
    context = LLMContext([{"role": "user", "content": question}])
    down, _ = await run_test(
        llm, frames_to_send=[LLMContextFrame(context)], send_end_frame=True
    )
    reply = "".join(f.text for f in down if isinstance(f, LLMTextFrame))
    thought = "".join(f.text for f in down if isinstance(f, LLMThoughtTextFrame))
    frames = [type(f).__name__ for f in down]
    print(f"OK pipeline [{model}]: frames={frames}")
    print(f"OK pipeline [{model}]: reply={reply!r}")
    print(f"OK pipeline [{model}]: thought={thought!r}")
    if not reply.strip():
        print("ERROR: pipeline reply was empty")
        return 1

    # 2. Direct streaming call, same model and budget, for exact usage.
    from openai import AsyncOpenAI

    client = AsyncOpenAI(api_key=api_key, base_url="https://api.gmi-serving.com/v1")
    stream = await client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": question}],
        stream=True,
        stream_options={"include_usage": True},
        max_completion_tokens=1000,
    )
    streamed = ""
    usage = None
    chunks = 0
    async for chunk in stream:
        chunks += 1
        if chunk.usage:
            usage = chunk.usage
        for choice in chunk.choices:
            if choice.delta.content:
                streamed += choice.delta.content
    print(f"OK direct [{model}]: {chunks} chunks, streamed={streamed!r}")
    if usage is not None:
        prompt = usage.prompt_tokens
        completion = usage.completion_tokens
        reasoning = (
            usage.completion_tokens_details.reasoning_tokens
            if usage.completion_tokens_details
            else None
        )
        print(
            f"OK direct [{model}]: usage prompt={prompt} completion={completion} "
            f"reasoning={reasoning} total={usage.total_tokens}"
        )
        in_price, out_price = LIST_PRICE.get(model, (None, None))
        if in_price is not None:
            cost = prompt * in_price / 1_000_000 + completion * out_price / 1_000_000
            print(f"OK direct [{model}]: cost at list prices = ${cost:.6f}")
    if not streamed.strip():
        print("ERROR: direct streamed reply was empty")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
