#
# Copyright (c) 2026, Jayanng
#
# SPDX-License-Identifier: BSD 2-Clause License
#

"""Ask one question through GMI Cloud, in a Pipecat pipeline.

The foundational example for pipecat-gmicloud-llm: a minimal Pipecat
pipeline that sends one question to a GMI Cloud language model and prints
the streamed reply. No transport is needed; the question is queued as an
LLMContextFrame and the reply frames are printed by the sink.

Requires the GMI_CLOUD_API_KEY environment variable.

Usage:

    $ uv pip install pipecat-gmicloud-llm
    $ GMI_CLOUD_API_KEY=<your key> python examples/ask-one-question-gmicloud.py
    $ GMI_CLOUD_API_KEY=<your key> python examples/ask-one-question-gmicloud.py \\
        "What is the capital of France?" deepseek-ai/deepseek-v4.1-flash-1017
"""

import asyncio
import os
import sys

from pipecat.frames.frames import (
    EndFrame,
    LLMContextFrame,
    LLMFullResponseEndFrame,
    LLMFullResponseStartFrame,
    LLMTextFrame,
    LLMThoughtEndFrame,
    LLMThoughtStartFrame,
    LLMThoughtTextFrame,
)
from pipecat.pipeline.pipeline import Pipeline
from pipecat.pipeline.worker import PipelineWorker
from pipecat.processors.aggregators.llm_context import LLMContext
from pipecat.processors.frame_processor import FrameDirection, FrameProcessor
from pipecat.workers.runner import WorkerRunner

from pipecat_gmicloud_llm import GmicloudLLMService


class PrintSink(FrameProcessor):
    """Pipeline sink that prints LLM reply and thought frames."""

    async def process_frame(self, frame, direction: FrameDirection):
        """Print reply text and thought text as frames arrive."""
        await super().process_frame(frame, direction)
        if isinstance(frame, LLMFullResponseStartFrame):
            print("\n--- reply ---")
        elif isinstance(frame, LLMTextFrame):
            print(frame.text, end="", flush=True)
        elif isinstance(frame, LLMThoughtStartFrame):
            print("\n--- thinking ---")
        elif isinstance(frame, LLMThoughtTextFrame):
            print(frame.text, end="", flush=True)
        elif isinstance(frame, LLMThoughtEndFrame):
            print("\n--- end of thinking ---")
        elif isinstance(frame, LLMFullResponseEndFrame):
            print("\n--- end of reply ---")
        # A sink still pushes frames onward: the worker only counts the
        # pipeline as started once the StartFrame reaches the end.
        await self.push_frame(frame, direction)


async def main() -> int:
    api_key = os.environ.get("GMI_CLOUD_API_KEY")
    if not api_key:
        print("GMI_CLOUD_API_KEY is not set", file=sys.stderr)
        return 2

    question = sys.argv[1] if len(sys.argv) > 1 else "Say hello in one short sentence."
    model = sys.argv[2] if len(sys.argv) > 2 else None

    settings_kwargs = {}
    if model:
        settings_kwargs["model"] = model

    llm = GmicloudLLMService(
        api_key=api_key,
        settings=GmicloudLLMService.Settings(**settings_kwargs),
    )
    print(f"Model: {llm._settings.model}")

    pipeline = Pipeline([llm, PrintSink()])
    worker = PipelineWorker(pipeline, cancel_on_idle_timeout=False)
    runner = WorkerRunner()
    await runner.add_workers(worker)

    started = asyncio.Event()

    @worker.event_handler("on_pipeline_started")
    async def _on_pipeline_started(worker, frame):
        started.set()

    async def run():
        await started.wait()
        context = LLMContext([{"role": "user", "content": question}])
        await worker.queue_frames([LLMContextFrame(context), EndFrame()])

    task = asyncio.create_task(run())
    await runner.run()
    await asyncio.wait_for(task, timeout=120)
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
