#
# Copyright (c) 2026, Jayanng
#
# SPDX-License-Identifier: BSD 2-Clause License
#

"""GMI Cloud LLM service for Pipecat.

An OpenAI-compatible LLM service for `GMI Cloud
<https://www.gmicloud.ai>`_'s inference engine, following the pattern of
Pipecat's own OpenAI-compatible services (for example
:class:`pipecat.services.xai.llm.GrokLLMService`).

Two GMI behaviours are handled here rather than left to callers:

* GMI's default model, ``zai-org/GLM-5.3-Flash``, reasons before it
  answers. Its reasoning tokens count against the completion budget, so a
  small budget can be spent entirely on reasoning and return an empty
  reply. The service therefore defaults ``max_completion_tokens`` to 1000
  and surfaces the model's reasoning as Pipecat thought frames
  (``LLMThoughtStartFrame`` / ``LLMThoughtTextFrame`` /
  ``LLMThoughtEndFrame``) instead of silently dropping it.
* GMI's OpenAI-compatible endpoint has not been verified to support the
  ``developer`` message role or strict JSON-schema responses, so the
  service converts ``developer`` messages to ``user`` messages and does
  not advertise response-schema support.
"""

from dataclasses import dataclass, field
from typing import Any

from openai import NOT_GIVEN as OPENAI_NOT_GIVEN

from pipecat.adapters.llm.services.open_ai_adapter import OpenAILLMInvocationParams
from pipecat.frames.frames import (
    LLMThoughtEndFrame,
    LLMThoughtStartFrame,
    LLMThoughtTextFrame,
)
from pipecat.services.openai.base_llm import BaseOpenAILLMService
from pipecat.services.openai.llm import OpenAILLMService
from pipecat.utils.types import NOT_GIVEN, is_given

DEFAULT_BASE_URL = "https://api.gmi-serving.com/v1"
DEFAULT_MODEL = "zai-org/GLM-5.3-Flash"
DEFAULT_MAX_COMPLETION_TOKENS = 1000


def _reasoning_text(payload: Any) -> str:
    """Reasoning from a completion delta, under either field name.

    GMI streams reasoning in ``reasoning_content`` on the choice delta.
    The OpenAI SDK may surface it as a delta attribute or inside
    ``model_extra``; both are checked.

    Args:
        payload: A streaming choice delta (or message).

    Returns:
        The reasoning text, or an empty string when there is none.
    """
    for name in ("reasoning_content", "reasoning"):
        value = getattr(payload, name, None)
        if isinstance(value, str) and value:
            return value
    model_extra = getattr(payload, "model_extra", None)
    if isinstance(model_extra, dict):
        for name in ("reasoning_content", "reasoning"):
            value = model_extra.get(name)
            if isinstance(value, str) and value:
                return value
    return ""


@dataclass
class GmicloudLLMSettings(BaseOpenAILLMService.Settings):
    """Settings for GmicloudLLMService.

    Parameters:
        emit_thought_frames: Emit the model's reasoning as Pipecat thought
            frames (``LLMThoughtStartFrame`` / ``LLMThoughtTextFrame`` /
            ``LLMThoughtEndFrame``). Defaults to True. Set to False to drop
            reasoning silently.
    """

    emit_thought_frames: bool = field(default=True)


class _ReasoningStream:
    """Async stream wrapper that turns reasoning chunks into thought frames.

    Wraps the stream returned by ``AsyncOpenAI`` so the base service's
    ``_process_context`` keeps its own tool-call and text handling
    untouched. Reasoning chunks carry no answer text, so the base service
    ignores them; this wrapper pushes thought frames for them as they
    arrive, opening the thought on the first reasoning chunk and closing
    it when answer text, a tool call, or the end of the stream arrives.
    """

    def __init__(self, service: "GmicloudLLMService", stream: Any):
        """Initialize the wrapper.

        Args:
            service: The owning service, used to push thought frames.
            stream: The underlying ``AsyncStream[ChatCompletionChunk]``.
        """
        self._service = service
        self._stream = stream
        self._thought_open = False

    def __aiter__(self):
        """Iterate the wrapped stream, emitting thought frames as needed."""
        return self._iterate()

    async def _iterate(self):
        try:
            async for chunk in self._stream:
                reasoning = ""
                if chunk.choices:
                    reasoning = _reasoning_text(chunk.choices[0].delta)
                if reasoning:
                    if not self._thought_open:
                        self._thought_open = True
                        await self._service.push_frame(LLMThoughtStartFrame())
                    await self._service.push_frame(LLMThoughtTextFrame(text=reasoning))
                else:
                    await self._close_thought()
                yield chunk
        finally:
            await self._close_thought()

    async def _close_thought(self):
        if self._thought_open:
            self._thought_open = False
            await self._service.push_frame(LLMThoughtEndFrame())

    async def close(self):
        """Close the underlying stream."""
        await self._close_thought()
        close = getattr(self._stream, "close", None)
        if callable(close):
            result = close()
            if result is not None:
                await result

    async def aclose(self):
        """Close the underlying stream (async alias for ``close``)."""
        await self.close()


class GmicloudLLMService(OpenAILLMService):
    """A Pipecat LLM service for GMI Cloud's OpenAI-compatible API.

    Connects to ``https://api.gmi-serving.com/v1`` with a GMI Cloud API
    key and runs any model in GMI Cloud's catalog. The default model is
    ``zai-org/GLM-5.3-Flash``.
    """

    Settings = GmicloudLLMSettings
    _settings: Settings

    # OpenAILLMService does not require a key (the OpenAI client falls
    # back to OPENAI_API_KEY), but for a non-OpenAI provider that fallback
    # would send the user's OpenAI key to GMI Cloud. Require a key here.
    _requires_api_key = True

    # GMI's support for the "developer" role has not been verified, so the
    # adapter converts developer messages to user messages.
    supports_developer_role: bool = False
    # Strict JSON-schema responses have not been verified against GMI.
    supports_response_schema: bool = False

    def __init__(
        self,
        *,
api_key: str,
        base_url: str = DEFAULT_BASE_URL,
        model: str | None = None,
        settings: Settings | None = None,
        **kwargs,
    ):
        """Initialize the GmicloudLLMService.

        Args:
api_key: GMI Cloud API key.
            base_url: GMI Cloud OpenAI-compatible base URL. Defaults to
                ``https://api.gmi-serving.com/v1``.
            model: The model identifier to use. Defaults to
                ``zai-org/GLM-5.3-Flash``.

                .. deprecated:: 0.0.105
                    Use ``settings=GmicloudLLMService.Settings(model=...)``
                    instead. Will be removed in 2.0.0.

            settings: Runtime-updatable settings. When provided alongside
                deprecated parameters, ``settings`` values take precedence.
            **kwargs: Additional arguments passed to the parent service.
        """
        # 1. Defaults. The 1000-token completion budget matters: the
        # default model reasons before answering, and its reasoning tokens
        # count against the budget. A small budget can be spent entirely
        # on reasoning and return an empty reply.
        default_settings = self.Settings(
            model=DEFAULT_MODEL,
            system_instruction=None,
            frequency_penalty=OPENAI_NOT_GIVEN,
            presence_penalty=OPENAI_NOT_GIVEN,
            seed=OPENAI_NOT_GIVEN,
            temperature=OPENAI_NOT_GIVEN,
            top_p=OPENAI_NOT_GIVEN,
            top_k=None,
            max_tokens=OPENAI_NOT_GIVEN,
            max_completion_tokens=DEFAULT_MAX_COMPLETION_TOKENS,
            filter_incomplete_user_turns=False,
            user_turn_completion_config=None,
            extra={},
            emit_thought_frames=True,
        )

        # 2. Direct init arg override (deprecated).
        if model is not None:
            self._warn_init_param_moved_to_settings("model", "model")
            default_settings.model = model

        # 3. Apply settings delta (canonical API, always wins).
        if settings is not None:
            default_settings.apply_update(settings)

        super().__init__(api_key=api_key, base_url=base_url, settings=default_settings, **kwargs)

    def build_chat_completion_params(
        self, params_from_context: OpenAILLMInvocationParams
    ) -> dict[str, Any]:
        """Build the chat completion request parameters.

        The base parameters are kept, except that ``max_tokens`` is dropped
        whenever ``max_completion_tokens`` is set: GMI's models count
        reasoning against the completion budget, and sending both limits
        risks the older one cutting the reply short.

        Args:
            params_from_context: Parameters derived from the LLM context
                (messages, tools, tool choice).

        Returns:
            The request parameters for the chat completion call.
        """
        params = super().build_chat_completion_params(params_from_context)

        if is_given(self._settings.max_completion_tokens) and (
            self._settings.max_completion_tokens is not None
        ):
            params["max_tokens"] = OPENAI_NOT_GIVEN

        return params

    async def get_chat_completions(self, context):  # type: ignore[override]
        """Get streaming chat completions, with reasoning as thought frames.

        The base implementation's stream is wrapped so reasoning chunks
        become Pipecat thought frames. Text and tool calls are handled by
        the base service exactly as before. When
        ``settings.emit_thought_frames`` is False, the raw stream is
        returned unchanged and reasoning is dropped.

        Args:
            context: The LLM context containing conversation history.

        Returns:
            An async stream of chat completion chunks.
        """
        stream = await super().get_chat_completions(context)
        if not self._settings.emit_thought_frames:
            return stream
        return _ReasoningStream(self, stream)

    def can_generate_metrics(self) -> bool:
        """Check if this service can generate processing metrics.

        Returns:
            True, as this service supports metrics generation.
        """
        return True
