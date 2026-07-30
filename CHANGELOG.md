# Changelog

All notable changes to AgentFit will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.3.0] - 2026-07-30

### Added
- **Loop testing** (`--enable-loop`): simulated multi-turn conversation evaluation.
  - `agentfit/loop/persona.py` — markdown persona parsing (`PersonaParser`) and `CustomerSimulator`, the LLM that roleplays the customer one turn at a time with a structured `{"message", "done"}` stop-signal protocol instead of fragile no-progress heuristics.
  - `agentfit/loop/orchestrator.py` — `ConversationOrchestrator` drives the turn-by-turn loop against any adapter, threading conversation history through the existing `to_agent_interface()` contract.
  - `agentfit/loop/judge.py` — `TranscriptJudge` scores a finished conversation against BNP-selected dimensions, producing the same `DimensionResult` shape heuristic dimensions produce, so governance decisions and Pass@k/Pass^k reliability work unchanged.
  - `agentfit/loop/trace.py` — `AgentTrace`/`TurnRecord`, written to a standalone, self-contained trace file via `--agent-trace-output`.
  - New CLI flags: `--enable-loop`, `--loop-instructions`, `--loop-max-turns`, `--loop-llm-provider`, `--loop-llm-api-key`, `--loop-llm-model`, `--loop-llm-base-url`, `--agent-trace-output`.
- **`CustomHTTPAdapter`** (`--agent-adapter custom_http`): evaluate any REST endpoint that doesn't speak OpenAI's `/v1/chat/completions` shape, configured entirely via `--agent-base-url`, `--agent-request-body` (JSON template with a `{task}` placeholder), `--agent-headers`, and `--agent-response-path` — no adapter subclass or bridge code required.
  - `--agent-response-path` accepts either a single dot-path or a JSON object mapping multiple output fields (content, tool calls, tokens, model) to response paths.
  - Response-path resolution handles both genuinely nested JSON and flat keys that happen to contain literal dots (e.g. workflow platforms returning `"agent1.content"` as one flat key).
- **`agentfit/protocol/tool_call_normalizer.py`**: cross-platform tool-call parsing that tolerates OpenAI-style (`function.name`/`function.arguments`), flatter shapes (`name`/`args`, `toolName`/`arguments`), and unrecognized shapes without crashing an evaluation.
- Conversation-history support across adapters: `OpenAICompatibleAdapter` now prepends prior turns instead of always starting a fresh exchange; `CustomHTTPAdapter` gained a `{conversation_history}` template placeholder that splices in the real structured history rather than a stringified blob.
- `agentfit/bnp/rendering.py` — shared BNP-to-prompt rendering, used by both the post-hoc interpretability judge and the new transcript judge so they never describe the same BNP differently.

### Fixed
- `GenericAdapter`'s sync-callable execution path silently dropped `tools`/`context` on every call (only the async path forwarded them), making `context["conversation_history"]` unreachable for sync bridge callables. Fixed with a signature-aware kwargs filter that stays backward-compatible with simple `lambda task: ...`-style callables.

### Changed
- License changed from Apache License 2.0 to the **Business Source License 1.1**: free to self-host and use (including commercial/institutional use), with resale, sublicensing, or commercial redistribution of the software reserved to RecruitBase absent a separate commercial license. Converts automatically to Apache License 2.0 on the license's Change Date. See [LICENSE](LICENSE).
- `.gitignore` now excludes local evaluation artifacts (`results.json`, `trace.json`, `*.trace.json`) and root-level test fixtures (`/persona.md`, `/refund-policy.md`) generated while running `agentfit evaluate` locally, and generalizes Python bytecode exclusion (`__pycache__/`, `*.py[cod]`) repo-wide instead of per-directory.
- `agentfit/examples/refund-policy.md` reworked into a fully valid BNP profile (previously a plain policy document that failed `BNPParser` validation) — the original refund policy is preserved in full underneath the required BNP structure.

## [0.2.0] - 2024-03-27

### Added
- **Universal Agent Protocol**: Framework-agnostic protocol for evaluating any agent
  - Core protocol definitions with Message, ToolCall, ToolResult formats
  - Pluggable adapter architecture with minimal implementation overhead
  - Zero vendor lock-in design

- **Pre-built Adapters**: 
  - OpenAI adapter for GPT-3.5, GPT-4, and compatible models
  - Anthropic adapter for Claude models
  - Google AgentKit adapter for Vertex AI agents
  - Generic adapter for custom frameworks

- **7 Evaluation Dimensions**:
  - Task Competence (15%) - Ability to understand and execute tasks
  - Tool Use & Integration (15%) - Correct tool selection and invocation
  - Autonomy & Escalation (15%) - Appropriate independence and escalation handling
  - Safety & Alignment (15%) - Safety under adversarial conditions
  - Compliance & Auditability (15%) - Regulatory compliance and audit trails
  - Operational Performance (10%) - Latency, throughput, and cost efficiency
  - Deployment Compatibility (15%) - Infrastructure and deployment readiness

- **Business Need Profiles (BNP)**:
  - Define organization-specific requirements
  - Weighted dimension evaluation based on priorities
  - Support for compliance and performance requirements
  - Domain-specific evaluation scenarios

- **Comprehensive Testing**:
  - Unit tests for all modules
  - Integration tests for evaluator and BNP
  - Protocol and adapter tests
  - 80%+ code coverage

- **Documentation**:
  - Universal Agent Protocol specification with examples
  - Detailed evaluation dimensions guide
  - Quick start guide (5-minute setup)
  - Testing guide with examples
  - PyPI publishing guide
  - Contributing guidelines

- **Examples**:
  - OpenAI agent evaluation example
  - Anthropic agent evaluation example
  - Custom adapter creation example
  - Batch evaluation example

- **Development Tools**:
  - Setup verification script
  - Comprehensive test runner
  - CLI for evaluation
  - Pre-commit hooks

### Changed
- Updated pyproject.toml with proper PyPI metadata
- Enhanced version to 0.2.0 for public release
- Added optional dependencies for adapter support

### Fixed
- CLI integration with async evaluator
- Dimension registration in module initialization
- Protocol message format validation

## [0.1.0] - 2024-03-01

### Added
- Initial project structure
- Core evaluator framework
- Basic dimension implementations
- BNP schema and parser
- CLI interface

---

## Unreleased

### Planned for 0.3.0
- [ ] Web UI for evaluation results
- [ ] Integration with SWE-Bench and other benchmarks
- [ ] Automatic performance profiling
- [ ] A/B testing framework for agent versions
- [ ] Integration with MLOps platforms (MLflow, Weights & Biases)
- [ ] Multi-language support for dimension definitions
- [ ] Cloud-based evaluation service
- [ ] Real-time evaluation dashboard
- [ ] Advanced caching for scenario evaluation

### Under Consideration
- [ ] Distributed evaluation support
- [ ] Custom dimension templates
- [ ] Scenario library (common evaluation cases)
- [ ] Integration with agent monitoring platforms
- [ ] Automated report generation
- [ ] Cost analysis and optimization
- [ ] Performance regression detection
- [ ] Automated agent improvement suggestions

---

## Guidelines for Updates

### Adding New Features
1. Create feature branch: `git checkout -b feature/description`
2. Implement feature with tests
3. Update documentation
4. Create PR for review
5. Once merged, update CHANGELOG.md

### Version Bumping
- **MAJOR.MINOR.PATCH** format
- MAJOR: Breaking changes
- MINOR: New features, backwards compatible
- PATCH: Bug fixes

### Release Checklist
- [ ] Update version in pyproject.toml
- [ ] Update CHANGELOG.md with all changes
- [ ] Run full test suite
- [ ] Build and test on TestPyPI
- [ ] Create git tag
- [ ] Upload to PyPI
- [ ] Create GitHub release
- [ ] Update documentation site

---

## Archive

### Release History
- **0.3.0** - 2026-07-30: Loop testing, CustomHTTPAdapter, cross-platform tool-call normalization, BUSL-1.1 license
- **0.2.0** - 2024-03-27: Universal protocol and 7 dimensions
- **0.1.0** - 2024-03-01: Initial release with core functionality
