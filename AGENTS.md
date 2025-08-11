<general_rules>
- Search before creating:
  - R tools: check scripts/tools/. If none exists, add scripts/tools/<tool_name>.R and keep logic modular.
  - R dispatcher: wire new tools in scripts/entry/mcp_tools.R (source the file and add a dispatcher branch returning a JSON-like list with a status field).
  - Python MCP server: update TOOLS in server.py and ensure call_tool_resp supports the new tool. The server writes args to a temp JSON in the session tmp/ and calls R with [RSCRIPT_BIN, '--vanilla', scripts/entry/mcp_tools.R, <tool>, <args_file>, <session_dir>].
  - LangChain app: in chatbot_langchain.py, define a Pydantic input model and register a StructuredTool, then add it to the agent’s tool list with a concise description.
- Security and validation:
  - Do not use subprocess with shell=True. Prefer utils/security_integration.apply_security_patches() (already used by server.py) or utils/secure_subprocess.SecureSubprocess for any new subprocess execution.
  - Validate and sanitize all external inputs using utils/validators.InputValidator and utils/r_sanitizer.RScriptSanitizer. Use temp files for large payloads; sanitize R-facing strings.
  - Never commit secrets. Use environment variables (.env based on .env.example). Key vars: OPENAI_API_KEY or ANTHROPIC_API_KEY, SESSIONS_DIR, RSCRIPT_BIN, RSCRIPT_TIMEOUT_SEC, DEBUG_R, GRADIO_SERVER_NAME, GRADIO_SERVER_PORT.
- Code style and structure:
  - Python (3.8+): add type hints and docstrings where useful. Before committing, run: black ., flake8 ., mypy . (tools available via tests/requirements-test.txt).
  - R: keep functions pure and deterministic. Return structured lists that serialize to JSON via jsonlite with a status field (success/error). Shared logic belongs in scripts/adapters/ (e.g., meta_adapter.R).
- File placement conventions:
  - R tools: scripts/tools/; adapters/utilities: scripts/adapters/; R dispatcher: scripts/entry/mcp_tools.R.
  - Python bridge/server: server.py; UI apps: chatbot_langchain.py, chatbot_app.py, gradio_native_mcp.py.
  - Python shared utilities: utils/ (security_integration.py, secure_subprocess.py, validators.py, r_sanitizer.py, error_handler.py, health_check.py, etc.).
  - Templates/assets: templates/; runtime data: sessions/ (excluded from VCS).
- Sessions and data:
  - Sessions live under sessions/{session_id}/ with session.json, input/, processing/, results/, tmp/; controlled by SESSIONS_DIR. Do not commit session contents.
  - Encode large outputs (plots, HTML) as base64 in responses when needed.
- Common commands:
  - Install Python deps: pip install -r requirements-chatbot.txt
  - Install R deps: Rscript scripts/utils/install_packages.R
  - Run main chatbot: python chatbot_langchain.py (serves on port 7860)
  - Run all tests: python tests/run_all_tests.py
  - Run specific suites: python tests/run_all_tests.py functional | ui | integration | inspector
  - Docker build/run: docker build -f Dockerfile.chatbot -t meta-analysis-chatbot . ; docker run -p 7860:7860 -e OPENAI_API_KEY="..." meta-analysis-chatbot
</general_rules>

<repository_structure>
- Applications and orchestration
  - chatbot_langchain.py: Primary Gradio + LangChain chatbot with tool orchestration and conversation memory.
  - chatbot_app.py: Simpler chatbot implementation for core concepts.
  - gradio_native_mcp.py: Native Gradio MCP demo implementation.
  - server.py: Minimal MCP stdio server bridging Python to R via scripts/entry/mcp_tools.R; manages sessions and temp JSON arg files.
- R statistical backend
  - scripts/entry/mcp_tools.R: Main R dispatcher; sources tool scripts and optional adapters; routes calls by tool name.
  - scripts/tools/: R tool implementations (upload_data.R, perform_analysis.R, generate_forest_plot.R, assess_publication_bias.R, generate_report.R, get_session_status.R).
  - scripts/adapters/: Abstractions/guidance (meta_adapter.R, cochrane_guidance.R, etc.).
- Utilities and shared modules
  - utils/: Security and validation (security_integration.py, secure_subprocess.py, validators.py, r_sanitizer.py, error_handler.py, health_check.py, etc.).
- Configuration and requirements
  - .env.example: Template for environment configuration.
  - config/agent-environment.yaml: Declarative agent settings (reference for tooling).
  - requirements-chatbot.txt (main), requirements-mcp.txt (FastMCP variant), requirements-poc.txt (PoC demos).
  - Dockerfile.chatbot and Dockerfile.enhanced for containerized deployments.
- Tests
  - tests/: Pytest-based suites, including Playwright UI tests and functional/integration suites; tests/run_all_tests.py orchestrates environment checks and execution; tests/requirements-test.txt lists test and lint tools.
- Documentation
  - README.md and focused guides (README_CHATBOT.md, README_NATIVE.md, README_R_NATIVE.md); CLAUDE.md contains architecture overview and quick commands.
- Runtime data
  - sessions/: Per-session working directories created at runtime; should be ignored by VCS.
</repository_structure>

<dependencies_and_installation>
- Python (3.8+)
  - Create/activate a virtual environment.
  - Install main app dependencies: pip install -r requirements-chatbot.txt
  - Alternative stacks: requirements-mcp.txt (FastMCP server) and requirements-poc.txt (PoC demos) as needed.
- R (4.0+)
  - Install required R packages (meta, metafor, jsonlite, ggplot2, rmarkdown, knitr, etc.). Recommended: Rscript scripts/utils/install_packages.R
- Environment variables
  - Copy .env.example to .env or export variables. At minimum set OPENAI_API_KEY or ANTHROPIC_API_KEY. Common extras: SESSIONS_DIR, RSCRIPT_BIN, RSCRIPT_TIMEOUT_SEC, DEBUG_R, GRADIO_SERVER_NAME, GRADIO_SERVER_PORT.
- UI testing prerequisites (optional)
  - pip install -r tests/requirements-test.txt
  - playwright install chromium
- Docker (optional)
  - Build: docker build -f Dockerfile.chatbot -t meta-analysis-chatbot .
  - Run: docker run -p 7860:7860 -e OPENAI_API_KEY="..." meta-analysis-chatbot
</dependencies_and_installation>

<testing_instructions>
- Frameworks and scope
  - Pytest for unit/integration tests; Playwright for UI tests. End-to-end tests exercise the Python→R tool pipeline and MCP server.
- Setup
  - pip install -r tests/requirements-test.txt
  - Rscript scripts/utils/install_packages.R
  - For UI tests: playwright install chromium
- Running
  - All tests: python tests/run_all_tests.py
  - Specific suites: python tests/run_all_tests.py functional | ui | integration | inspector
  - Direct pytest: pytest tests/ -v; coverage: pytest tests/ --cov=. --cov-report=html
- Environment notes
  - Ensure R is installed and RSCRIPT_BIN is resolvable. Set OPENAI_API_KEY or ANTHROPIC_API_KEY (UI tests may inject a dummy key). Use DEBUG_R=1 to surface R stderr during failures. RSCRIPT_TIMEOUT_SEC controls R subprocess timeouts.
- What to test
  - utils/ modules (validators, secure_subprocess, error handling, health checks).
  - server.py MCP flows (tools/list, tools/call) and session management.
  - Full tool pipeline: initialize_meta_analysis → upload_study_data → perform_meta_analysis → generate_forest_plot → assess_publication_bias → generate_report.
  - Gradio UI behaviors in chatbot_langchain.py or gradio_native_mcp.py.
- Troubleshooting
  - Verify R package installation; check sessions/ for expected artifacts; review tests/playwright_report.html for UI failures; enable DEBUG_R for detailed R errors.
</testing_instructions>

<pull_request_formatting>
</pull_request_formatting>

