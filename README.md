# pipecat-gmicloud-llm

A [Pipecat](https://github.com/pipecat-ai/pipecat) LLM service for
[GMI Cloud](https://www.gmicloud.ai)'s OpenAI-compatible inference API.
Community-maintained by [@Jayanng](https://github.com/Jayanng) (GMI Cloud
Ambassador). This is not an official GMI Cloud or Pipecat project.

One service, every text model in GMI Cloud's catalog: GLM, DeepSeek,
Gemini, Qwen and more, behind the standard OpenAI-compatible chat
completions endpoint. Drop it into any Pipecat pipeline as the LLM,
next to the [`pipecat-gmicloud`](https://github.com/Jayanng/pipecat-gmicloud)
TTS service, for a voice agent that runs entirely on GMI Cloud.

**Live verification (2026-11-26, Pipecat 1.17.0):** the default model
`zai-org/GLM-5.3-Flash` and `deepseek-ai/deepseek-v4.1-flash-1017` were
both run end to end in a Pipecat pipeline against the live GMI Cloud
API. See [Live verification](#live-verification) for the exact replies,
token counts and costs.

## Models

Any model id from GMI Cloud's `/v1/models` list works through the
`model` setting. The list returned 71 models on 2026-11-26. The full
list is in [MODELS.md](MODELS.md). Examples:

| Model id | What it is |
|---|---|
| `zai-org/GLM-5.3-Flash` (default) | Cheapest GMI text model; 1M-token context |
| `zai-org/GLM-5.3` | Full GLM-5.3 |
| `deepseek-ai/deepseek-v4.1-flash-1017` | DeepSeek flash model |
| `google/gemini-3.8-flash` | Gemini flash model |
| `Qwen/Qwen3.8-27B` | Qwen 3.8 27B |

Default-model pricing, per 1M tokens, from GMI Cloud's model library:
list $0.15 input / $0.50 output, with a promotional $0.075 / $0.25
in effect at the last check (2026-11-18). Prices change; check the
model library before budgeting.

## Installation

```bash
uv add pipecat-gmicloud-llm
```

Requires a GMI Cloud API key ([get one here](https://console.gmicloud.ai/)).

## Usage

```python
import os

from pipecat_gmicloud_llm import GmicloudLLMService

llm = GmicloudLLMService(
    api_key=os.environ["GMI_CLOUD_API_KEY"],
    settings=GmicloudLLMService.Settings(
        model="zai-org/GLM-5.3-Flash",
    ),
)

# Drop into any Pipecat pipeline:
# Pipeline([llm, transport.output()])
```

Switching models is one setting:

```python
settings=GmicloudLLMService.Settings(
    model="deepseek-ai/deepseek-v4.1-flash-1017",
)
```

### Constructor parameters

| Parameter | Default | Description |
|---|---|---|
| `api_key` | required | GMI Cloud API key |
| `base_url` | `https://api.gmi-serving.com/v1` | GMI Cloud OpenAI-compatible base URL |
| `model` | `zai-org/GLM-5.3-Flash` | Any GMI Cloud text model id (deprecated direct arg; prefer `settings`) |

### Settings (runtime-updatable)

| Setting | Default | Description |
|---|---|---|
| `model` | `zai-org/GLM-5.3-Flash` | Any GMI Cloud text model id |
| `temperature` | model default | Sampling temperature |
| `top_p` | model default | Nucleus sampling probability |
| `max_tokens` | unset | Maximum tokens (dropped when `max_completion_tokens` is set) |
| `max_completion_tokens` | `1000` | Maximum completion tokens, including reasoning tokens |
| `emit_thought_frames` | `True` | Emit reasoning as Pipecat thought frames |

### Reasoning and the token budget

The default model reasons before it answers, and its reasoning tokens
count against the completion budget. A small budget can be spent
entirely on reasoning and return an empty reply, so the service
defaults `max_completion_tokens` to 1000. Reasoning is surfaced as
Pipecat thought frames (`LLMThoughtStartFrame` /
`LLMThoughtTextFrame` / `LLMThoughtEndFrame`) instead of being silently
dropped; set `emit_thought_frames=False` to drop it.

### Function calling

Function/tool calling works through Pipecat's OpenAI adapter. Register
tools in the `LLMContext` as `FunctionSchema` objects with handlers, or
with `llm.register_function(...)`, exactly as with any OpenAI-compatible
Pipecat LLM service.

### What is not verified

- The `developer` message role: GMI's support for it has not been
  verified, so the service converts `developer` messages to `user`
  messages.
- Strict JSON-schema responses: not verified against GMI, so the service
  does not advertise response-schema support.

## Running the example

`examples/ask-one-question-gmicloud.py` asks one question through GMI
Cloud in a Pipecat pipeline and prints the streamed reply and thought
frames. No transport is needed.

```bash
uv pip install pipecat-gmicloud-llm
GMI_CLOUD_API_KEY=<your key> python examples/ask-one-question-gmicloud.py
GMI_CLOUD_API_KEY=<your key> python examples/ask-one-question-gmicloud.py \
    "What is the capital of France?" deepseek-ai/deepseek-v4.1-flash-1017
```

## Live verification

Verified against the live GMI Cloud API on 2026-11-26
(`scripts/verify_live.py`, `GMI_CLOUD_LIVE=1 python -m pytest tests/`).
Latest run, 2026-11-26:

- Default model `zai-org/GLM-5.3-Flash`, prompt "Say hello in one
  short sentence.": real streamed reply text arrived in a Pipecat
  pipeline (`LLMFullResponseStartFrame`, `LLMTextFrame`,
  `LLMFullResponseEndFrame`), with thought frames carrying the model's
  reasoning. Reply: "Hello there, it's great to meet you!". Direct
  streaming call with the same settings: 25 chunks, usage prompt 19,
  completion 53 (of which reasoning 42), total 72 tokens, cost
  $0.000029 at list prices ($0.000015 at the promotional rate).
- A function-calling run: the model called the registered `get_weather`
  tool with `{"city": "Paris"}`, the handler ran, and the model
  answered from the tool result: "The weather in Paris right now is
  **sunny with a temperature of 24°C**".
- Second model `deepseek-ai/deepseek-v4.1-flash-1017`: real streamed
  reply text arrived in a Pipecat pipeline ("Hello! It's nice to meet
  you."). Note: this model also spends reasoning tokens (74 in one
  run), but it does not always stream its reasoning as
  `reasoning_content`, so thought frames may or may not appear for it.

## Pipecat compatibility

Tested with Pipecat v1.17.0 (`pipecat-ai`).

## Notes

- The service follows Pipecat's community integration conventions
  (`OpenAILLMService` / `OpenAILLMSettings`, tracing via the base
  service, `LLMFullResponseStartFrame` / `LLMTextFrame` /
  `LLMFullResponseEndFrame`, thought frames for reasoning models,
  usage metrics).
- Attribution: this is a community-maintained integration by a GMI Cloud
  Ambassador. GMI Cloud is the service provider; this package is not
  maintained by the Pipecat team or by GMI Cloud.

## License

BSD-2-Clause, same spirit as Pipecat. See [LICENSE](LICENSE).
