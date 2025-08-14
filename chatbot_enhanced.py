"""
Enhanced Meta-Analysis AI Chatbot with Multi-Modal Support and MCP Tools
Combines best practices from ScienceBrain.AI with robust R statistical backend
"""

import os
import json
import subprocess
import base64
import glob
import re
import sys
import tempfile
import threading
import atexit
import subprocess
import uuid
from typing import Optional, List, Dict, Any, Tuple
from datetime import datetime
from pathlib import Path
from io import BytesIO

import gradio as gr
import pandas as pd
import numpy as np
import pytz
from PIL import Image
from PyPDF2 import PdfReader

# LangChain imports for better tool orchestration
from langchain.agents import Tool, AgentExecutor, create_openai_tools_agent
from langchain.memory import ConversationBufferMemory
from langchain_openai import ChatOpenAI
from langchain_anthropic import ChatAnthropic
from langchain.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain.schema import HumanMessage, AIMessage, SystemMessage
from langchain.tools import StructuredTool
from pydantic import BaseModel, Field

# =====================================================================================
#  Configuration & Initialization
# =====================================================================================

# API Keys
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
ANTHROPIC_API_KEY = os.getenv('ANTHROPIC_API_KEY')

# Model Configuration
DEFAULT_MODEL = "gpt-4o-2024-05-13" if OPENAI_API_KEY else "claude-3-opus-20240229"
AVAILABLE_MODELS = []
if OPENAI_API_KEY:
    AVAILABLE_MODELS.extend(["gpt-4o-2024-05-13", "gpt-4o-mini", "gpt-3.5-turbo"])
if ANTHROPIC_API_KEY:
    AVAILABLE_MODELS.extend(["claude-3-opus-20240229", "claude-3-sonnet-20240229", "claude-3-haiku-20240307"])

# Session Management
SESSIONS_DIR = Path(os.getenv("SESSIONS_DIR", "./sessions"))
SESSIONS_DIR.mkdir(exist_ok=True)

# =====================================================================================
#  Enhanced System Prompt
# =====================================================================================

SYSTEM_PROMPT = """You are an advanced meta-analysis assistant with expertise in:
- Statistical analysis using R (meta, metafor packages)
- Research methodology and study design
- Data visualization and interpretation
- Academic writing and reporting

You can process:
- Text queries and commands
- CSV/Excel data files for analysis
- PDF research papers for extraction
- Images of charts/figures for interpretation
- Audio recordings of research discussions

You have a powerful R code interpreter (`execute_r_code`) for custom tasks.

Available tools:
1. initialize_meta_analysis - Start a new analysis session
2. upload_study_data - Upload data for analysis
3. perform_meta_analysis - Run statistical analysis
4. generate_forest_plot - Create visualizations
5. assess_publication_bias - Check for bias
6. generate_report - Create comprehensive reports
7. get_current_session_id - Get the active session ID
8. extract_pdf_data - Extract data from PDF papers
9. analyze_figure - Analyze chart/figure images
10. execute_r_code - Execute arbitrary R code for custom analysis, data manipulation, or plotting. Use this powerful tool when other tools are insufficient.

Always:
- Explain statistical concepts clearly
- Interpret results in context
- Suggest appropriate next steps
- Maintain rigorous scientific standards
"""

# =====================================================================================
#  Pydantic Models for Tool Parameters
# =====================================================================================

class InitializeMetaAnalysisInput(BaseModel):
    name: str = Field(description="Name of the meta-analysis project", default="My Meta-Analysis")
    study_type: str = Field(description="Type of study: clinical_trial, observational, or diagnostic", default="clinical_trial")
    effect_measure: str = Field(description="Effect measure: OR, RR, MD, SMD, HR, PROP, or MEAN", default="OR")
    analysis_model: str = Field(description="Analysis model: fixed, random, or auto", default="random")

class UploadStudyDataInput(BaseModel):
    csv_content: str = Field(description="CSV content as a single string")
    session_id: Optional[str] = Field(description="Session ID from initialization. If None, uses the active session.", default=None)
    validation_level: str = Field(default="comprehensive", description="Validation: basic or comprehensive")

class PerformMetaAnalysisInput(BaseModel):
    session_id: Optional[str] = Field(description="Session ID. If None, uses the active session.", default=None)
    heterogeneity_test: bool = Field(default=True, description="Test for heterogeneity")
    publication_bias: bool = Field(default=True, description="Test for publication bias")
    sensitivity_analysis: bool = Field(default=False, description="Perform sensitivity analysis")

class GenerateForestPlotInput(BaseModel):
    session_id: Optional[str] = Field(description="Session ID. If None, uses the active session.", default=None)
    plot_style: str = Field(default="modern", description="Style: classic, modern, or journal_specific")
    confidence_level: float = Field(default=0.95, description="Confidence level (0.90, 0.95, or 0.99)")

class AssessPublicationBiasInput(BaseModel):
    session_id: Optional[str] = Field(description="Session ID. If None, uses the active session.", default=None)
    methods: List[str] = Field(
        default=["funnel_plot", "egger_test"],
        description="Methods: funnel_plot, egger_test, begg_test, trim_fill"
    )

class GenerateReportInput(BaseModel):
    session_id: Optional[str] = Field(description="Session ID. If None, uses the active session.", default=None)
    format: str = Field(default="html", description="Format: html, pdf, or word")
    include_code: bool = Field(default=False, description="Include R code in report")

class ExecuteRCodeInput(BaseModel):
    r_code: str = Field(description="A string of R code to be executed in the current session context.")

# =====================================================================================
#  File Management Functions
# =====================================================================================

def generate_filename(prompt: str, file_type: str, original_name: str = None) -> str:
    """Generate a safe, timestamped filename"""
    central = pytz.timezone('US/Central')
    safe_date_time = datetime.now(central).strftime("%m%d_%H%M")
    
    safe_prompt = re.sub(r'[<>:"/\\|?*\n]', ' ', prompt).strip()[:50]
    
    if original_name:
        base_name = os.path.splitext(original_name)[0]
        file_stem = f"{safe_date_time}_{safe_prompt}_{base_name}"[:100]
    else:
        file_stem = f"{safe_date_time}_{safe_prompt}"[:100]
        
    return f"{file_stem}.{file_type}"

def create_and_save_file(content: str, prompt: str, should_save: bool, file_type: str = "md", original_name: str = None):
    """Save content to file if enabled"""
    if not should_save:
        return None
    
    filename = generate_filename(prompt, file_type, original_name)
    try:
        output_dir = Path("outputs")
        output_dir.mkdir(exist_ok=True)
        filepath = output_dir / filename
        
        with open(filepath, "w", encoding="utf-8") as f:
            full_content = f"# Meta-Analysis Session\n\n## Prompt:\n{prompt}\n\n---\n\n## Response:\n{content}"
            f.write(full_content)
        
        return str(filepath)
    except Exception as e:
        print(f"Error saving file {filename}: {e}")
        return None

def update_file_list_display(file_types: list):
    """Refresh the list of generated files"""
    if not file_types:
        return gr.update(choices=[], value=[])
    
    output_dir = Path("outputs")
    if not output_dir.exists():
        return gr.update(choices=[], value=[])
    
    all_files = []
    for ext in file_types:
        all_files.extend(output_dir.glob(f"*{ext}"))
    
    all_files.sort(key=lambda x: x.stat().st_mtime, reverse=True)
    file_choices = [str(f.relative_to(output_dir)) for f in all_files]
    
    return gr.update(choices=file_choices[:50], value=[])  # Limit to 50 most recent

def delete_selected_files(files_to_delete: list, current_filter: list):
    """Delete selected files"""
    if not files_to_delete:
        gr.Warning("No files selected for deletion")
        return update_file_list_display(current_filter)
    
    output_dir = Path("outputs")
    for file_name in files_to_delete:
        file_path = output_dir / file_name
        try:
            file_path.unlink()
        except Exception as e:
            gr.Warning(f"Could not delete {file_name}: {e}")
    
    gr.Info(f"Deleted {len(files_to_delete)} files")
    return update_file_list_display(current_filter)

# =====================================================================================
#  MCP Client for Server Communication
# =====================================================================================

class MCPClient:
    """
    A self-contained client for managing and communicating with the standalone
    MCP server process (`server.py`).
    """
    def __init__(self):
        self._lock = threading.Lock()
        self.process: Optional[subprocess.Popen] = None
        self.current_session_id: Optional[str] = None
        self.sessions: Dict[str, Dict] = {}
        atexit.register(self.stop)

    def start(self):
        """Starts the MCP server as a background process."""
        if self.process is None or self.process.poll() is not None:
            print("Starting MCP server...")
            try:
                self.process = subprocess.Popen(
                    [sys.executable, "server.py"],
                    stdin=subprocess.PIPE,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    encoding='utf-8',
                    bufsize=1  # Line-buffered for reliable stdin communication
                )
                print(f"MCP server started with PID: {self.process.pid}")
            except FileNotFoundError:
                print("ERROR: `server.py` not found. Make sure it is in the same directory.")
                raise
            except Exception as e:
                print(f"ERROR: Failed to start MCP server: {e}")
                raise

    def stop(self):
        """Stops the MCP server process."""
        if self.process and self.process.poll() is None:
            print("Stopping MCP server...")
            self.process.terminate()
            try:
                self.process.wait(timeout=5)
                print("MCP server stopped.")
            except subprocess.TimeoutExpired:
                print("MCP server did not terminate in time, killing it.")
                self.process.kill()
                print("MCP server killed.")
            self.process = None

    def call_tool(self, tool_name: str, args: Dict[str, Any]) -> Dict[str, Any]:
        """Sends a tool call request to the MCP server and gets the result."""
        if self.process is None or self.process.poll() is not None:
            print("MCP server process not running. Attempting to start...")
            self.start()
            if self.process is None or self.process.poll() is not None:
                return {"status": "error", "error": "MCP server is not running and could not be restarted."}

        request_id = str(uuid.uuid4())
        if "session_id" not in args and self.current_session_id:
            args["session_id"] = self.current_session_id

        request = {
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {"name": tool_name, "arguments": args},
            "id": request_id,
        }

        with self._lock:
            try:
                self.process.stdin.write(json.dumps(request) + "\n")
                self.process.stdin.flush()
                response_line = self.process.stdout.readline()
                if not response_line:
                    stderr_output = self.process.stderr.read() if self.process.stderr else ""
                    return {"status": "error", "error": "Empty response from MCP server.", "details": stderr_output}
                response = json.loads(response_line)
                if response.get("id") != request_id:
                    return {"status": "error", "error": "Mismatched response ID from MCP server."}
                if "error" in response:
                    return {"status": "error", "error": response["error"]}
                content = response.get("result", {}).get("content", [{}])[0]
                if content.get("type") == "text":
                    return json.loads(content.get("text", "{}"))
                else:
                    return {"status": "error", "error": "Unsupported content type from MCP server."}
            except (IOError, json.JSONDecodeError) as e:
                error_details = self.process.stderr.read() if self.process and self.process.stderr else ""
                return {"status": "error", "error": f"Failed to communicate with MCP server: {e}", "details": error_details}

    def initialize_meta_analysis(self, name: str, study_type: str, effect_measure: str, analysis_model: str) -> str:
        """Initialize a new meta-analysis session."""
        result = self.call_tool("initialize_meta_analysis", {
            "name": name, "study_type": study_type,
            "effect_measure": effect_measure, "analysis_model": analysis_model
        })
        if result.get("status") == "success" and "session_id" in result:
            session_id = result["session_id"]
            self.current_session_id = session_id
            self.sessions[session_id] = {
                "name": name,
                "path": result.get("session_path", tempfile.mkdtemp(prefix=f"meta_{session_id}_")),
                "config": {
                    "study_type": study_type,
                    "effect_measure": effect_measure,
                    "analysis_model": analysis_model
                }
            }
            return f"✅ Meta-analysis initialized successfully!\n\nSession ID: {session_id}\nProject: {name}"
        return f"❌ Initialization failed: {result.get('error', 'Unknown error')}"

    def upload_study_data(self, csv_content: str, session_id: Optional[str] = None, validation_level: str = "comprehensive") -> str:
        """Upload study data from a CSV string."""
        active_session_id = session_id or self.current_session_id
        if not active_session_id:
            return "❌ Error: No active session. Please initialize a meta-analysis first."

        if not csv_content.startswith("data:"):
            encoded_data = base64.b64encode(csv_content.encode()).decode()
        else:
            encoded_data = csv_content

        result = self.call_tool("upload_study_data", {
            "session_id": active_session_id,
            "data_content": encoded_data,
            "data_format": "csv",
            "validation_level": validation_level
        })

        if result.get("status") == "success":
            return f"✅ Data uploaded successfully!\n\nStudies: {result.get('n_studies', 'N/A')}\nValidation: {result.get('validation_summary', 'Passed')}"
        return f"❌ Upload failed: {result.get('error', 'Unknown error')}"

    def perform_meta_analysis(self, session_id: Optional[str] = None, **kwargs) -> str:
        """Perform the meta-analysis."""
        active_session_id = session_id or self.current_session_id
        if not active_session_id:
            return "❌ Error: No active session."

        args = {"session_id": active_session_id, **kwargs}
        result = self.call_tool("perform_meta_analysis", args)

        if result.get("status") == "success":
            summary = result.get("summary", {})
            return f"""✅ Meta-analysis completed!

**Overall Effect:**
- Estimate: {summary.get('estimate', 'N/A')}
- 95% CI: [{summary.get('ci_lower', 'N/A')}, {summary.get('ci_upper', 'N/A')}]
- p-value: {summary.get('p_value', 'N/A')}

**Heterogeneity:**
- I²: {summary.get('i_squared', 'N/A')}%
- τ²: {summary.get('tau_squared', 'N/A')}
- Q-test p-value: {summary.get('q_pvalue', 'N/A')}

**Interpretation:** {summary.get('interpretation', 'See detailed report for full interpretation.')}"""
        return f"❌ Analysis failed: {result.get('error', 'Unknown error')}"

    def generate_forest_plot(self, session_id: Optional[str] = None, **kwargs) -> str:
        """Generate a forest plot."""
        active_session_id = session_id or self.current_session_id
        if not active_session_id:
            return "❌ Error: No active session."

        args = {"session_id": active_session_id, **kwargs}
        result = self.call_tool("generate_forest_plot", args)

        if result.get("status") == "success":
            plot_data = result.get("plot", "")
            if plot_data:
                return f"✅ Forest plot generated!\n\n![Forest Plot](data:image/png;base64,{plot_data})"
            return "✅ Forest plot generated and saved to session folder."
        return f"❌ Plot generation failed: {result.get('error', 'Unknown error')}"

    def assess_publication_bias(self, session_id: Optional[str] = None, methods: List[str] = None) -> str:
        """Assess publication bias."""
        active_session_id = session_id or self.current_session_id
        if not active_session_id:
            return "❌ Error: No active session."

        if methods is None:
            methods = ["funnel_plot", "egger_test"]

        args = {"session_id": active_session_id, "methods": methods}
        result = self.call_tool("assess_publication_bias", args)

        if result.get("status") == "success":
            tests = result.get("tests", {})
            return f"""✅ Publication bias assessment completed!

**Egger's Test:**
- p-value: {tests.get('egger_p', 'N/A')}
- Interpretation: {tests.get('egger_interpretation', 'N/A')}

**Begg's Test:**
- p-value: {tests.get('begg_p', 'N/A')}
- Interpretation: {tests.get('begg_interpretation', 'N/A')}

**Overall Assessment:** {result.get('overall_assessment', 'See full report for details.')}"""
        return f"❌ Bias assessment failed: {result.get('error', 'Unknown error')}"

    def generate_report(self, session_id: Optional[str] = None, **kwargs) -> str:
        """Generate a comprehensive report."""
        active_session_id = session_id or self.current_session_id
        if not active_session_id:
            return "❌ Error: No active session."

        args = {"session_id": active_session_id, **kwargs}
        result = self.call_tool("generate_report", args)

        if result.get("status") == "success":
            report_path = result.get("report_path", "")
            return f"✅ Report generated successfully!\n\nFormat: {kwargs.get('format', 'html').upper()}\nLocation: {report_path}"
        return f"❌ Report generation failed: {result.get('error', 'Unknown error')}"

    def get_current_session_id(self) -> str:
        """Get the current session ID."""
        if self.current_session_id:
            return f"Current session ID: {self.current_session_id}"
        return "No active session. Please use 'initialize_meta_analysis' to start."

    def execute_r_code(self, r_code: str) -> str:
        """Executes arbitrary R code and returns the result."""
        result = self.call_tool("execute_r_code", {"r_code": r_code})

        if result.get("status") == "error":
            return f"""❌ R Code Execution Failed:
Error: {result.get('error', 'Unknown error')}
"""

        response_parts = ["✅ R Code Executed Successfully:"]
        if result.get("stdout") and result['stdout'].strip():
            response_parts.append(f"**Console Output:**\n```\n{result['stdout'].strip()}\n```")
        if result.get("returned_result") and result['returned_result'].strip() != "NULL":
            response_parts.append(f"**Returned Result:**\n```R\n{result['returned_result'].strip()}\n```")
        if result.get("warnings") and result['warnings'].strip():
            response_parts.append(f"**Warnings:**\n```\n{result['warnings'].strip()}\n```")
        if result.get("plot"):
            response_parts.append(f"**Generated Plot:**\n![R Plot](data:image/png;base64,{result['plot']})")

        if len(response_parts) == 1:
            return "✅ R code executed successfully with no output, return value, or plot."

        return "\n\n".join(response_parts)

    def extract_pdf_data(self, pdf_path: str) -> dict:
        """Extract text and metadata from PDF"""
        try:
            reader = PdfReader(pdf_path)
            text = ""
            metadata = {
                "pages": len(reader.pages),
                "title": reader.metadata.title if reader.metadata else None,
                "author": reader.metadata.author if reader.metadata else None
            }

            for page in reader.pages:
                text += page.extract_text() + "\n"

            patterns = {
                "sample_sizes": r"n\s*=\s*(\d+)",
                "effect_sizes": r"(?:OR|RR|MD|SMD|HR)\s*=\s*([\d.]+)",
                "confidence_intervals": r"CI\s*[:=]\s*\[([\d.]+),\s*([\d.]+)\]",
                "p_values": r"p\s*[<>=]\s*([\d.]+)"
            }

            extracted_data = {}
            for name, pattern in patterns.items():
                matches = re.findall(pattern, text, re.IGNORECASE)
                if matches:
                    extracted_data[name] = matches

            return {
                "status": "success",
                "text": text[:5000],
                "metadata": metadata,
                "extracted_data": extracted_data
            }
        except Exception as e:
            return {"status": "error", "error": f"PDF extraction failed: {str(e)}"}

    def analyze_figure(self, image_path: str) -> dict:
        """Analyze figure/chart from image"""
        try:
            img = Image.open(image_path)
            analysis = {"dimensions": img.size, "mode": img.mode, "format": img.format}
            buffered = BytesIO()
            img.save(buffered, format="PNG")
            img_base64 = base64.b64encode(buffered.getvalue()).decode()
            return {"status": "success", "analysis": analysis, "image_base64": img_base64, "message": "Image processed successfully. Ready for AI interpretation."}
        except Exception as e:
            return {"status": "error", "error": f"Image analysis failed: {str(e)}"}



# =====================================================================================
#  LLM Integration
# =====================================================================================

def get_llm_client(model_name: str):
    """Get the appropriate LLM client based on model selection"""
    if model_name.startswith("gpt"):
        if not OPENAI_API_KEY:
            raise gr.Error("OpenAI API key not configured")
        return ChatOpenAI(model=model_name, temperature=0.7)
    elif model_name.startswith("claude"):
        if not ANTHROPIC_API_KEY:
            raise gr.Error("Anthropic API key not configured")
        return ChatAnthropic(model=model_name, temperature=0.7)
    else:
        raise gr.Error(f"Unknown model: {model_name}")

def convert_history_to_langchain(gradio_history: list) -> List:
    """Convert Gradio chat history to LangChain format"""
    messages = []
    for user_msg, bot_msg in gradio_history:
        if user_msg:
            if isinstance(user_msg, tuple):
                text, _ = user_msg
                messages.append(HumanMessage(content=text))
            else:
                messages.append(HumanMessage(content=user_msg))
        if bot_msg:
            messages.append(AIMessage(content=bot_msg))
    return messages

# =====================================================================================
#  Main Chat Handler
# =====================================================================================

def handle_multimodal_submit(message: dict, history: list, model_name: str, should_save: bool):
    """Handle multi-modal chat submissions"""
    text_prompt = message.get("text", "")
    files = message.get("files", [])
    
    # Show user message immediately (optimistic UI)
    user_content = text_prompt
    if files:
        file_names = ", ".join([os.path.basename(f) for f in files])
        user_content += f"\n\n📎 Attached: {file_names}"
    
    history.append([user_content, None])
    yield history, gr.MultimodalTextbox(value=None, interactive=False)
    
    try:
        # Use the global backend client and initialize LLM
        backend = mcp_client
        llm = get_llm_client(model_name)
        
        # Process any attached files
        file_context = ""
        if files:
            for file_path in files:
                ext = os.path.splitext(file_path)[1].lower()
                
                if ext == ".pdf":
                    # Extract PDF data
                    pdf_result = backend.extract_pdf_data(file_path)
                    if pdf_result["status"] == "success":
                        file_context += f"\n\nPDF Analysis:\n{pdf_result['text'][:2000]}..."
                        if pdf_result.get("extracted_data"):
                            file_context += f"\n\nExtracted Data: {json.dumps(pdf_result['extracted_data'], indent=2)}"
                
                elif ext in [".png", ".jpg", ".jpeg", ".gif"]:
                    # Analyze image
                    img_result = backend.analyze_figure(file_path)
                    if img_result["status"] == "success":
                        file_context += f"\n\nImage Analysis: {img_result['message']}"
                
                elif ext in [".csv", ".xlsx", ".xls"]:
                    # Read data file - FIXED INDENTATION HERE
                    try:
                        if ext == ".csv":
                            df = pd.read_csv(file_path)
                        else:
                            df = pd.read_excel(file_path)
                        file_context += f"\n\nData File ({ext}):\nShape: {df.shape}\nColumns: {list(df.columns)}\nFirst 5 rows:\n{df.head().to_string()}"
                    except Exception as e:
                        file_context += f"\n\nError reading {ext} file: {str(e)}"
        
        # Combine prompt with file context
        full_prompt = text_prompt
        if file_context:
            full_prompt += file_context
        
        # Create tools for the agent
        tools = [
            StructuredTool.from_function(
                func=backend.initialize_meta_analysis,
                name="initialize_meta_analysis",
                description="Start a new meta-analysis session",
                args_schema=InitializeMetaAnalysisInput
            ),
            StructuredTool.from_function(
                func=backend.upload_study_data,
                name="upload_study_data",
                description="Upload study data for analysis",
                args_schema=UploadStudyDataInput
            ),
            StructuredTool.from_function(
                func=backend.perform_meta_analysis,
                name="perform_meta_analysis",
                description="Execute the meta-analysis",
                args_schema=PerformMetaAnalysisInput
            ),
            StructuredTool.from_function(
                func=backend.generate_forest_plot,
                name="generate_forest_plot",
                description="Generate forest plot visualization",
                args_schema=GenerateForestPlotInput
            ),
            StructuredTool.from_function(
                func=backend.assess_publication_bias,
                name="assess_publication_bias",
                description="Assess publication bias",
                args_schema=AssessPublicationBiasInput
            ),
            StructuredTool.from_function(
                func=backend.generate_report,
                name="generate_report",
                description="Generate comprehensive report",
                args_schema=GenerateReportInput
            ),
            StructuredTool.from_function(
                func=backend.get_current_session_id,
                name="get_current_session_id",
                description="Get the current active session ID"
            ),
            StructuredTool.from_function(
                func=backend.execute_r_code,
                name="execute_r_code",
                description="Execute arbitrary R code for custom analysis or plotting. Use this for tasks not covered by other tools, like generating custom plots with ggplot2 or performing non-standard calculations.",
                args_schema=ExecuteRCodeInput
            )
        ]
        
        # Create the agent
        prompt = ChatPromptTemplate.from_messages([
            ("system", SYSTEM_PROMPT),
            MessagesPlaceholder(variable_name="chat_history"),
            ("human", "{input}"),
            MessagesPlaceholder(variable_name="agent_scratchpad")
        ])
        
        agent = create_openai_tools_agent(llm, tools, prompt)
        
        # Create memory
        memory = ConversationBufferMemory(
            memory_key="chat_history",
            return_messages=True
        )
        
        # Load existing history into memory
        for msg in convert_history_to_langchain(history[:-1]):
            if isinstance(msg, HumanMessage):
                memory.chat_memory.add_user_message(msg.content)
            elif isinstance(msg, AIMessage):
                memory.chat_memory.add_ai_message(msg.content)
        
        # Create agent executor
        agent_executor = AgentExecutor(
            agent=agent,
            tools=tools,
            memory=memory,
            verbose=True,
            handle_parsing_errors=True
        )
        
        # Execute the agent
        response = agent_executor.invoke({"input": full_prompt})
        bot_response = response["output"]
        
        # Save the response if enabled
        if should_save:
            saved_file = create_and_save_file(bot_response, text_prompt, should_save)
            if saved_file:
                bot_response += f"\n\n💾 *Session saved to: {saved_file}*"
        
        # Update history with bot response
        history[-1][1] = bot_response
        yield history, gr.MultimodalTextbox(value=None, interactive=True)
        
    except Exception as e:
        error_msg = f"❌ **Error:** {str(e)}"
        history[-1][1] = error_msg
        yield history, gr.MultimodalTextbox(value=message, interactive=True)

# =====================================================================================
#  Gradio UI
# =====================================================================================

with gr.Blocks(
    theme=gr.themes.Soft(primary_hue="blue", secondary_hue="green"),
    title="Meta-Analysis AI Assistant Enhanced",
    css="""
    .gradio-container {
        max-width: 1400px !important;
        margin: auto !important;
    }
    """
) as demo:
    gr.Markdown("""
    # 🧬 Meta-Analysis AI Assistant - Enhanced Edition
    *Advanced statistical analysis with multi-modal support and intelligent file management*
    
    ### Features:
    - 📊 **Statistical Analysis**: Comprehensive meta-analysis using R
    - 📄 **PDF Processing**: Extract data from research papers
    - 🖼️ **Image Analysis**: Interpret charts and figures
    - 💾 **Smart File Management**: Auto-save sessions with filtering
    - 🤖 **Multiple AI Models**: Choose between GPT-4 and Claude
    """)
    
    with gr.Row():
        # Sidebar
        with gr.Column(scale=1, min_width=300):
            gr.Markdown("### ⚙️ Configuration")
            
            model_selector = gr.Dropdown(
                label="AI Model",
                choices=AVAILABLE_MODELS if AVAILABLE_MODELS else ["No API keys configured"],
                value=DEFAULT_MODEL if AVAILABLE_MODELS else None,
                interactive=bool(AVAILABLE_MODELS)
            )
            
            save_checkbox = gr.Checkbox(
                label="💾 Auto-save sessions",
                value=True
            )
            
            with gr.Accordion("📁 Session Files", open=False):
                file_filter = gr.CheckboxGroup(
                    label="Filter by type",
                    choices=[".md", ".html", ".pdf", ".png", ".csv"],
                    value=[".md", ".html"]
                )
                file_list = gr.CheckboxGroup(
                    label="Generated files (select to delete)",
                    choices=[],
                    value=[]
                )
                with gr.Row():
                    refresh_btn = gr.Button("🔄 Refresh", size="sm")
                    delete_btn = gr.Button("🗑️ Delete", size="sm", variant="stop")
            
            with gr.Accordion("📚 Quick Guide", open=False):
                gr.Markdown("""
                **Getting Started:**
                1. Start with "Initialize a meta-analysis for [your topic]"
                2. Upload your data (CSV/Excel) or paste it
                3. Run the analysis with "Perform the meta-analysis"
                4. Generate visualizations and reports
                
                **Supported Files:**
                - CSV/Excel: Study data
                - PDF: Research papers
                - Images: Charts/figures
                
                **Example Prompts:**
                - "Start a meta-analysis for diabetes treatment studies"
                - "Extract data from this PDF paper"
                - "Analyze this forest plot image"
                - "Generate a PRISMA-compliant report"
                """)
            
            clear_btn = gr.Button("🗑️ Clear Chat", variant="stop", size="lg")
        
        # Main Chat Area
        with gr.Column(scale=3):
            chatbot = gr.Chatbot(
                label="Conversation",
                bubble_full_width=False,
                height=600,
                avatar_images=(None, "🤖"),
                type="tuples"  # Explicitly set to avoid deprecation warning
            )
            
            multimodal_input = gr.MultimodalTextbox(
                file_types=["image", "text"],
                placeholder="Ask a question, upload data files, or share research papers...",
                label="Your Input",
                submit_btn=True
            )
            
            with gr.Row():
                gr.Examples(
                    examples=[
                        ["Initialize a meta-analysis for randomized controlled trials on hypertension treatments"],
                        ["Upload and validate my study data"],
                        ["Perform a random-effects meta-analysis with heterogeneity testing"],
                        ["Generate a forest plot with 95% confidence intervals"],
                        ["Check for publication bias using funnel plots and Egger's test"],
                        ["Create a comprehensive HTML report with all results"]
                    ],
                    inputs=multimodal_input,
                    label="Example Prompts"
                )
    
    # Event Handlers
    multimodal_input.submit(
        fn=handle_multimodal_submit,
        inputs=[multimodal_input, chatbot, model_selector, save_checkbox],
        outputs=[chatbot, multimodal_input]
    )
    
    clear_btn.click(
        fn=lambda: ([], None),
        outputs=[chatbot, multimodal_input]
    )
    
    refresh_btn.click(
        fn=update_file_list_display,
        inputs=[file_filter],
        outputs=[file_list]
    )
    
    file_filter.change(
        fn=update_file_list_display,
        inputs=[file_filter],
        outputs=[file_list]
    )
    
    delete_btn.click(
        fn=delete_selected_files,
        inputs=[file_list, file_filter],
        outputs=[file_list]
    )
    
    # Load initial file list
    demo.load(
        fn=update_file_list_display,
        inputs=[file_filter],
        outputs=[file_list]
    )

# This section is now managed by the MCPClient class.


# =====================================================================================
#  Launch Configuration
# =====================================================================================

# Create a single, shared MCPClient instance for the application
mcp_client = MCPClient()
if __name__ == "__main__":
    # Check for API keys
    if not AVAILABLE_MODELS:
        print("⚠️  Warning: No API keys configured!")
        print("Please set OPENAI_API_KEY or ANTHROPIC_API_KEY environment variables")
    
    # Create necessary directories
    Path("outputs").mkdir(exist_ok=True)
    Path("sessions").mkdir(exist_ok=True)
    
    # Start the MCP server using the client instance
    mcp_client.start()

    # Launch the app
    demo.launch(
        server_name=os.getenv("GRADIO_SERVER_NAME", "0.0.0.0"),
        server_port=int(os.getenv("GRADIO_SERVER_PORT", 7860)),
        share=False,
        debug=True
    )