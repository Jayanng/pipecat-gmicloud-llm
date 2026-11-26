# Models

Every model id below works through the `model` setting of `GmicloudLLMService`,
through GMI Cloud's OpenAI-compatible chat completions endpoint.

Source: live `GET /v1/models` on 2026-11-26. Count: **71 models**.
The catalog changes, GMI adds and removes models, so treat this as a snapshot
from that date, not a permanent list. Check the live list before budgeting
or relying on a specific model id.

Live verification: only two models were run end to end in a Pipecat pipeline
on 2026-11-26, `zai-org/GLM-5.3-Flash` (default) and
`deepseek-ai/deepseek-v4.1-flash-1017`. The other 69 ids are listed as
returned by the live API, not as tested.

## All 71 models

| # | Model id |
| --- | --- |
| 1 | `deepseek-ai/deepseek-v4.1-flash-1017` |
| 2 | `google/gemini-3.8-flash` |
| 3 | `zai-org/GLM-5.3-Flash` |
| 4 | `Qwen/Qwen3.8-27B` |
| 5 | `stepfun-ai/Step-3.7-Flash` |
| 6 | `google/gemini-3.7-flash` |
| 7 | `Qwen/Qwen3.8-Max` |
| 8 | `deepseek-ai/DeepSeek-V4-Flash-0731` |
| 9 | `google/gemini-3.6-flash` |
| 10 | `google/gemini-3.5-flash-lite` |
| 11 | `moonshotai/kimi-k3` |
| 12 | `openai/gpt-5.6-luna` |
| 13 | `openai/gpt-5.6-terra` |
| 14 | `openai/gpt-5.6-sol` |
| 15 | `tencent/Hy3` |
| 16 | `moonshotai/kimi-k2.7-code-highspeed` |
| 17 | `zai-org/GLM-5.2-FP8` |
| 18 | `MiniMaxAI/MiniMax-M3` |
| 19 | `Qwen/Qwen3.7-Max` |
| 20 | `google/gemini-3.5-flash` |
| 21 | `openai/gpt-5.5` |
| 22 | `deepseek-ai/DeepSeek-V4-Pro` |
| 23 | `zai-org/GLM-5.1-FP8` |
| 24 | `zai-org/GLM-5-FP8` |
| 25 | `MiniMaxAI/MiniMax-M2.7` |
| 26 | `google/gemini-3.1-flash-lite-preview` |
| 27 | `google/gemini-3.1-pro-preview` |
| 28 | `deepseek-ai/DeepSeek-V3.2` |
| 29 | `deepseek-ai/DeepSeek-V3-0324` |
| 30 | `deepseek-ai/DeepSeek-V4.1-Flash` |
| 31 | `deepseek-ai/DeepSeek-V4-Flash` |
| 32 | `deepseek-ai/deepseek-v4-flash-vision-exp` |
| 33 | `deepseek-ai/DeepSeek-V4-Pro-0813` |
| 34 | `google/gemini-3-flash-preview` |
| 35 | `google/gemini-4-argon` |
| 36 | `google/gemini-4-carbon` |
| 37 | `google/gemini-4-hydrogen` |
| 38 | `google/gemma-4-26b-a4b-it` |
| 39 | `openai/gpt-6.1-sol` |
| 40 | `openai/gpt-6-astra` |
| 41 | `openai/gpt-6-luna` |
| 42 | `openai/gpt-6-sol` |
| 43 | `xai/grok4.6` |
| 44 | `xai/grok4.7` |
| 45 | `XiaomiMiMo/MiMo-V2.6-Flash` |
| 46 | `XiaomiMiMo/MiMo-V2.6-Pro` |
| 47 | `MiniMaxAI/MiniMax-M2.5` |
| 48 | `MiniMaxAI/MiniMax-M3.1-Flash` |
| 49 | `moonshotai/Kimi-K2.5` |
| 50 | `moonshotai/kimi-k2.7-code` |
| 51 | `moonshotai/Kimi-K2-Thinking` |
| 52 | `moonshotai/kimi-k3.1-pro` |
| 53 | `nvidia/nemotron-3-ultra-550b-a55b` |
| 54 | `zai-org/GLM-4.7-FP8` |
| 55 | `Qwen/Qwen3.5-122B-A10B` |
| 56 | `Qwen/Qwen3.5-27B` |
| 57 | `Qwen/Qwen3.5-35B-A3B` |
| 58 | `Qwen/Qwen3.5-397B-A17B` |
| 59 | `Qwen/Qwen3.6-35B-A3B` |
| 60 | `Qwen/Qwen3.6-Plus` |
| 61 | `Qwen/Qwen3.6-Plus-2026-04-02` |
| 62 | `Qwen/Qwen3.8-Flash` |
| 63 | `Qwen/Qwen3.8-Max-0902` |
| 64 | `Qwen/Qwen3-235B-A22B-Instruct-2507-FP8` |
| 65 | `gmicloud/Ripple-65B-Preview` |
| 66 | `stepfun-ai/Step-5-Preview` |
| 67 | `tencent/hy3-preview` |
| 68 | `tencent/hy4` |
| 69 | `tencent/hy4-flash` |
| 70 | `tencent/hy4-preview` |
| 71 | `zai-org/GLM-5.3` |
