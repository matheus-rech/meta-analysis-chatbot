# 🧬 Meta-Analysis AI Chatbot

An intelligent conversational assistant for conducting comprehensive meta-analyses, powered by LLMs (GPT-4/Claude) with R statistical backend.

[![Gradio](https://img.shields.io/badge/Gradio-5.11.0+-orange)](https://gradio.app)
[![R](https://img.shields.io/badge/R-4.0+-blue)](https://www.r-project.org/)
[![Python](https://img.shields.io/badge/Python-3.8+-green)](https://www.python.org/)
[![Docker](https://img.shields.io/badge/Docker-Ready-blue)](https://www.docker.com/)
[![Hugging Face Spaces](https://img.shields.io/badge/🤗%20Hugging%20Face-Spaces-yellow)](https://huggingface.co/spaces)

## 🌟 Features

- **🤖 Natural Language Interface**: Chat with AI to conduct your meta-analysis
- **🔬 R Statistical Backend**: Powered by `meta` and `metafor` R packages
- **🎯 Automatic Tool Orchestration**: AI decides which statistical tools to use
- **📊 Complete Analysis Pipeline**: From data upload to publication-ready reports
- **🎨 Multiple UI Options**: Chatbot, direct tools, and native Gradio MCP
- **☁️ Cloud Ready**: Deploy to Hugging Face Spaces with Docker

## 🚀 Quick Start

### Option 1: Local Development

```bash
# Clone the repository
git clone https://github.com/yourusername/meta-analysis-chatbot.git
cd meta-analysis-chatbot

# Install dependencies
pip install -r requirements-chatbot.txt

# Set API key (choose one)
export OPENAI_API_KEY="your-openai-key"
export ANTHROPIC_API_KEY="your-anthropic-key"

# Run the chatbot
python chatbot_langchain.py
```

Open browser to: http://localhost:7860

### Option 2: Docker

```bash
# Build the image
docker build -f Dockerfile.chatbot -t meta-analysis-chatbot .

# Run with API key
docker run -p 7860:7860 \
  -e OPENAI_API_KEY="your-key" \
  meta-analysis-chatbot
```

### Option 3: Deploy to Hugging Face Spaces

1. Fork this repository
2. Create a new Space on [Hugging Face](https://huggingface.co/spaces)
3. Choose "Docker" as the SDK
4. Connect your GitHub repository
5. Add your API key as a Space secret
6. Deploy!

## 📁 Repository Structure

```
meta-analysis-chatbot/
├── chatbot_langchain.py       # Main chatbot with LangChain
├── chatbot_app.py             # Basic chatbot implementation
├── gradio_native_mcp.py      # Native Gradio MCP implementation
├── server.py                  # Python MCP server
├── scripts/                   # R statistical scripts
│   ├── entry/                # Entry points
│   │   └── mcp_tools.R       # Main R dispatcher
│   ├── tools/                # Individual tool implementations
│   ├── adapters/             # Package adapters
│   └── utils/                # Utility functions
├── templates/                 # Report templates
├── requirements-chatbot.txt   # Python dependencies
├── Dockerfile.chatbot         # Docker configuration
└── README.md                 # This file
```

## 🛠️ Available Implementations

### 1. **LangChain Chatbot** (`chatbot_langchain.py`) - Recommended
- Advanced tool orchestration with LangChain
- Structured tool definitions with Pydantic
- Conversation memory management
- Best error handling

### 2. **Basic Chatbot** (`chatbot_app.py`)
- Direct LLM integration
- Simpler implementation
- Good for understanding the architecture

### 3. **Native Gradio MCP** (`gradio_native_mcp.py`)
- Follows Gradio's official MCP patterns
- Three-tab interface
- Best for developers who want direct tool access

## 💬 Example Conversations

```
You: "Start a new meta-analysis for my clinical trial data"
AI: "I'll help you set up a meta-analysis for clinical trials. Let me initialize a session..."

You: "Here's my CSV data: [paste data]"
AI: "I'll upload and validate your data now..."

You: "Run the analysis with heterogeneity testing"
AI: "Running comprehensive meta-analysis with heterogeneity and publication bias tests..."

You: "What does an I² of 75% mean?"
AI: "An I² value of 75% indicates substantial heterogeneity. This means that 75% of the variability..."
```

## 📊 Supported Analyses

- **Effect Measures**: OR, RR, MD, SMD, HR, PROP, MEAN
- **Models**: Fixed effects, Random effects, Auto-selection
- **Heterogeneity**: I², Q-test, τ²
- **Publication Bias**: Funnel plots, Egger's test, Begg's test, Trim & Fill
- **Visualizations**: Forest plots, Funnel plots
- **Reports**: HTML, PDF, Word formats

## 🔧 Configuration

### Environment Variables

```bash
OPENAI_API_KEY          # OpenAI API key
ANTHROPIC_API_KEY       # Anthropic API key (alternative)
SESSIONS_DIR            # Directory for session storage
GRADIO_SERVER_NAME      # Server binding (default: 0.0.0.0)
GRADIO_SERVER_PORT      # Port (default: 7860)
```

### Data Format

Upload CSV with these columns:
```csv
study_id,effect_size,se,year,n_treatment,n_control
Smith2020,0.45,0.12,2020,150,148
Johnson2021,0.38,0.15,2021,200,195
```

## 🐳 Docker Deployment

The Docker image includes:
- Python 3.8+ with Gradio
- R 4.0+ with statistical packages
- All required dependencies
- Optimized for Hugging Face Spaces

```yaml
# For Hugging Face Spaces, add to README.md:
---
title: Meta Analysis AI Assistant
emoji: 🧬
colorFrom: blue
colorTo: green
sdk: docker
app_port: 7860
---
```

## 🔬 R Integration

This project leverages R's powerful statistical ecosystem:
- **meta**: Comprehensive meta-analysis package
- **metafor**: Advanced meta-analysis methods
- **ggplot2**: Publication-quality visualizations
- **rmarkdown**: Report generation

The R backend is essential and cannot be replaced with Python equivalents.

## 🤝 Contributing

Contributions are welcome! Please:
1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

## 📄 License

MIT License - see LICENSE file for details

## 🙏 Acknowledgments

- Built on [Gradio](https://gradio.app) by Hugging Face
- Statistical analysis powered by R [meta](https://cran.r-project.org/package=meta) and [metafor](https://cran.r-project.org/package=metafor) packages
- LLM integration via [LangChain](https://langchain.com)
- Original MCP implementation from [meta-analysis-mvp-standalone](https://github.com/matheus-rech/meta-analysis-mvp-standalone)

## 📧 Support

For issues and questions:
- Open an issue on GitHub
- Check the documentation in `/docs`
- Review example notebooks in `/examples`

---

Made with ❤️ for the research community