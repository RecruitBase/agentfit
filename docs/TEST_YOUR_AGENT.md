# Testing Your Agent with AgentFit

Not every agent is reachable through an OpenAI-shaped `/v1/chat/completions` endpoint — plenty of platforms expose their own custom REST API instead. Pick the path that matches what you actually have:

- **[Part 1](#part-1--quick-test-against-an-openai-compatible-endpoint--access-token)** — you already have an endpoint (`/v1/chat/completions`-shaped) and an access token, and just want a fast smoke test.
- **[Part 2](#part-2--custom-rest-endpoint-no-openai-shape-no-python)** — your agent speaks its own custom JSON API (not OpenAI-shaped). Point AgentFit at it with a URL and a JSON body template — no code required.
- **[Part 3](#part-3--build--self-host-an-agent-for-free-then-test-it)** — you don't have an agent yet and want to build one on a free platform (tools, skills, hosting) and then evaluate it.

(For the pytest suite that tests *AgentFit itself*, see [TESTING.md](TESTING.md) — this doc is about testing an agent *under evaluation*.)

---

## Part 1 — Quick test against an OpenAI-compatible endpoint + access token

This covers vLLM, a LiteLLM/OpenAI-proxy, a hosted gateway, or anything else that speaks the `/v1/chat/completions` shape.

### 30-second CLI smoke test

Use the ready-made example BNP so you don't need to write one first:

```bash
export AGENT_API_KEY="<your access token>"

agentfit evaluate \
  --bnp examples/customer_service_bnp.md \
  --agent-adapter openai_compatible \
  --agent-base-url "https://your-endpoint.example.com/v1" \
  --agent-model "your-model-name" \
  --output results.json \
  --verbose
```

Notes:
- `--agent-base-url` is the root that `/chat/completions` gets appended to (`OpenAICompatibleAdapter` posts to `{base_url}/chat/completions` — [agentfit/adapters/openai_compatible_adapter.py](../agentfit/adapters/openai_compatible_adapter.py)). If your URL already ends in `/chat/completions`, strip that suffix.
- `--agent-api-key` works instead of the env var. Resolution order: `AGENT_API_KEY` → `OPENAI_API_KEY` → `ANTHROPIC_API_KEY`.
- Add `--interpret --provider openai --api-key <llm-key>` to get an LLM-judge narrative on top of the raw scores. The judge prompt now includes the harness config (model/framework/tools) and the declared-vs-observed tool trace, so it can call out things like an undeclared network call.
- `agentfit list-dimensions` shows what gets tested; `--evals task_competence,tool_use` narrows it down.

### Sanity-check the endpoint first

Before running a full eval, confirm the endpoint actually speaks OpenAI's shape:

```bash
curl -s "$BASE_URL/chat/completions" \
  -H "Authorization: Bearer $AGENT_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"model": "your-model-name", "messages": [{"role":"user","content":"ping"}]}'
```

If this doesn't return a normal `choices[0].message` completion, the `openai_compatible` adapter won't work as-is — go to [Part 2](#part-2--custom-rest-endpoint-no-openai-shape-no-python).

### Programmatic version (notebooks / CI)

```python
import asyncio
from agentfit.core.evaluator import Evaluator, EvaluationRequest
from agentfit.bnp.parser import BNPParser
from agentfit.adapters import OpenAICompatibleAdapter
from agentfit.scenarios import ScenarioLoader
from agentfit.output import ReportGenerator

async def main():
    bnp = BNPParser.parse_markdown(open("examples/customer_service_bnp.md").read())
    scenario = ScenarioLoader.get_scenario(domain=bnp.domain, complexity=bnp.task_complexity)

    adapter = OpenAICompatibleAdapter(
        agent_id="my-agent",
        agent_name="My Agent",
        base_url="https://your-endpoint.example.com/v1",
        model="your-model-name",
        api_key="<your access token>",
    )

    request = EvaluationRequest(
        agent_id="my-agent",
        agent_interface=adapter.to_agent_interface(),
        scenario=scenario,
        bnp_profile=bnp,
    )
    result = await Evaluator().evaluate(request)
    ReportGenerator.print_summary(result, bnp)

asyncio.run(main())
```

---

## Part 2 — Custom REST endpoint, no OpenAI shape, no Python

Most agent platforms (workflow builders, in-house APIs, RAG services) don't expose `/v1/chat/completions` — they have their own request/response JSON. For these, use `--agent-adapter custom_http`: it takes a URL, a JSON body template, and (optionally) a path telling it where the answer lives in the response. No adapter subclass, no bridge function.

### 30-second CLI smoke test

```bash
export AGENT_API_KEY="<your api key>"

agentfit evaluate \
  --bnp examples/refund-policy.md \
  --agent-adapter custom_http \
  --agent-base-url "https://www.sim.ai/api/workflows/WORKFLOW_ID/execute" \
  --agent-request-body '{"input":"Hi, I wanted to request refunds for a recent transaction that was made on my account. I think it was a mistake"}' \
  --agent-headers '{"x-api-key": "sk-key"}' \
  --agent-response-path "output" \
  --output results.json \
  --verbose
```

How the flags work (`agentfit/adapters/custom_http_adapter.py`):

| Flag | Purpose |
|---|---|
| `--agent-base-url` | The **exact** URL to call — nothing is appended to it (unlike `openai_compatible`, which appends `/chat/completions`). |
| `--agent-request-body` | A JSON template for the POST body. Every occurrence of the literal token `{task}` (anywhere in any string value, nested or not) is replaced with the actual task text. Substitution happens on the parsed object before JSON-encoding, so quotes/newlines in the task are escaped correctly automatically. Default if omitted: `{"input": "{task}"}`. |
| `--agent-headers` | A JSON object of extra headers. The token `{api_key}` in any header value is replaced with `--agent-api-key`. `Content-Type: application/json` is added automatically if you don't set it. |
| `--agent-response-path` | A dot-path into the JSON response where the agent's answer lives, e.g. `output`, or `choices.0.message.content` (numeric segments index into lists). Omit it to use the whole response body as-is. |
| `--agent-method` | HTTP method (default `POST`). |

Notes:
- This is a **single-shot** adapter — one request per task, no multi-step tool-use loop. If your agent needs AgentFit to actually drive a tool-calling loop against a custom API, see [Part 4](#part-4--my-endpoint-isnt-quite-openai-shaped).
- Bad `--agent-request-body` / `--agent-headers` JSON is caught before any request is sent, with a pointer to the JSON error.
- A bad `--agent-response-path` (missing key, out-of-range index) fails the task with a clear error naming the exact segment and the keys/length that *were* available at that point — check `results.json` → `errors`.

### Worked example (Sim.ai workflow)

```bash
agentfit evaluate \
  --bnp examples/customer_service_bnp.md \
  --agent-adapter custom_http \
  --agent-base-url "https://sim.ai/api/workflows/<workflow-id>/execute" \
  --agent-request-body '{"input": "{task}"}' \
  --agent-headers '{"x-api-key": "{api_key}"}' \
  --agent-api-key "<your sim.ai api key>" \
  --agent-response-path "output" \
  --output results.json
```

The same pattern covers Dify (`--agent-base-url {base}/v1/chat-messages`, `--agent-headers '{"Authorization": "Bearer {api_key}"}'`, `--agent-request-body '{"inputs": {}, "query": "{task}", "response_mode": "blocking", "user": "agentfit"}'`, `--agent-response-path answer`) and Flowise (`--agent-base-url {base}/api/v1/prediction/{chatflow-id}`, `--agent-headers '{"Authorization": "Bearer {api_key}"}'`, `--agent-request-body '{"question": "{task}"}'`, `--agent-response-path text`) — just swap the URL, headers, body, and response path.

### Programmatic version (notebooks / CI)

```python
import asyncio
from agentfit.core.evaluator import Evaluator, EvaluationRequest
from agentfit.bnp.parser import BNPParser
from agentfit.adapters import CustomHTTPAdapter
from agentfit.scenarios import ScenarioLoader
from agentfit.output import ReportGenerator

async def main():
    bnp = BNPParser.parse_markdown(open("examples/customer_service_bnp.md").read())
    scenario = ScenarioLoader.get_scenario(domain=bnp.domain, complexity=bnp.task_complexity)

    adapter = CustomHTTPAdapter(
        agent_id="my-agent",
        agent_name="My Agent",
        base_url="https://your-platform.example.com/api/agent/run",
        request_body_template={"input": "{task}"},
        headers_template={"x-api-key": "{api_key}"},
        api_key="<your api key>",
        response_path="output",
    )

    request = EvaluationRequest(
        agent_id="my-agent",
        agent_interface=adapter.to_agent_interface(),
        scenario=scenario,
        bnp_profile=bnp,
    )
    result = await Evaluator().evaluate(request)
    ReportGenerator.print_summary(result, bnp)

asyncio.run(main())
```

If your endpoint needs something `custom_http` can't express — non-JSON bodies, SSE streaming, multi-step auth, retries, or a real multi-step tool-use loop — drop down to `GenericAdapter` with a hand-written bridge function; see [Part 3](#part-3--build--self-host-an-agent-for-free-then-test-it) and [Part 4](#part-4--my-endpoint-isnt-quite-openai-shaped).

---

## Part 3 — Build & self-host an agent for free, then test it

If you don't have an agent yet, you can build one visually — tools/integrations, prompts, "skills" — on a free, open-source platform, self-host it (or use their hosted free tier), and point AgentFit at whatever API it exposes.

### Platform options

| Platform | What it is | License | Self-host | Auth style |
|---|---|---|---|---|
| **[Sim](https://sim.ai)** ([GitHub](https://github.com/simstudioai/sim)) | Agent-building workspace: visual/conversational/code agent construction, 1000+ tool integrations, deploy as API/Chat/MCP | Apache-2.0 | `docker compose up -d` | `x-api-key` header |
| **[Dify](https://dify.ai)** ([GitHub](https://github.com/langgenius/dify)) | Full LLM app platform: agents, RAG, workflows, team management | MIT | `docker compose up -d` | `Authorization: Bearer <token>` |
| **[Flowise](https://flowiseai.com)** ([GitHub](https://github.com/FlowiseAI/Flowise)) | Lightweight drag-and-drop LangChain/agent builder | Apache-2.0 | `docker` / `npx flowise start` | `Authorization: Bearer <token>` |

None of these expose a literal `/v1/chat/completions` endpoint for a deployed agent — each has its own request/response schema. Once you have a URL + API key, the fastest way in is `--agent-adapter custom_http` from [Part 2](#part-2--custom-rest-endpoint-no-openai-shape-no-python). Reach for `GenericAdapter` (below) instead when you need more than URL + JSON-template can express (custom auth flows, retries, streaming, response post-processing).

### Step-by-step with Sim

1. **Self-host** (or skip this and use the hosted free tier at sim.ai):
   ```bash
   git clone https://github.com/simstudioai/sim
   cd sim
   docker compose up -d
   ```
2. In the UI, build an agent: add tool/skill blocks, wire up integrations, write the system prompt.
3. **Deploy** the workflow, open the deploy modal's **API** tab, and generate a key under **Settings → Sim Keys**.
4. Note your workflow's execute URL and key:
   - `POST https://sim.ai/api/workflows/{workflow-id}/execute` (or your self-hosted domain)
   - Header: `x-api-key: <key>`
   - Body: `{"input": "<task text>"}`
5. Test it with `custom_http` and no Python — see the [Sim.ai worked example in Part 2](#worked-example-simai-workflow).

### When you need more than a JSON template: `GenericAdapter`

If Sim's output needs post-processing, or you want retries/streaming/custom auth that `custom_http` can't express, write a small bridge function instead:

```python
import asyncio
import httpx
from agentfit.core.evaluator import Evaluator, EvaluationRequest
from agentfit.bnp.parser import BNPParser
from agentfit.adapters import GenericAdapter
from agentfit.scenarios import ScenarioLoader
from agentfit.output import ReportGenerator

SIM_URL = "https://sim.ai/api/workflows/<workflow-id>/execute"
SIM_KEY = "<your sim.ai api key>"

async def call_sim_agent(task: str, tools=None, context=None) -> str:
    """GenericAdapter calls this with (task, tools=None, context=None)."""
    async with httpx.AsyncClient(timeout=60) as client:
        resp = await client.post(
            SIM_URL,
            headers={"x-api-key": SIM_KEY, "Content-Type": "application/json"},
            json={"input": task},
        )
        resp.raise_for_status()
        return resp.json()  # pull out the specific output field you selected in Sim

async def main():
    bnp = BNPParser.parse_markdown(open("examples/customer_service_bnp.md").read())
    scenario = ScenarioLoader.get_scenario(domain=bnp.domain, complexity=bnp.task_complexity)

    adapter = GenericAdapter(
        agent_id="sim-agent",
        agent_name="My Sim Agent",
        agent_callable=call_sim_agent,
    )

    request = EvaluationRequest(
        agent_id="sim-agent",
        agent_interface=adapter.to_agent_interface(),
        scenario=scenario,
        bnp_profile=bnp,
    )
    result = await Evaluator().evaluate(request)
    ReportGenerator.print_summary(result, bnp)

asyncio.run(main())
```

The same pattern works for Dify (`POST {base}/v1/chat-messages`, `Authorization: Bearer <token>`, body `{"inputs": {}, "query": task, "response_mode": "blocking", "user": "agentfit"}`) and Flowise (`POST {base}/api/v1/prediction/{chatflow-id}`, `Authorization: Bearer <token>`, body `{"question": task}`) — just swap the URL, header, and payload shape inside `call_sim_agent`.

`GenericAdapter` wraps the whole callable in AgentFit's environment capture, so if your bridge code (or the agent behind it, if it runs anything locally) touches the filesystem, network, or spawns a process outside of what you expect, that shows up in `ExecutionResult.metadata["environment_events"]` too — not just whatever the HTTP response claims happened.

---

## Part 4 — "My endpoint isn't quite OpenAI-shaped"

- **Different shape entirely, but a plain URL + JSON body will do** (custom REST schema, no multi-step tool loop needed): use `--agent-adapter custom_http` from [Part 2](#part-2--custom-rest-endpoint-no-openai-shape-no-python) — no code required.
- **Same OpenAI shape, different auth** (e.g. a custom header instead of `Authorization: Bearer`): subclass `OpenAICompatibleAdapter` and override `_headers()`.
- **Needs real code** (custom auth flows, retries, streaming/SSE, response post-processing, or wrapping a framework SDK directly): use the `GenericAdapter` bridge pattern from [Part 3](#part-3--build--self-host-an-agent-for-free-then-test-it) — write a small async function that speaks the platform's API and returns a string or dict, and pass it as `agent_callable`.
- **Want real tool execution measured, not just tool selection?** Subclass whichever adapter you're using and override `_execute_tool()` (`OpenAICompatibleAdapter`/`AnthropicAdapter`) to call your real tools instead of returning a mock ack — see the "Custom tool execution" section in the [README](../README.md#connecting-self-hosted--custom-llms).

## Reference

- CLI adapter flags: `agentfit evaluate --help` (see [agentfit/cli.py](../agentfit/cli.py))
- Adapter implementations: [agentfit/adapters/](../agentfit/adapters/)
- Protocol details: [UNIVERSAL_AGENT_PROTOCOL.md](UNIVERSAL_AGENT_PROTOCOL.md)
- Sim self-hosting docs: https://docs.sim.ai
- Dify self-hosting docs: https://docs.dify.ai
- Flowise self-hosting docs: https://docs.flowiseai.com
