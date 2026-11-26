#
# Copyright (c) 2026, Jayanng
#
# SPDX-License-Identifier: BSD 2-Clause License
#

"""Live tests for GmicloudLLMService against the real GMI Cloud API.

Runs only when ``GMI_CLOUD_LIVE=1`` is set. Each test spends a few hundred tokens on
the live API (default model list price $0.15/M input, $0.50/M output;
currently $0.075/$0.25 promotional on GMI). The key is resolved by
``tests/live_key.py`` and is never printed.
"""

import os

import pytest

from pipecat.adapters.llm.schemas.function_schema import FunctionSchema
import asyncio

from pipecat.frames.frames import (
    EndFrame,
    LLMContextFrame,
    LLMFullResponseEndFrame,
    LLMFullResponseStartFrame,
    LLMTextFrame,
    LLMThoughtTextFrame,
)
from pipecat.pipeline.pipeline import Pipeline
from pipecat.pipeline.worker import PipelineWorker
from pipecat.processors.frame_processor import FrameDirection, FrameProcessor
from pipecat.workers.runner import WorkerRunner
from pipecat.processors.aggregators.llm_context import LLMContext
from pipecat.tests.utils import run_test

from pipecat_gmicloud_llm import GmicloudLLMService
from tests.live_key import resolve_live_api_key

pytestmark = pytest.mark.skipif(
    os.environ.get("GMI_CLOUD_LIVE") != "1",
    reason="live tests need GMI_CLOUD_LIVE=1",
)


def _reply_text(frames):
    return "".join(f.text for f in frames if isinstance(f, LLMTextFrame))


def _thought_text(frames):
    return "".join(f.text for f in frames if isinstance(f, LLMThoughtTextFrame))




@pytest.mark.asyncio
async def test_live_default_model_replies():
    """Default model returns real streamed reply text, not an empty reply."""
    api_key = resolve_live_api_key()
    assert api_key, "no live GMI Cloud key available"
    llm = GmicloudLLMService(api_key=api_key)
    context = LLMContext(
        [{"role": "user", "content": "Say hello in one short sentence."}]
    )
    # The frame sequence is asserted loosely: thought frames may appear
    # between the start and end frames, so check the sequence by type.
    down, _ = await run_test(
        llm, frames_to_send=[LLMContextFrame(context)], send_end_frame=True
    )
    types = [type(f).__name__ for f in down]
    # The service also broadcasts a metadata frame at pipeline start.
    assert "LLMFullResponseStartFrame" in types
    assert "LLMFullResponseEndFrame" in types
    start_at = types.index("LLMFullResponseStartFrame")
    end_at = types.index("LLMFullResponseEndFrame")
    first_text_at = next(
        i for i, f in enumerate(down) if isinstance(f, LLMTextFrame)
    )
    assert start_at < first_text_at < end_at
    assert any(isinstance(f, LLMTextFrame) for f in down)
    reply = _reply_text(down)
    assert reply.strip(), "live reply text was empty"
    print(f"\nLIVE default-model reply: {reply!r}")
    print(f"LIVE default-model thought: {_thought_text(down)!r}")


@pytest.mark.asyncio
async def test_live_thought_frames_emitted():
    """The default reasoning model surfaces reasoning as thought frames."""
    api_key = resolve_live_api_key()
    assert api_key, "no live GMI Cloud key available"
    llm = GmicloudLLMService(api_key=api_key)
    context = LLMContext(
        [{"role": "user", "content": "What is 17 plus 25? Answer in one short sentence."}]
    )
    down, _ = await run_test(
        llm, frames_to_send=[LLMContextFrame(context)], send_end_frame=True
    )
    assert _thought_text(down).strip(), "no thought frames arrived from the live model"
    assert _reply_text(down).strip()


@pytest.mark.asyncio
async def test_live_tool_call():
    """Function calling works through the OpenAI adapter.

    Turn 1: the model calls the registered get_weather tool and the
    handler runs. The tool result is then appended to the context the
    way a Pipecat context aggregator would record it (this test pipeline
    has no aggregator, so the append is explicit), and turn 2 sends the
    context again: the model answers from the tool result. In a real
    pipeline the aggregator records the result and re-triggers the LLM.
    """
    api_key = resolve_live_api_key()
    assert api_key, "no live GMI Cloud key available"

    calls = []

    async def get_weather(params):
        calls.append((params.tool_call_id, params.arguments))
        await params.result_callback("sunny, 24C")

    llm = GmicloudLLMService(api_key=api_key)
    context = LLMContext(
        [
            {
                "role": "user",
                "content": "What is the weather in Paris right now? Use the get_weather tool.",
            }
        ],
        tools=[
            FunctionSchema(
                name="get_weather",
                description="Get the current weather for a city.",
                properties={
                    "city": {"type": "string", "description": "City name."},
                },
                required=["city"],
                handler=get_weather,
            )
        ],
    )

    seen: list = []
    first_turn_done = asyncio.Event()

    class CollectSink(FrameProcessor):
        async def process_frame(self, frame, direction: FrameDirection):
            await super().process_frame(frame, direction)
            seen.append(frame)
            if isinstance(frame, LLMFullResponseEndFrame) and not first_turn_done.is_set():
                first_turn_done.set()
            # Push onward: the worker only counts the pipeline as started
            # once the StartFrame reaches the end.
            await self.push_frame(frame, direction)

    worker = PipelineWorker(
        Pipeline([llm, CollectSink()]), cancel_on_idle_timeout=False
    )
    runner = WorkerRunner()
    await runner.add_workers(worker)

    started = asyncio.Event()

    @worker.event_handler("on_pipeline_started")
    async def _on_pipeline_started(worker, frame):
        started.set()

    async def drive():
        await started.wait()
        await worker.queue_frame(LLMContextFrame(context))
        await asyncio.wait_for(first_turn_done.wait(), timeout=120)
        assert calls, "the live model never called get_weather"
        tool_call_id, arguments = calls[0]
        assert arguments.get("city"), f"tool call had no city: {arguments}"
        # Record the call and its result in the context, as a Pipecat
        # context aggregator would, then run a second turn.
        import json as _json

        context.add_message(
            {
                "role": "assistant",
                "content": None,
                "tool_calls": [
                    {
                        "id": tool_call_id,
                        "type": "function",
                        "function": {
                            "name": "get_weather",
                            "arguments": _json.dumps(arguments),
                        },
                    }
                ],
            }
        )
        context.add_message(
            {"role": "tool", "tool_call_id": tool_call_id, "content": "sunny, 24C"}
        )
        first_turn_done.clear()
        await worker.queue_frames([LLMContextFrame(context), EndFrame()])

    task = asyncio.create_task(drive())
    await runner.run()
    await asyncio.wait_for(task, timeout=180)
    reply = _reply_text(seen)
    assert reply.strip(), "no reply text after the tool result"
    assert "sunny" in reply.lower() or "24" in reply, f"reply did not use the tool result: {reply!r}"
    print(f"\nLIVE tool call: {calls[0]}, reply: {reply!r}")


@pytest.mark.asyncio
async def test_live_second_model_replies():
    """A second catalog model also returns a real reply through the pipeline."""
    api_key = resolve_live_api_key()
    assert api_key, "no live GMI Cloud key available"
    llm = GmicloudLLMService(
        api_key=api_key,
        settings=GmicloudLLMService.Settings(
            model="deepseek-ai/deepseek-v4.1-flash-1017"
        ),
    )
    context = LLMContext(
        [{"role": "user", "content": "Say hello in one short sentence."}]
    )
    down, _ = await run_test(
        llm, frames_to_send=[LLMContextFrame(context)], send_end_frame=True
    )
    reply = _reply_text(down)
    assert reply.strip(), "live reply text was empty for the second model"
    print(f"\nLIVE second-model reply: {reply!r}")
    print(f"LIVE second-model thought: {_thought_text(down)!r}")
