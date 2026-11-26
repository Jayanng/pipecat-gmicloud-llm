# Changelog

All notable changes to this project will be documented in this file.

## [0.1.0] - 2026-11-26

### Added

- `GmicloudLLMService`: Pipecat LLM service for GMI Cloud's
  OpenAI-compatible inference API (`https://api.gmi-serving.com/v1`),
  subclassing Pipecat's `OpenAILLMService`.
- Default model `zai-org/GLM-5.3-Flash`, with a default
  `max_completion_tokens` of 1000: the default model reasons before it
  answers, and its reasoning tokens count against the completion budget.
- Reasoning surfaced as Pipecat thought frames (`LLMThoughtStartFrame` /
  `LLMThoughtTextFrame` / `LLMThoughtEndFrame`); disable with
  `settings.emit_thought_frames=False`.
- Function/tool calling through Pipecat's OpenAI adapter.
- Settings (runtime-updatable): model, temperature, top_p, max_tokens,
  max_completion_tokens, emit_thought_frames, plus the standard
  `OpenAILLMSettings` fields.
- Foundational example: `examples/ask-one-question-gmicloud.py`.
- Live verification tooling: `scripts/verify_live.py` (service-class
  pipeline run) and `tests/test_live_gmicloud_llm.py` (runs only when
  `GMI_CLOUD_LIVE=1` is set). Verified against the live GMI Cloud API on
  2026-11-26; see the README for the exact runs.
