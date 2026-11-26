#
# Copyright (c) 2026, Jayanng
#
# SPDX-License-Identifier: BSD 2-Clause License
#

"""Unit tests for GmicloudLLMService. No API key and no network needed."""

import pytest

from pipecat_gmicloud_llm.llm import (
    DEFAULT_BASE_URL,
    DEFAULT_MAX_COMPLETION_TOKENS,
    DEFAULT_MODEL,
    _ReasoningStream,
    _reasoning_text,
    GmicloudLLMService,
)


def test_defaults():
    """Defaults match the documented GMI Cloud setup."""
    llm = GmicloudLLMService(api_key="test-key")
    assert llm._settings.model == DEFAULT_MODEL == "zai-org/GLM-5.3-Flash"
    assert llm._settings.max_completion_tokens == DEFAULT_MAX_COMPLETION_TOKENS == 1000
    assert llm._settings.emit_thought_frames is True
    assert str(llm._client.base_url).rstrip("/") == DEFAULT_BASE_URL
    assert llm.supports_developer_role is False
    assert llm.supports_response_schema is False
    assert llm.can_generate_metrics() is True


def test_api_key_required():
    """The service refuses to start without a key, so a key is never sent to the wrong host."""
    with pytest.raises(ValueError, match="requires an api_key"):
        GmicloudLLMService(api_key="")


def test_settings_override():
    """Caller settings win over the defaults."""
    llm = GmicloudLLMService(
        api_key="test-key",
        settings=GmicloudLLMService.Settings(
            model="deepseek-ai/deepseek-v4.1-flash-1017",
            temperature=0.2,
            emit_thought_frames=False,
        ),
    )
    assert llm._settings.model == "deepseek-ai/deepseek-v4.1-flash-1017"
    assert llm._settings.temperature == 0.2
    assert llm._settings.emit_thought_frames is False
    # Untouched defaults stay in place.
    assert llm._settings.max_completion_tokens == 1000


def test_reasoning_text_from_delta_attribute():
    """Reasoning is read from the delta's reasoning_content attribute."""

    class Delta:
        reasoning_content = "let me think"

    assert _reasoning_text(Delta()) == "let me think"


def test_reasoning_text_from_model_extra():
    """Reasoning is read from model_extra when the SDK puts it there."""

    class Delta:
        reasoning_content = None
        model_extra = {"reasoning_content": "from extra"}

    assert _reasoning_text(Delta()) == "from extra"


def test_reasoning_text_empty_when_absent():
    """A delta with no reasoning yields an empty string."""

    class Delta:
        pass

    assert _reasoning_text(Delta()) == ""


class _FakeDelta:
    def __init__(self, content=None, reasoning_content=None):
        self.content = content
        self.reasoning_content = reasoning_content


class _FakeChoice:
    def __init__(self, delta):
        self.delta = delta


class _FakeChunk:
    def __init__(self, delta):
        self.choices = [_FakeChoice(delta)]
        self.usage = None
        self.model = None


class _FakeStream:
    def __init__(self, chunks):
        self._chunks = chunks
        self.closed = False

    def __aiter__(self):
        return self._iter()

    async def _iter(self):
        for chunk in self._chunks:
            yield chunk

    async def close(self):
        self.closed = True


class _RecordingService:
    """Minimal stand-in for the service's push_frame."""

    def __init__(self):
        self.frames = []

    async def push_frame(self, frame):
        self.frames.append(frame)


@pytest.mark.asyncio
async def test_reasoning_stream_emits_thought_frames():
    """Reasoning chunks become thought frames; answer text passes through."""
    from pipecat.frames.frames import (
        LLMThoughtEndFrame,
        LLMThoughtStartFrame,
        LLMThoughtTextFrame,
    )

    service = _RecordingService()
    chunks = [
        _FakeChunk(_FakeDelta(reasoning_content="first thought ")),
        _FakeChunk(_FakeDelta(reasoning_content="second thought")),
        _FakeChunk(_FakeDelta(content="Hello!")),
    ]
    stream = _ReasoningStream(service, _FakeStream(chunks))

    seen = [chunk async for chunk in stream]
    await stream.close()

    assert len(seen) == 3
    thought_text = "".join(
        f.text for f in service.frames if isinstance(f, LLMThoughtTextFrame)
    )
    assert thought_text == "first thought second thought"
    assert any(isinstance(f, LLMThoughtStartFrame) for f in service.frames)
    assert any(isinstance(f, LLMThoughtEndFrame) for f in service.frames)
    # Thought frames close before the answer chunk is yielded.
    assert isinstance(service.frames[-1], LLMThoughtEndFrame)
