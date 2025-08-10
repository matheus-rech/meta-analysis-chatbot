# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

### Development & Testing

```bash
# Install Python dependencies
pip install -r requirements-chatbot.txt

# Install R dependencies
Rscript scripts/utils/install_packages.R

# Run the main chatbot (recommended)
python chatbot_langchain.py

# Run alternative implementations
python chatbot_app.py           # Basic implementation
python gradio_native_mcp.py    # Native Gradio MCP

# Run all tests
python tests/run_all_tests.py

# Run specific test suites
python tests/run_all_tests.py functional    # MCP server tests
python tests/run_all_tests.py ui           # Gradio UI tests
python tests/run_all_tests.py integration  # Client integration tests

# Test R backend directly
Rscript scripts/entry/mcp_tools.R health_check '{}'
Rscript scripts/entry/health_test.R
```

### Docker Operations

```bash
# Build Docker image
docker build -f Dockerfile.chatbot -t meta-analysis-chatbot .

# Run container with API key
docker run -p 7860:7860 -e OPENAI_API_KEY="your-key" meta-analysis-chatbot
```

## Architecture

### Core Components

**Python-R Bridge Architecture**
- `server.py`: MCP server that dispatches tool calls to R scripts via subprocess
- `scripts/entry/mcp_tools.R`: Main R dispatcher that routes to specific tool implementations
- Communication: JSON serialization between Python and R layers
- Session management: UUID-based sessions stored in `sessions/` directory

**Multi-Implementation Strategy**
1. **chatbot_langchain.py**: Production-ready with LangChain agent framework, structured tool definitions, conversation memory
2. **chatbot_app.py**: Simpler direct LLM integration for understanding core concepts
3. **gradio_native_mcp.py**: Three-tab interface following Gradio's MCP patterns

**Tool Pipeline**
1. User request → LLM parses intent
2. LLM calls appropriate tool with parameters
3. Python MCP server receives tool call
4. Server dispatches to R script via subprocess
5. R script executes analysis using meta/metafor packages
6. Results returned as JSON through the stack

### R Statistical Backend

**Tool Scripts** (`scripts/tools/`)
- `upload_data.R`: Data validation and preparation
- `perform_analysis.R`: Core meta-analysis execution
- `generate_forest_plot.R`: Visualization generation
- `assess_publication_bias.R`: Bias testing (Egger's, Begg's, trim-and-fill)
- `generate_report.R`: HTML/PDF report generation
- `get_session_status.R`: Session state management

**Adapters** (`scripts/adapters/`)
- `cochrane_guidance.R`: Cochrane Handbook implementation
- `meta_adapter.R`: Package abstraction layer

### Session Management

Each analysis session creates:
```
sessions/{session_id}/
├── session.json          # Session metadata
├── input/                # Raw uploaded data
├── processing/           # Intermediate RDS files
├── results/              # Analysis outputs
└── tmp/                  # Temporary files
```

## Key Design Patterns

### Error Handling
- R scripts return structured JSON with `status` field (success/error)
- Python layer catches subprocess errors and timeouts
- LLM receives error messages and can retry or suggest fixes

### Data Flow
1. CSV/Excel upload → Base64 encoding → JSON transport
2. R validates and converts to appropriate data structures
3. Analysis results stored as RDS files for session persistence
4. Visualizations generated as base64-encoded PNG/HTML

### LLM Integration
- Tool descriptions include parameter schemas (Pydantic models)
- System prompts guide appropriate tool selection
- Conversation memory maintains context across interactions

## Environment Variables

```bash
OPENAI_API_KEY          # OpenAI API key (required for GPT models)
ANTHROPIC_API_KEY       # Anthropic API key (alternative)
SESSIONS_DIR           # Session storage directory (default: ./sessions)
RSCRIPT_BIN           # R executable path (default: Rscript)
RSCRIPT_TIMEOUT_SEC   # R script timeout (default: 300)
DEBUG_R               # Enable R debugging output (set to "1")
```

## Common Development Tasks

### Adding a New Statistical Tool

1. Create R implementation in `scripts/tools/new_tool.R`
2. Add tool name to `TOOLS` list in `server.py`
3. Update dispatcher in `scripts/entry/mcp_tools.R`
4. Define Pydantic model in `chatbot_langchain.py`
5. Add tool to agent's tool list

### Debugging R Integration

```bash
# Enable debug output
export DEBUG_R=1

# Test R script directly
Rscript scripts/entry/mcp_tools.R upload_study_data '{"session_id":"test","csv_content":"..."}' ./sessions/test

# Check R package installation
Rscript -e "installed.packages()[,'Package']"
```

### Testing Data Flow

```python
# Test Python-R bridge
python test_subprocess_bridge.py

# Test MCP client
python test_mcp_clients.py
```

## Important Notes

- R backend is essential - cannot be replaced with Python equivalents
- Session cleanup is manual - implement cleanup strategy for production
- Large datasets may hit subprocess communication limits
- API keys should never be committed - use environment variables
- Docker deployment requires both Python and R environments