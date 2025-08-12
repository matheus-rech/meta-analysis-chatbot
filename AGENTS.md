<repository_structure>
- Applications and orchestration:
  - /chatbot_langchain.py: Primary Gradio + LangChain chatbot that orchestrates tools and manages conversation memory.
  - /chatbot_app.py: Simpler chatbot variant for core concepts.
  - /gradio_native_mcp.py: Native Gradio MCP implementation demo.
  - /server.py: Minimal MCP stdio server bridging Python to R via scripts/entry/mcp_tools.R; maintains sessions and temp JSON arg files.
- R backend:
  - /scripts/entry/mcp_tools.R: CLI dispatcher; sources tool scripts and optional adapters; routes calls based on tool name.
  - /scripts/tools/: R tool implementations (e.g., upload_data.R, perform_analysis.R, generate_forest_plot.R, assess_publication_bias.R, generate_report.R, get_session_status.R).
  - /scripts/adapters/: Abstraction and guidance layers (e.g., meta_adapter.R, cochrane_guidance.R).
- Python utilities:
  - /utils/: Security and validation modules (security_integration.py, secure_subprocess.py, validators.py, r_sanitizer.py, error_handler.py, health_check.py, etc.).
- Configuration and environment:
  - /.env.example: Template for required/optional environment variables.
  - /config/agent-environment.yaml: Declarative agent settings (non-runtime, for reference and tooling).
  - Requirements files: requirements-chatbot.txt (main), requirements-mcp.txt (FastMCP variant), requirements-poc.txt (PoC demos).
  - Dockerfile.chatbot: Container build targeting LangChain chatbot + R backend.
- Tests:
  - /tests/: Pytest-based suites; includes Playwright UI tests and functional/integration tests. tests/run_all_tests.py orchestrates environment checks and test execution. tests/requirements-test.txt includes pytest, playwright, black, flake8, mypy, etc.
- Documentation:
  - README.md and specialized READMEs (README_CHATBOT.md, README_NATIVE.md, README_R_NATIVE.md); CLAUDE.md has quick commands, architecture, and workflows.
- Runtime data:
  - /sessions/: Per-session working data and outputs created at runtime; should be excluded from VCS.
</repository_structure>

<dependencies_and_installation>
- Python environment (3.8+):
  - Create a virtualenv, then install main app dependencies: pip install -r requirements-chatbot.txt
  - Alternative stacks: requirements-mcp.txt (FastMCP server variant) and requirements-poc.txt (PoC demos) as needed.
- R environment (4.0+):
  - Install required packages (meta, metafor, jsonlite, ggplot2, rmarkdown, knitr, etc.). Recommended: Rscript scripts/utils/install_packages.R
- Environment variables:
  - Copy .env.example to .env or export variables. At minimum set OPENAI_API_KEY or ANTHROPIC_API_KEY. Common extras: SESSIONS_DIR, RSCRIPT_BIN, RSCRIPT_TIMEOUT_SEC, DEBUG_R, GRADIO_SERVER_NAME, GRADIO_SERVER_PORT.
- UI testing prerequisites (optional):
  - pip install -r tests/requirements-test.txt ; playwright install chromium
- Docker (optional):
  - Build: docker build -f Dockerfile.chatbot -t meta-analysis-chatbot .
  - Run: docker run -p 7860:7860 -e OPENAI_API_KEY="..." meta-analysis-chatbot
</dependencies_and_installation>

<testing_instructions>
- Frameworks and scope:
  - Tests use pytest; UI tests use Playwright; functional/integration tests exercise the Python-R bridge and MCP server.
- Setup:
  - pip install -r tests/requirements-test.txt
  - Rscript scripts/utils/install_packages.R
  - For UI tests: playwright install chromium
- Running:
  - All tests: python tests/run_all_tests.py
  - Specific suites: python tests/run_all_tests.py functional | ui | integration | inspector
  - Direct pytest: pytest tests/ -v ; coverage: pytest tests/ --cov=. --cov-report=html
- Environment notes:
  - Set OPENAI_API_KEY or ANTHROPIC_API_KEY (UI tests may use a dummy key). Ensure R is installed and RSCRIPT_BIN is resolvable. Use DEBUG_R=1 to surface R stderr during failures.
- What to test:
  - Python utils in /utils (validators, security wrappers, error handling, health checks).
  - MCP server in /server.py (tools/list and tools/call flows).
  - End-to-end tool pipeline: initialize_meta_analysis → upload_study_data → perform_meta_analysis → generate_forest_plot → assess_publication_bias → generate_report.
  - Gradio UI behaviors in /chatbot_langchain.py or /gradio_native_mcp.py.
- Troubleshooting:
  - Verify R packages are installed, RSCRIPT_TIMEOUT_SEC is adequate, and sessions/ contains expected artifacts; check tests/playwright_report.html for UI failures.
</testing_instructions>

<pull_request_formatting>
</pull_request_formatting>