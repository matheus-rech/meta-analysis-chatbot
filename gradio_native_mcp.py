"""
Gradio-Native MCP Server Implementation with R Integration
Following Gradio's official MCP patterns while maintaining R backend
"""

import os
import json
import subprocess
import base64
import tempfile
import re
from typing import Dict, Any, List, Optional
from pathlib import Path

import gradio as gr
from gradio import ChatMessage
import pandas as pd
import numpy as np

# LLM imports
try:
    import openai
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False

try:
    import anthropic
    ANTHROPIC_AVAILABLE = True
except ImportError:
    ANTHROPIC_AVAILABLE = False


class RIntegrationMCPServer:
    """
    Native Gradio MCP Server that maintains R script integration
    Following patterns from https://www.gradio.app/guides/building-mcp-server-with-gradio
    """
    
    def __init__(self):
        self.sessions = {}
        self.current_session_id = None
        # Resolve scripts path locally first, then Docker fallback
        self.scripts_path = Path(__file__).parent / "scripts"
        self.mcp_tools_path = self.scripts_path / "entry" / "mcp_tools.R"
        
        # Verify R scripts exist
        if not self.mcp_tools_path.exists():
            # Try alternative path for Docker
            alt_path = Path("/app/scripts/entry/mcp_tools.R")
            if alt_path.exists():
                self.scripts_path = Path("/app/scripts")
                self.mcp_tools_path = alt_path
            else:
                raise FileNotFoundError(f"R scripts not found at {self.mcp_tools_path}")
    
    def execute_r_tool(self, tool_name: str, args: Dict[str, Any]) -> Dict[str, Any]:
        """Execute R script tool maintaining compatibility with existing R backend"""
        
        # Prepare session path
        sess_id = args.get("session_id", "")
        if sess_id and sess_id in self.sessions:
            session_path = self.sessions[sess_id]["path"]
        else:
            session_path = tempfile.mkdtemp(prefix="meta_analysis_")
        
        # Write args to a temp json file to avoid CLI arg-length limits
        fd, args_file = tempfile.mkstemp(suffix=".json")
        os.close(fd)
        with open(args_file, "w", encoding="utf-8") as f:
            json.dump(args, f)
        
        rscript = os.getenv("RSCRIPT_BIN", "Rscript")
        timeout = int(os.getenv("RSCRIPT_TIMEOUT_SEC", "300"))
        debug_r = os.getenv("DEBUG_R") == "1"
        
        try:
            # Execute R script
            result = subprocess.run(
                [rscript, "--vanilla", str(self.mcp_tools_path), tool_name, args_file, session_path],
                capture_output=True,
                text=True,
                encoding="utf-8",
                timeout=timeout
            )
        except subprocess.TimeoutExpired:
            os.remove(args_file)
            return {"status": "error", "error": "R script execution timed out"}
        except Exception as e:
            os.remove(args_file)
            return {"status": "error", "error": str(e)}
        finally:
            try:
                if os.path.exists(args_file):
                    os.remove(args_file)
            except Exception:
                pass
        
        if result.returncode != 0:
            resp = {"status": "error", "error": "R script failed"}
            if debug_r:
                resp["stderr"] = (result.stderr or "").strip()
                resp["stdout"] = (result.stdout or "").strip()
            return resp
        
        # Parse JSON output from R
        try:
            return json.loads(result.stdout.strip())
        except json.JSONDecodeError:
            resp = {"status": "error", "error": "Invalid JSON from R", "raw_output": (result.stdout or "").strip()}
            if debug_r:
                resp["stderr"] = (result.stderr or "").strip()
            return resp
    
    # MCP Tool Implementations (wrapping R scripts)
    
    def initialize_meta_analysis(
        self,
        name: str,
        study_type: str = "clinical_trial",
        effect_measure: str = "OR",
        analysis_model: str = "random"
    ) -> Dict[str, Any]:
        """Initialize a new meta-analysis session"""
        
        result = self.execute_r_tool("initialize_meta_analysis", {
            "name": name,
            "study_type": study_type,
            "effect_measure": effect_measure,
            "analysis_model": analysis_model
        })
        
        # Extract session ID if successful
        if result.get("status") == "success" and "session_id" in result:
            session_id = result["session_id"]
            self.current_session_id = session_id
            self.sessions[session_id] = {
                "name": name,
                "path": result.get("session_path", tempfile.mkdtemp()),
                "config": {
                    "study_type": study_type,
                    "effect_measure": effect_measure,
                    "analysis_model": analysis_model
                }
            }
        
        return result
    
    def upload_study_data(
        self,
        data: pd.DataFrame = None,
        csv_text: str = None,
        session_id: str = None,
        validation_level: str = "comprehensive"
    ) -> Dict[str, Any]:
        """Upload study data with native Gradio file handling"""
        
        # Use current session if not provided
        if not session_id:
            session_id = self.current_session_id
        
        if not session_id:
            return {"status": "error", "error": "No active session. Please initialize first."}
        
        # Convert DataFrame to CSV if provided
        if data is not None:
            csv_text = data.to_csv(index=False)
        
        if not csv_text:
            return {"status": "error", "error": "No data provided"}
        
        # Encode for R script
        data_content = base64.b64encode(csv_text.encode()).decode()
        
        return self.execute_r_tool("upload_study_data", {
            "session_id": session_id,
            "data_content": data_content,
            "data_format": "csv",
            "validation_level": validation_level
        })
    
    def perform_meta_analysis(
        self,
        session_id: str = None,
        heterogeneity_test: bool = True,
        publication_bias: bool = True,
        sensitivity_analysis: bool = False
    ) -> Dict[str, Any]:
        """Perform meta-analysis"""
        
        if not session_id:
            session_id = self.current_session_id
        
        if not session_id:
            return {"status": "error", "error": "No active session"}
        
        return self.execute_r_tool("perform_meta_analysis", {
            "session_id": session_id,
            "heterogeneity_test": heterogeneity_test,
            "publication_bias": publication_bias,
            "sensitivity_analysis": sensitivity_analysis
        })
    
    def assess_publication_bias(
        self,
        session_id: str = None,
        methods: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Assess publication bias using R backend"""
        if not session_id:
            session_id = self.current_session_id
        if not session_id:
            return {"status": "error", "error": "No active session"}
        if methods is None:
            methods = ["funnel_plot", "egger_test"]
        return self.execute_r_tool(
            "assess_publication_bias",
            {"session_id": session_id, "methods": methods},
        )
    
    def generate_forest_plot(
        self,
        session_id: str = None,
        plot_style: str = "modern",
        confidence_level: float = 0.95,
        engine: str = "metafor",
    ) -> Dict[str, Any]:
        """Generate forest plot"""
        
        if not session_id:
            session_id = self.current_session_id
        
        if not session_id:
            return {"status": "error", "error": "No active session"}
        
        result = self.execute_r_tool(
            "generate_forest_plot",
            {
            "session_id": session_id,
            "plot_style": plot_style,
                "confidence_level": confidence_level,
                "engine": engine,
            },
        )
        
        # If successful, try to load the image
        if result.get("status") == "success":
            plot_path_str = result.get("forest_plot_path") or result.get("plot_file")
            if plot_path_str:
                session_path = self.sessions[session_id]["path"]
                plot_path = Path(plot_path_str)
                if not plot_path.is_absolute():
                    plot_path = Path(session_path) / "results" / plot_path_str
                if plot_path.exists():
                    result["plot_path"] = str(plot_path)
        
        return result
    
    def generate_report(
        self,
        session_id: str = None,
        format: str = "html",
        include_code: bool = False
    ) -> Dict[str, Any]:
        """Generate comprehensive report"""
        
        if not session_id:
            session_id = self.current_session_id
        
        if not session_id:
            return {"status": "error", "error": "No active session"}
        
        return self.execute_r_tool("generate_report", {
            "session_id": session_id,
            "format": format,
            "include_code": include_code
        })

    def get_session_status(self, session_id: str = None) -> Dict[str, Any]:
        """Get session status including paths to results"""
        if not session_id:
            session_id = self.current_session_id
        if not session_id:
            return {"status": "error", "error": "No active session"}
        return self.execute_r_tool("get_session_status", {"session_id": session_id})

    def health_check(self, detailed: bool = False) -> Dict[str, Any]:
        """Verify R environment and tool availability"""
        return self.execute_r_tool("health_check", {"detailed": detailed})


class MetaAnalysisChatbot:
    """
    Chatbot interface using Gradio's native patterns
    Following https://www.gradio.app/guides/building-an-mcp-client-with-gradio
    """
    
    def __init__(self, mcp_server: RIntegrationMCPServer):
        self.mcp_server = mcp_server
        self.setup_llm()
    
    def setup_llm(self):
        """Setup LLM client with multi-provider support (OpenAI/DeepSeek/Ollama/OpenRouter/Anthropic)."""
        self.llm_client = None
        self.llm_type = None

        provider_hint = os.getenv("LLM_PROVIDER", "").lower()

        # Anthropic first if explicitly requested
        if (provider_hint == "anthropic" or provider_hint == "claude") and ANTHROPIC_AVAILABLE and os.getenv("ANTHROPIC_API_KEY"):
            self.llm_client = anthropic.Anthropic()
            self.llm_model = os.getenv("ANTHROPIC_MODEL", "claude-3-5-sonnet-20240620")
            self.llm_type = "anthropic"
            return

        # OpenAI-compatible: native OpenAI, OpenRouter, Ollama, DeepSeek via base_url + api_key
        if OPENAI_AVAILABLE:
            base_url = (
                os.getenv("OPENAI_BASE_URL")
                or os.getenv("DEEPSEEK_BASE_URL")
                or os.getenv("OLLAMA_BASE_URL")
            )

            # API key resolution (OpenAI first, then DeepSeek, then generic)
            api_key = (
                os.getenv("OPENAI_API_KEY")
                or os.getenv("DEEPSEEK_API_KEY")
                or os.getenv("OPENAI_COMPAT_API_KEY")
                or os.getenv("OLLAMA_API_KEY")
            )

            client_kwargs = {}
            if base_url:
                client_kwargs["base_url"] = base_url.rstrip("/")
            if api_key:
                client_kwargs["api_key"] = api_key

            # Default to OpenAI cloud if no base_url specified
            try:
                self.llm_client = openai.OpenAI(**client_kwargs)
                # Prefer user-specified model; fallback sequence
                self.llm_model = (
                    os.getenv("OPENAI_MODEL")
                    or os.getenv("DEEPSEEK_MODEL")
                    or os.getenv("OLLAMA_MODEL")
                    or "gpt-4.1"
                )
                # Support o3/o4.1 selection by env
                # Examples: OPENAI_MODEL=o3-mini / gpt-4.1 / gpt-4o
            self.llm_type = "openai"
                return
            except Exception:
                pass

        # Anthropic fallback if available and key present
        if ANTHROPIC_AVAILABLE and os.getenv("ANTHROPIC_API_KEY"):
            self.llm_client = anthropic.Anthropic()
            self.llm_model = os.getenv("ANTHROPIC_MODEL", "claude-3-opus-20240229")
            self.llm_type = "anthropic"
            return

        # No provider configured
            self.llm_client = None
            self.llm_type = None
    
    def process_message(self, message: str, history: List[ChatMessage], auto_tools: bool = True) -> str:
        """Process user message with LLM and MCP tools"""
        
        if not self.llm_client:
            return "❌ No LLM configured. Please set OPENAI_API_KEY or ANTHROPIC_API_KEY"
        
        # Build conversation context
        system_prompt = """You are an expert meta-analysis assistant. You help researchers conduct 
        comprehensive meta-analyses using R-based statistical tools.
        
        Available tools:
        1. initialize_meta_analysis(name, study_type, effect_measure, analysis_model)
        2. upload_study_data(csv_text, session_id, validation_level)
        3. perform_meta_analysis(session_id, heterogeneity_test, publication_bias, sensitivity_analysis)
        4. generate_forest_plot(session_id, plot_style, confidence_level)
        5. generate_report(session_id, format, include_code)
        
        Guide users through the workflow and explain statistical concepts when needed."""
        
        # Prepare messages for LLM
        messages = [{"role": "system", "content": system_prompt}]
        
        for msg in history:
            if msg["role"] == "user":
                messages.append({"role": "user", "content": msg["content"]})
            elif msg["role"] == "assistant":
                messages.append({"role": "assistant", "content": msg["content"]})
        
        messages.append({"role": "user", "content": message})
        
        # Get LLM response
        try:
            if self.llm_type == "openai":
                response = self.llm_client.chat.completions.create(
                    model=self.llm_model,
                    messages=messages,
                    temperature=0.7,
                    max_tokens=2000
                )
                ai_response = response.choices[0].message.content
            else:  # anthropic
                response = self.llm_client.messages.create(
                    model=self.llm_model,
                    messages=messages[1:],  # Skip system message for format
                    system=system_prompt,
                    max_tokens=2000,
                    temperature=0.7
                )
                ai_response = response.content[0].text
            
            if auto_tools:
            # Check if we should execute any tools based on the conversation
            tool_results = self.detect_and_execute_tools(message, ai_response)
            if tool_results:
                ai_response += "\n\n" + tool_results
            
            return ai_response
            
        except Exception as e:
            return f"❌ Error: {str(e)}"
    
    def detect_and_execute_tools(self, user_message: str, ai_response: str) -> str:
        """Detect intent and execute appropriate MCP tools"""
        
        results = []
        message_lower = user_message.lower()
        
        # Initialize session
        if any(word in message_lower for word in ["start", "begin", "initialize", "new"]):
            if not self.mcp_server.current_session_id:
                result = self.mcp_server.initialize_meta_analysis(
                    name="Meta-Analysis Project",
                    study_type="clinical_trial",
                    effect_measure="OR",
                    analysis_model="random"
                )
                if result.get("status") == "success":
                    results.append(f"✅ Session initialized: {result.get('session_id', 'unknown')}")
        
        # Upload data
        if "csv" in message_lower or "data" in message_lower:
            # Extract CSV data if present
            if "```" in user_message:
                csv_start = user_message.find("```") + 3
                csv_end = user_message.find("```", csv_start)
                if csv_end > csv_start:
                    csv_text = user_message[csv_start:csv_end].strip()
                    if csv_text.startswith("csv\n"):
                        csv_text = csv_text[4:]
                    
                    result = self.mcp_server.upload_study_data(
                        csv_text=csv_text,
                        validation_level="comprehensive"
                    )
                    if result.get("status") == "success":
                        results.append("✅ Data uploaded successfully")
        
        # Run analysis
        if any(word in message_lower for word in ["analyze", "analysis", "run", "perform"]):
            result = self.mcp_server.perform_meta_analysis()
            if result.get("status") == "success":
                results.append("📊 Analysis completed")
        
        # Generate plot
        if any(word in message_lower for word in ["forest", "plot", "visualiz"]):
            result = self.mcp_server.generate_forest_plot()
            if result.get("status") == "success":
                results.append("📈 Forest plot generated")
        
        # Generate report
        if any(word in message_lower for word in ["report", "summary", "document"]):
            result = self.mcp_server.generate_report()
            if result.get("status") == "success":
                results.append("📄 Report generated")
        
        return "\n".join(results) if results else ""


def create_gradio_app():
    """
    Create Gradio app following native MCP patterns
    Combines chatbot interface with MCP server tools
    """
    
    # Initialize MCP server and chatbot
    mcp_server = RIntegrationMCPServer()
    chatbot = MetaAnalysisChatbot(mcp_server)
    
    with gr.Blocks(title="🧬 Meta-Analysis Assistant", theme=gr.themes.Soft()) as app:
        gr.Markdown(
            """
        # 🧬 Meta-Analysis AI Assistant
            A single-chat interface that guides, teaches, and executes meta-analyses.
            """
        )

                chatbot_ui = gr.Chatbot(
            height=640,
                    type="messages",
                    show_label=False,
            avatar_images=(None, "🤖"),
        )

        msg_input = gr.MultimodalTextbox(
            file_types=[".csv", ".xlsx", ".png", ".jpg", ".jpeg"],
            placeholder="Ask a question, upload your data, or request synthetic data...",
            label="",
            submit_btn=True,
        )

                session_info = gr.Textbox(
            label="Session",
                    value="No active session",
            interactive=False,
        )
        
        # Event handlers (UI only; hide from API/MCP)
        def _encode_image_to_data_uri(path: str) -> Optional[str]:
            try:
                with open(path, "rb") as f:
                    b64 = base64.b64encode(f.read()).decode()
                return f"data:image/png;base64,{b64}"
            except Exception:
                return None

        def _maybe_initialize():
            if not mcp_server.current_session_id:
                mcp_server.initialize_meta_analysis(
                    name="Meta-Analysis Project",
                    study_type="clinical_trial",
                    effect_measure="OR",
                    analysis_model="random",
                )

        def chat_response_mm(message, history):
            if not message:
                return history, None, session_info.value

            text = message.get("text") or ""
            files = message.get("files") or []

            # Add user message
            history.append(ChatMessage(role="user", content=text))

            # Handle file uploads (CSV/XLSX)
            upload_msg = ""
            if files:
                for fp in files:
                    if str(fp).lower().endswith(".csv"):
                        try:
                            df = pd.read_csv(fp)
                            _maybe_initialize()
                            up_res = mcp_server.upload_study_data(data=df)
                            if up_res.get("status") == "success":
                                upload_msg += "\n✅ Data uploaded successfully."
                            else:
                                upload_msg += f"\n❌ Upload failed: {up_res.get('error','unknown')}"
                        except Exception as e:
                            upload_msg += f"\n❌ Upload error: {e}"
                    elif str(fp).lower().endswith((".xlsx", ".xls")):
                        try:
                            df = pd.read_excel(fp)
                            _maybe_initialize()
                            up_res = mcp_server.upload_study_data(data=df)
                            upload_msg += "\n✅ Excel uploaded successfully." if up_res.get("status") == "success" else "\n❌ Upload failed."
                        except Exception as e:
                            upload_msg += f"\n❌ Upload error: {e}"

            # Synthetic data request
            synth_msg = ""
            if re.search(r"\b(simulate|synthetic)\b", text, re.I):
                _maybe_initialize()
                m = re.search(r"\b(\d{1,4})\b", text)
                n = int(m.group(1)) if m else 20
                measure = "OR"
                for cand in ["OR", "RR", "MD", "SMD", "PROP", "MEAN"]:
                    if cand.lower() in text.lower():
                        measure = cand
                        break
                # simple binary dataset for OR
                if measure in ("OR", "RR"):
                    rng = np.random.default_rng(42)
                    df = pd.DataFrame(
                        {
                            "study": [f"S{i+1}" for i in range(n)],
                            "event1": rng.integers(1, 20, size=n),
                            "n1": rng.integers(50, 200, size=n),
                            "event2": rng.integers(1, 25, size=n),
                            "n2": rng.integers(50, 220, size=n),
                        }
                    )
                else:
                    # generic effect_size/se
                    rng = np.random.default_rng(42)
                    df = pd.DataFrame(
                        {
                            "study": [f"S{i+1}" for i in range(n)],
                            "effect_size": rng.normal(0, 0.3, size=n),
                            "se": rng.uniform(0.05, 0.2, size=n),
                        }
                    )
                up_res = mcp_server.upload_study_data(data=df)
                synth_msg = (
                    "\n✅ Synthetic data generated and uploaded."
                    if up_res.get("status") == "success"
                    else "\n❌ Synthetic upload failed."
                )

            # Tool intents
            tool_feedback = ""
            low = text.lower()
            if any(k in low for k in ["start", "begin", "initialize", "new session"]):
                init_res = mcp_server.initialize_meta_analysis(
                    name="Guided Session",
                    study_type="clinical_trial",
                    effect_measure="OR",
                    analysis_model="random",
                )
                if init_res.get("status") == "success":
                    tool_feedback += "\n✅ Session initialized."
            if any(k in low for k in ["analy", "run", "perform"]):
                ana = mcp_server.perform_meta_analysis()
                if ana.get("status") == "success":
                    summ = ana.get("summary") or ana
                    tool_feedback += f"\n📊 Analysis complete. k={summ.get('study_count', 'N/A')}"
            image_to_show = None
            if any(k in low for k in ["forest", "plot"]):
                plot_res = mcp_server.generate_forest_plot(engine="metafor")
                if plot_res.get("status") == "success":
                    pth = plot_res.get("plot_path") or plot_res.get("forest_plot_path")
                    if pth and Path(pth).exists():
                        uri = _encode_image_to_data_uri(pth)
                        if uri:
                            image_to_show = uri
                            tool_feedback += "\n📈 Forest plot generated."
            if any(k in low for k in ["bias", "egger", "funnel"]):
                bias = mcp_server.assess_publication_bias()
                if bias.get("status") == "success":
                    tool_feedback += "\n🧪 Publication bias assessed."
            if "report" in low:
                rep = mcp_server.generate_report(format="html")
                if rep.get("status") == "success":
                    tool_feedback += "\n📄 Report generated (HTML)."

            # LLM guidance (no auto tools)
            guidance = chatbot.process_message(text, history, auto_tools=False)
            guidance += upload_msg + synth_msg + tool_feedback
            history.append(ChatMessage(role="assistant", content=guidance))

            # Update session label
            sess_lbl = (
                f"Active session: {mcp_server.current_session_id[:8]}..."
                if mcp_server.current_session_id
                else "No active session"
            )

            return history, None, sess_lbl
        
        # Chat events (single-chat UI)
        msg_input.submit(
            chat_response_mm,
            [msg_input, chatbot_ui],
            [chatbot_ui, msg_input, session_info],
            show_api=False,
        )

        # API-only MCP tool endpoints
        # 1) Initialize meta-analysis
        def initialize_meta_analysis(name: str,
                                     study_type: str = "clinical_trial",
                                     effect_measure: str = "OR",
                                     analysis_model: str = "random") -> Dict[str, Any]:
            """Initialize a new meta-analysis session"""
            return mcp_server.initialize_meta_analysis(name, study_type, effect_measure, analysis_model)

        gr.on(
            None,
            initialize_meta_analysis,
            inputs=[
                gr.Textbox(label="name", visible=False),
                gr.Dropdown(["clinical_trial", "observational", "diagnostic"], label="study_type", value="clinical_trial", visible=False),
                gr.Dropdown(["OR", "RR", "MD", "SMD", "HR"], label="effect_measure", value="OR", visible=False),
                gr.Dropdown(["fixed", "random", "auto"], label="analysis_model", value="random", visible=False),
            ],
            outputs=gr.JSON(label="result", visible=False),
            api_name="initialize_meta_analysis",
        )

        # 2) Upload study data
        def upload_study_data(session_id: str, csv_text: str, validation_level: str = "comprehensive") -> Dict[str, Any]:
            """Upload study data for analysis (CSV text)"""
            return mcp_server.upload_study_data(csv_text=csv_text, session_id=session_id, validation_level=validation_level)

        gr.on(
            None,
            upload_study_data,
            inputs=[
                gr.Textbox(label="session_id", visible=False),
                gr.Textbox(label="csv_text", lines=8, visible=False),
                gr.Dropdown(["basic", "comprehensive"], label="validation_level", value="comprehensive", visible=False),
            ],
            outputs=gr.JSON(label="result", visible=False),
            api_name="upload_study_data",
        )

        # 3) Perform meta-analysis
        def perform_meta_analysis(session_id: str,
                                  heterogeneity_test: bool = True,
                                  publication_bias: bool = True,
                                  sensitivity_analysis: bool = False) -> Dict[str, Any]:
            """Run statistical meta-analysis"""
            return mcp_server.perform_meta_analysis(
                session_id=session_id,
                heterogeneity_test=heterogeneity_test,
                publication_bias=publication_bias,
                sensitivity_analysis=sensitivity_analysis,
            )

        gr.on(
            None,
            perform_meta_analysis,
            inputs=[
                gr.Textbox(label="session_id", visible=False),
                gr.Checkbox(label="heterogeneity_test", value=True, visible=False),
                gr.Checkbox(label="publication_bias", value=True, visible=False),
                gr.Checkbox(label="sensitivity_analysis", value=False, visible=False),
            ],
            outputs=gr.JSON(label="result", visible=False),
            api_name="perform_meta_analysis",
        )

        # 4) Generate forest plot
        def generate_forest_plot(session_id: str,
                                 plot_style: str = "modern",
                                 confidence_level: float = 0.95) -> Dict[str, Any]:
            """Generate a forest plot visualization"""
            return mcp_server.generate_forest_plot(
                session_id=session_id,
                plot_style=plot_style,
                confidence_level=confidence_level,
            )

        gr.on(
            None,
            generate_forest_plot,
            inputs=[
                gr.Textbox(label="session_id", visible=False),
                gr.Dropdown(["classic", "modern", "journal_specific"], label="plot_style", value="modern", visible=False),
                gr.Slider(0.90, 0.99, value=0.95, label="confidence_level", visible=False),
            ],
            outputs=gr.JSON(label="result", visible=False),
            api_name="generate_forest_plot",
        )

        # 5) Assess publication bias
        def assess_publication_bias(session_id: str, methods: str = "funnel_plot, egger_test") -> Dict[str, Any]:
            """Assess publication bias (methods as comma-separated list)"""
            methods_list = [m.strip() for m in methods.split(",") if m.strip()]
            return mcp_server.assess_publication_bias(session_id=session_id, methods=methods_list)

        gr.on(
            None,
            assess_publication_bias,
            inputs=[
                gr.Textbox(label="session_id", visible=False),
                gr.Textbox(label="methods", value="funnel_plot, egger_test", visible=False),
            ],
            outputs=gr.JSON(label="result", visible=False),
            api_name="assess_publication_bias",
        )

        # 6) Generate report
        def generate_report(session_id: str, format: str = "html", include_code: bool = False) -> Dict[str, Any]:
            """Generate a comprehensive analysis report"""
            return mcp_server.generate_report(session_id=session_id, format=format, include_code=include_code)

        gr.on(
            None,
            generate_report,
            inputs=[
                gr.Textbox(label="session_id", visible=False),
                gr.Dropdown(["html", "pdf", "word"], label="format", value="html", visible=False),
                gr.Checkbox(label="include_code", value=False, visible=False),
            ],
            outputs=gr.JSON(label="result", visible=False),
            api_name="generate_report",
        )

        # 7) Get session status
        def get_session_status(session_id: str) -> Dict[str, Any]:
            """Get session status and file paths"""
            return mcp_server.get_session_status(session_id=session_id)

        gr.on(
            None,
            get_session_status,
            inputs=[gr.Textbox(label="session_id", visible=False)],
            outputs=gr.JSON(label="result", visible=False),
            api_name="get_session_status",
        )

        # 8) Health check
        def health_check(detailed: bool = False) -> Dict[str, Any]:
            """Verify R environment"""
            return mcp_server.health_check(detailed=detailed)

        gr.on(
            None,
            health_check,
            inputs=[gr.Checkbox(label="detailed", value=False, visible=False)],
            outputs=gr.JSON(label="result", visible=False),
            api_name="health_check",
        )
    
    return app


if __name__ == "__main__":
    print("🚀 Starting Meta-Analysis Assistant with Native Gradio MCP...")
    print("📚 Following Gradio's official MCP patterns")
    print("🔬 R backend integration maintained")
    
    # Check for LLM API keys
    if not os.getenv("OPENAI_API_KEY") and not os.getenv("ANTHROPIC_API_KEY"):
        print("⚠️ Warning: No LLM API key found. Chatbot features will be limited.")
        print("Set OPENAI_API_KEY or ANTHROPIC_API_KEY for full functionality.")
    
    app = create_gradio_app()
    app.launch(server_name="0.0.0.0", server_port=7860, mcp_server=True)