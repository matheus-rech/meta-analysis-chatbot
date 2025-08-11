"""
Enhanced Meta-Analysis AI Chatbot with Multi-Modal Support
Combines best practices from ScienceBrain.AI with robust R statistical backend
"""

import os
import json
import subprocess
import base64
import glob
import re
import tempfile
import threading
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
import cv2
from openai import OpenAI

# LangChain imports for better tool orchestration
from langchain.agents import Tool, AgentExecutor, create_openai_tools_agent
from langchain.memory import ConversationBufferMemory
from langchain_openai import ChatOpenAI
from langchain_anthropic import ChatAnthropic
from langchain.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain.schema import HumanMessage, AIMessage, SystemMessage
from langchain.tools import StructuredTool
from pydantic import BaseModel, Field

# MCP Server management
SERVER_SCRIPT_PATH = os.path.join(os.path.dirname(__file__), "server.py")
SERVER_CMD = ["python", SERVER_SCRIPT_PATH]
server_proc: Optional[subprocess.Popen] = None
server_lock = threading.Lock()

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

Available tools:
1. initialize_meta_analysis - Start a new analysis session
2. upload_study_data - Upload data for analysis
3. perform_meta_analysis - Run statistical analysis
4. generate_forest_plot - Create visualizations
5. assess_publication_bias - Check for bias
6. generate_report - Create comprehensive reports
7. extract_pdf_data - Extract data from PDF papers
8. analyze_figure - Analyze chart/figure images

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
    name: str = Field(description="Name of the meta-analysis project")
    study_type: str = Field(description="Type of study: clinical_trial, observational, or diagnostic")
    effect_measure: str = Field(description="Effect measure: OR, RR, MD, SMD, HR, PROP, or MEAN")
    analysis_model: str = Field(description="Analysis model: fixed, random, or auto")

class UploadStudyDataInput(BaseModel):
    session_id: str = Field(description="Session ID from initialization")
    csv_content: str = Field(description="CSV content as string (will be encoded)")
    data_format: str = Field(default="csv", description="Data format: csv, excel, or revman")
    validation_level: str = Field(default="comprehensive", description="Validation: basic or comprehensive")

class PerformMetaAnalysisInput(BaseModel):
    session_id: str = Field(description="Session ID")
    heterogeneity_test: bool = Field(default=True, description="Test for heterogeneity")
    publication_bias: bool = Field(default=True, description="Test for publication bias")
    sensitivity_analysis: bool = Field(default=False, description="Perform sensitivity analysis")

class GenerateForestPlotInput(BaseModel):
    session_id: str = Field(description="Session ID")
    plot_style: str = Field(default="modern", description="Style: classic, modern, or journal_specific")
    confidence_level: float = Field(default=0.95, description="Confidence level (0.90, 0.95, or 0.99)")

class AssessPublicationBiasInput(BaseModel):
    session_id: str = Field(description="Session ID")
    methods: List[str] = Field(
        default=["funnel_plot", "egger_test"],
        description="Methods: funnel_plot, egger_test, begg_test, trim_fill"
    )

class GenerateReportInput(BaseModel):
    session_id: str = Field(description="Session ID")
    format: str = Field(default="html", description="Format: html, pdf, or word")
    include_code: bool = Field(default=False, description="Include R code in report")

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
#  Enhanced MCP Tool Wrapper
# =====================================================================================

class EnhancedMCPToolWrapper:
    """Enhanced wrapper for MCP tools with multi-modal support"""
    
    def __init__(self):
        self.current_session_id = None
        self.server_proc = None
        self.sessions = {}
    
    def start_server(self):
        """Start MCP server if not running"""
        global server_proc
        with server_lock:
            if server_proc and server_proc.poll() is None:
                return
            server_proc = subprocess.Popen(
                SERVER_CMD,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1
            )
            self.server_proc = server_proc
    
    def stop_server(self):
        """Stop MCP server"""
        global server_proc
        with server_lock:
            if server_proc and server_proc.poll() is None:
                server_proc.terminate()
                server_proc.wait(timeout=5)
                server_proc = None
    
    def call_mcp_tool(self, tool_name: str, arguments: dict) -> dict:
        """Call an MCP tool through the server"""
        self.start_server()
        
        request = {
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {
                "name": tool_name,
                "arguments": arguments
            },
            "id": 1
        }
        
        try:
            self.server_proc.stdin.write(json.dumps(request) + "\n")
            self.server_proc.stdin.flush()
            
            response_line = self.server_proc.stdout.readline()
            if response_line:
                response = json.loads(response_line)
                if "result" in response:
                    return response["result"]
                elif "error" in response:
                    return {"status": "error", "error": response["error"]["message"]}
            return {"status": "error", "error": "No response from server"}
        except Exception as e:
            return {"status": "error", "error": str(e)}
    
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
            
            # Look for common meta-analysis data patterns
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
                "text": text[:5000],  # First 5000 chars for context
                "metadata": metadata,
                "extracted_data": extracted_data
            }
        except Exception as e:
            return {"status": "error", "error": f"PDF extraction failed: {str(e)}"}
    
    def analyze_figure(self, image_path: str) -> dict:
        """Analyze figure/chart from image"""
        try:
            img = Image.open(image_path)
            
            # Basic image analysis
            analysis = {
                "dimensions": img.size,
                "mode": img.mode,
                "format": img.format
            }
            
            # Convert to base64 for potential API processing
            buffered = BytesIO()
            img.save(buffered, format="PNG")
            img_base64 = base64.b64encode(buffered.getvalue()).decode()
            
            return {
                "status": "success",
                "analysis": analysis,
                "image_base64": img_base64,
                "message": "Image processed successfully. Ready for AI interpretation."
            }
        except Exception as e:
            return {"status": "error", "error": f"Image analysis failed: {str(e)}"}
    
    # Existing MCP tool methods
    def initialize_meta_analysis(self, input_data: InitializeMetaAnalysisInput) -> str:
        """Initialize a new meta-analysis session"""
        result = self.call_mcp_tool("initialize_meta_analysis", input_data.dict())
        if result.get("status") == "success":
            self.current_session_id = result.get("session_id")
            self.sessions[self.current_session_id] = {
                "name": input_data.name,
                "created": datetime.now().isoformat()
            }
            return f"✅ Meta-analysis session initialized!\n\nSession ID: {self.current_session_id}\nProject: {input_data.name}"
        return f"❌ Initialization failed: {result.get('error', 'Unknown error')}"
    
    def upload_study_data(self, input_data: UploadStudyDataInput) -> str:
        """Upload study data"""
        # Encode CSV content if not already encoded
        if not input_data.csv_content.startswith("data:"):
            encoded = base64.b64encode(input_data.csv_content.encode()).decode()
            input_data.csv_content = f"data:text/csv;base64,{encoded}"
        
        result = self.call_mcp_tool("upload_study_data", input_data.dict())
        if result.get("status") == "success":
            return f"✅ Data uploaded successfully!\n\nStudies: {result.get('n_studies', 'N/A')}\nValidation: {result.get('validation_summary', 'Passed')}"
        return f"❌ Upload failed: {result.get('error', 'Unknown error')}"
    
    def perform_meta_analysis(self, input_data: PerformMetaAnalysisInput) -> str:
        """Perform the meta-analysis"""
        result = self.call_mcp_tool("perform_meta_analysis", input_data.dict())
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

**Interpretation:** {summary.get('interpretation', 'See detailed report for full interpretation.')}
"""
        return f"❌ Analysis failed: {result.get('error', 'Unknown error')}"
    
    def generate_forest_plot(self, input_data: GenerateForestPlotInput) -> str:
        """Generate forest plot"""
        result = self.call_mcp_tool("generate_forest_plot", input_data.dict())
        if result.get("status") == "success":
            plot_data = result.get("plot", "")
            if plot_data:
                return f"✅ Forest plot generated!\n\n![Forest Plot](data:image/png;base64,{plot_data})"
            return "✅ Forest plot generated and saved to session folder."
        return f"❌ Plot generation failed: {result.get('error', 'Unknown error')}"
    
    def assess_publication_bias(self, input_data: AssessPublicationBiasInput) -> str:
        """Assess publication bias"""
        result = self.call_mcp_tool("assess_publication_bias", input_data.dict())
        if result.get("status") == "success":
            tests = result.get("tests", {})
            return f"""✅ Publication bias assessment completed!

**Egger's Test:**
- p-value: {tests.get('egger_p', 'N/A')}
- Interpretation: {tests.get('egger_interpretation', 'N/A')}

**Begg's Test:**
- p-value: {tests.get('begg_p', 'N/A')}
- Interpretation: {tests.get('begg_interpretation', 'N/A')}

**Overall Assessment:** {result.get('overall_assessment', 'See full report for details.')}
"""
        return f"❌ Bias assessment failed: {result.get('error', 'Unknown error')}"
    
    def generate_report(self, input_data: GenerateReportInput) -> str:
        """Generate comprehensive report"""
        result = self.call_mcp_tool("generate_report", input_data.dict())
        if result.get("status") == "success":
            report_path = result.get("report_path", "")
            return f"✅ Report generated successfully!\n\nFormat: {input_data.format.upper()}\nLocation: {report_path}"
        return f"❌ Report generation failed: {result.get('error', 'Unknown error')}"

# =====================================================================================
#  LLM & Multimodal Helpers
# =====================================================================================

def transcribe_audio_file(audio_path: str) -> str:
    """Transcribe an audio file using OpenAI Whisper if available."""
    try:
        if not OPENAI_API_KEY:
            return "Audio transcription requires OPENAI_API_KEY to be set."
        client = OpenAI(api_key=OPENAI_API_KEY)
        with open(audio_path, "rb") as af:
            result = client.audio.transcriptions.create(
                model="whisper-1",
                file=af
            )
        text = getattr(result, "text", None)
        return text or str(result)
    except Exception as e:
        return f"Audio transcription failed: {e}"


def analyze_video_file(video_path: str) -> Dict[str, Any]:
    """Extract lightweight metadata and sample frames count from a video using OpenCV."""
    try:
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            return {"status": "error", "message": "Unable to open video"}
        fps = cap.get(cv2.CAP_PROP_FPS) or 0.0
        frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH) or 0)
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT) or 0)

        sampled = 0
        step = int(max(fps * 2, 1)) if fps > 0 else 30
        for i in range(0, frame_count, step):
            cap.set(cv2.CAP_PROP_POS_FRAMES, i)
            success, _ = cap.read()
            if not success:
                break
            sampled += 1
            if sampled >= 10:
                break
        cap.release()
        duration_s = (frame_count / fps) if fps > 0 else None
        return {
            "status": "success",
            "fps": round(fps, 2) if fps else None,
            "duration_seconds": round(duration_s, 2) if duration_s else None,
            "frame_count": frame_count,
            "resolution": {"width": width, "height": height},
            "sampled_frames": sampled,
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}

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
        # Initialize tool wrapper and LLM
        tool_wrapper = EnhancedMCPToolWrapper()
        llm = get_llm_client(model_name)
        
        # Helper: extract session id from prior bot messages
        def _extract_session_id_from_history(h: list) -> Optional[str]:
            for (_u, b) in reversed(h):
                if not b:
                    continue
                # Look for pattern 'Session ID: <id>' in bot text
                m = re.search(r"Session ID:\s*([a-f0-9]{16,})", str(b), re.IGNORECASE)
                if m:
                    return m.group(1)
            return None

        # Helper: parse MCP server 'result' content wrapper
        def _parse_mcp_result_content(result_obj: dict) -> Optional[dict]:
            try:
                content = result_obj.get("content") or []
                if content and isinstance(content, list) and content[0].get("type") == "text":
                    return json.loads(content[0]["text"])  # payload from R
            except Exception:
                return None
            return None

        # Process any attached files
        file_context = ""
        if files:
            for file_path in files:
                ext = os.path.splitext(file_path)[1].lower()
                
                if ext == ".pdf":
                    # Extract PDF data
                    pdf_result = tool_wrapper.extract_pdf_data(file_path)
                    if pdf_result["status"] == "success":
                        file_context += f"\n\nPDF Analysis:\n{pdf_result['text'][:2000]}..."
                        if pdf_result.get("extracted_data"):
                            file_context += f"\n\nExtracted Data: {json.dumps(pdf_result['extracted_data'], indent=2)}"
                
                elif ext in [".png", ".jpg", ".jpeg", ".gif"]:
                    # Analyze image
                    img_result = tool_wrapper.analyze_figure(file_path)
                    if img_result["status"] == "success":
                        file_context += f"\n\nImage Analysis: {img_result['message']}"
                
                elif ext in [".csv", ".xlsx", ".xls"]:
                    # Process data files
                    df = pd.read_csv(file_path) if ext == ".csv" else pd.read_excel(file_path)
                    file_context += f"\n\nData Preview ({len(df)} rows x {len(df.columns)} columns):\n{df.head(5).to_string()}"
                
                elif ext in [".mp3", ".wav", ".m4a", ".flac", ".ogg"]:
                    # Transcribe audio content when API key is available
                    transcript = transcribe_audio_file(file_path)
                    file_context += f"\n\nAudio Transcript (excerpt):\n{(transcript or '')[:1000]}"
                
                elif ext in [".mp4", ".mov", ".avi", ".mkv"]:
                    # Analyze basic video metadata and sampling
                    vid_info = analyze_video_file(file_path)
                    if vid_info.get("status") == "success":
                        file_context += (
                            f"\n\nVideo Info: FPS={vid_info.get('fps')}, Duration(s)={vid_info.get('duration_seconds')}, "
                            f"Frames={vid_info.get('frame_count')}, Resolution={vid_info.get('resolution')}, "
                            f"SampledFrames={vid_info.get('sampled_frames')}"
                        )
                    else:
                        file_context += f"\n\nVideo analysis error: {vid_info.get('message')}"
                    # Read data file
                    try:
                        if ext == ".csv":
                            df = pd.read_csv(file_path)
                        else:
                            df = pd.read_excel(file_path)
                        file_context += f"\n\nData File ({ext}):\nShape: {df.shape}\nColumns: {list(df.columns)}\nFirst 5 rows:\n{df.head().to_string()}"
                    except Exception as e:
                        file_context += f"\n\nError reading {ext} file: {str(e)}"
        
        # Build dynamic system context: session status + Cochrane guidance
        dynamic_context_lines: List[str] = []
        session_id = _extract_session_id_from_history(history[:-1])
        if session_id:
            status_raw = tool_wrapper.call_mcp_tool(
                "get_session_status",
                {"session_id": session_id}
            )
            status = _parse_mcp_result_content(status_raw) or {}
            if status.get("status") == "success":
                cfg = (status.get("configuration") or {})
                n_studies = ((status.get("data_info") or {}).get("n_studies"))
                dynamic_context_lines.append("[SESSION]")
                dynamic_context_lines.append(f"id={status.get('session_id')}")
                dynamic_context_lines.append(f"stage={status.get('workflow_stage')}")
                dynamic_context_lines.append(f"study_type={cfg.get('study_type')}")
                dynamic_context_lines.append(f"effect_measure={cfg.get('effect_measure')}")
                dynamic_context_lines.append(f"analysis_model={cfg.get('analysis_model')}")
                if n_studies is not None:
                    dynamic_context_lines.append(f"n_studies={n_studies}")

                # Minimal Cochrane-aligned hints (runtime)
                guidance_hints: List[str] = []
                if isinstance(n_studies, int) and n_studies < 10:
                    guidance_hints.append(
                        "Publication bias tests have low power with <10 studies; discuss risk qualitatively."
                    )
                if (cfg.get('analysis_model') or '').lower() == 'fixed':
                    guidance_hints.append(
                        "Fixed-effect assumes one true effect; if clinical/methodological diversity exists, prefer random-effects."
                    )
                if (cfg.get('effect_measure') or '').upper() in {"MD", "SMD"}:
                    guidance_hints.append(
                        "For continuous outcomes: use MD when scales are identical; SMD when scales differ."
                    )
                if (cfg.get('effect_measure') or '').upper() in {"OR", "RR"}:
                    guidance_hints.append(
                        "For binary outcomes: ensure data include event counts and totals (event1,n1,event2,n2)."
                    )
                if guidance_hints:
                    dynamic_context_lines.append("[COCHRANE_HINTS]")
                    for gh in guidance_hints:
                        dynamic_context_lines.append(f"- {gh}")

        dynamic_context = "\n".join(dynamic_context_lines) if dynamic_context_lines else ""

        # Combine prompt with file context
        full_prompt = text_prompt
        if file_context:
            full_prompt += file_context
        
        # Create tools for the agent
        tools = [
            StructuredTool.from_function(
                func=tool_wrapper.initialize_meta_analysis,
                name="initialize_meta_analysis",
                description="Start a new meta-analysis session",
                args_schema=InitializeMetaAnalysisInput
            ),
            StructuredTool.from_function(
                func=tool_wrapper.upload_study_data,
                name="upload_study_data",
                description="Upload study data for analysis",
                args_schema=UploadStudyDataInput
            ),
            StructuredTool.from_function(
                func=tool_wrapper.perform_meta_analysis,
                name="perform_meta_analysis",
                description="Execute the meta-analysis",
                args_schema=PerformMetaAnalysisInput
            ),
            StructuredTool.from_function(
                func=tool_wrapper.generate_forest_plot,
                name="generate_forest_plot",
                description="Generate forest plot visualization",
                args_schema=GenerateForestPlotInput
            ),
            StructuredTool.from_function(
                func=tool_wrapper.assess_publication_bias,
                name="assess_publication_bias",
                description="Assess publication bias",
                args_schema=AssessPublicationBiasInput
            ),
            StructuredTool.from_function(
                func=tool_wrapper.generate_report,
                name="generate_report",
                description="Generate comprehensive report",
                args_schema=GenerateReportInput
            )
        ]
        
        # Create the agent
        # Include dynamic context as a second system message when available
        messages_spec = [
            ("system", SYSTEM_PROMPT),
        ]
        if dynamic_context:
            messages_spec.append(("system", "{dynamic_context}"))
        messages_spec.extend([
            MessagesPlaceholder(variable_name="chat_history"),
            ("human", "{input}"),
            MessagesPlaceholder(variable_name="agent_scratchpad"),
        ])
        prompt = ChatPromptTemplate.from_messages(messages_spec)
        
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
        if dynamic_context:
            response = agent_executor.invoke({"input": full_prompt, "dynamic_context": dynamic_context})
        else:
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
                avatar_images=(None, "🤖")
            )
            
            multimodal_input = gr.MultimodalTextbox(
                file_types=["image", "video", "audio", "text"],
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

# =====================================================================================
#  Launch Configuration
# =====================================================================================

if __name__ == "__main__":
    # Check for API keys
    if not AVAILABLE_MODELS:
        print("⚠️  Warning: No API keys configured!")
        print("Please set OPENAI_API_KEY or ANTHROPIC_API_KEY environment variables")
    
    # Create necessary directories
    Path("outputs").mkdir(exist_ok=True)
    Path("sessions").mkdir(exist_ok=True)
    
    # Launch the app
    demo.launch(
        server_name=os.getenv("GRADIO_SERVER_NAME", "0.0.0.0"),
        server_port=int(os.getenv("GRADIO_SERVER_PORT", 7860)),
        share=False,
        debug=True
    )