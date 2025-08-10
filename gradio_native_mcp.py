"""
Gradio-Native MCP Server Implementation with R Integration
Following Gradio's official MCP patterns while maintaining R backend
"""

import os
import json
import subprocess
import base64
import tempfile
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
        self.scripts_path = Path(__file__).parent.parent.parent / "scripts"
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
        session_path = args.get("session_id", "")
        if session_path and session_path in self.sessions:
            session_path = self.sessions[session_path]["path"]
        else:
            session_path = tempfile.mkdtemp(prefix="meta_analysis_")
        
        # Prepare R script arguments
        r_args = [
            str(self.mcp_tools_path),
            tool_name,
            json.dumps(args),
            session_path
        ]
        
        try:
            # Execute R script
            result = subprocess.run(
                ["Rscript", "--vanilla"] + r_args,
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode != 0:
                return {
                    "status": "error",
                    "error": f"R script failed: {result.stderr}"
                }
            
            # Parse JSON output from R
            try:
                output = json.loads(result.stdout.strip())
                return output
            except json.JSONDecodeError:
                return {
                    "status": "success",
                    "output": result.stdout
                }
                
        except subprocess.TimeoutExpired:
            return {
                "status": "error",
                "error": "R script execution timed out"
            }
        except Exception as e:
            return {
                "status": "error",
                "error": str(e)
            }
    
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
    
    def generate_forest_plot(
        self,
        session_id: str = None,
        plot_style: str = "modern",
        confidence_level: float = 0.95
    ) -> Dict[str, Any]:
        """Generate forest plot"""
        
        if not session_id:
            session_id = self.current_session_id
        
        if not session_id:
            return {"status": "error", "error": "No active session"}
        
        result = self.execute_r_tool("generate_forest_plot", {
            "session_id": session_id,
            "plot_style": plot_style,
            "confidence_level": confidence_level
        })
        
        # If successful, try to load the image
        if result.get("status") == "success" and result.get("plot_file"):
            session_path = self.sessions[session_id]["path"]
            plot_path = Path(session_path) / "results" / result["plot_file"]
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


class MetaAnalysisChatbot:
    """
    Chatbot interface using Gradio's native patterns
    Following https://www.gradio.app/guides/building-an-mcp-client-with-gradio
    """
    
    def __init__(self, mcp_server: RIntegrationMCPServer):
        self.mcp_server = mcp_server
        self.setup_llm()
    
    def setup_llm(self):
        """Setup LLM client (OpenAI or Anthropic)"""
        if OPENAI_AVAILABLE and os.getenv("OPENAI_API_KEY"):
            self.llm_client = openai.OpenAI()
            self.llm_model = "gpt-4-turbo-preview"
            self.llm_type = "openai"
        elif ANTHROPIC_AVAILABLE and os.getenv("ANTHROPIC_API_KEY"):
            self.llm_client = anthropic.Anthropic()
            self.llm_model = "claude-3-opus-20240229"
            self.llm_type = "anthropic"
        else:
            self.llm_client = None
            self.llm_type = None
    
    def process_message(self, message: str, history: List[ChatMessage]) -> str:
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
    
    with gr.Blocks(title="🧬 Meta-Analysis Assistant (Native MCP)", theme=gr.themes.Soft()) as app:
        
        gr.Markdown("""
        # 🧬 Meta-Analysis AI Assistant
        ### Native Gradio MCP Implementation with R Backend
        
        This implementation follows [Gradio's official MCP patterns](https://www.gradio.app/guides/building-mcp-server-with-gradio)
        while maintaining full R integration for statistical analysis.
        """)
        
        with gr.Tabs():
            # Chatbot Interface Tab
            with gr.Tab("💬 AI Assistant"):
                chatbot_ui = gr.Chatbot(
                    height=600,
                    type="messages",
                    show_label=False,
                    avatar_images=(None, "🤖")
                )
                
                msg_input = gr.Textbox(
                    placeholder="Ask me anything about meta-analysis...",
                    label="Your message",
                    lines=2
                )
                
                with gr.Row():
                    submit_btn = gr.Button("Send", variant="primary")
                    clear_btn = gr.Button("Clear")
                
                session_info = gr.Textbox(
                    label="Session Status",
                    value="No active session",
                    interactive=False
                )
                
                # Example prompts
                gr.Examples(
                    examples=[
                        "Start a new meta-analysis for clinical trials",
                        "Upload my CSV data with study results",
                        "Perform the analysis with heterogeneity testing",
                        "Generate a forest plot",
                        "Create an HTML report"
                    ],
                    inputs=msg_input
                )
            
            # Direct Tools Tab (following MCP server pattern)
            with gr.Tab("🛠️ Direct Tools"):
                gr.Markdown("### Direct access to MCP tools (for testing/debugging)")
                
                with gr.Row():
                    with gr.Column():
                        # Initialize tool
                        gr.Markdown("#### Initialize Meta-Analysis")
                        init_name = gr.Textbox(label="Project Name", value="My Meta-Analysis")
                        init_type = gr.Dropdown(
                            ["clinical_trial", "observational", "diagnostic"],
                            label="Study Type",
                            value="clinical_trial"
                        )
                        init_measure = gr.Dropdown(
                            ["OR", "RR", "MD", "SMD", "HR"],
                            label="Effect Measure",
                            value="OR"
                        )
                        init_model = gr.Dropdown(
                            ["fixed", "random", "auto"],
                            label="Analysis Model",
                            value="random"
                        )
                        init_btn = gr.Button("Initialize")
                        init_output = gr.JSON(label="Result")
                    
                    with gr.Column():
                        # Upload data tool
                        gr.Markdown("#### Upload Study Data")
                        upload_file = gr.File(label="Upload CSV", file_types=[".csv"])
                        upload_text = gr.Textbox(
                            label="Or paste CSV data",
                            lines=5,
                            placeholder="study_id,effect_size,se\nStudy1,0.5,0.1"
                        )
                        upload_btn = gr.Button("Upload Data")
                        upload_output = gr.JSON(label="Result")
                
                with gr.Row():
                    with gr.Column():
                        # Analysis tool
                        gr.Markdown("#### Perform Analysis")
                        analysis_hetero = gr.Checkbox(label="Heterogeneity Test", value=True)
                        analysis_bias = gr.Checkbox(label="Publication Bias", value=True)
                        analysis_sens = gr.Checkbox(label="Sensitivity Analysis", value=False)
                        analysis_btn = gr.Button("Run Analysis")
                        analysis_output = gr.JSON(label="Result")
                    
                    with gr.Column():
                        # Forest plot tool
                        gr.Markdown("#### Generate Forest Plot")
                        plot_style = gr.Dropdown(
                            ["classic", "modern", "journal_specific"],
                            label="Style",
                            value="modern"
                        )
                        plot_conf = gr.Slider(0.90, 0.99, value=0.95, label="Confidence Level")
                        plot_btn = gr.Button("Generate Plot")
                        plot_output = gr.JSON(label="Result")
                        plot_image = gr.Image(label="Forest Plot")
            
            # File Upload Tab (following Gradio file-upload-mcp guide)
            with gr.Tab("📁 File Upload"):
                gr.Markdown("""
                ### Upload Study Data
                Following [Gradio's file upload MCP pattern](https://www.gradio.app/guides/file-upload-mcp)
                """)
                
                file_upload = gr.File(
                    label="Upload your data file",
                    file_types=[".csv", ".xlsx", ".txt"],
                    type="filepath"
                )
                
                file_preview = gr.Dataframe(
                    label="Data Preview",
                    interactive=False
                )
                
                validate_btn = gr.Button("Validate & Upload")
                validation_output = gr.Textbox(label="Validation Result")
        
        # Event handlers
        def chat_response(message, history):
            if not message:
                return history, ""
            
            # Add user message
            history.append(ChatMessage(role="user", content=message))
            
            # Get AI response
            response = chatbot.process_message(message, history)
            history.append(ChatMessage(role="assistant", content=response))
            
            # Update session info
            session_text = "No active session"
            if mcp_server.current_session_id:
                session_text = f"Active session: {mcp_server.current_session_id[:8]}..."
            
            return history, "", session_text
        
        # Chatbot events
        msg_input.submit(
            chat_response,
            [msg_input, chatbot_ui],
            [chatbot_ui, msg_input, session_info]
        )
        submit_btn.click(
            chat_response,
            [msg_input, chatbot_ui],
            [chatbot_ui, msg_input, session_info]
        )
        clear_btn.click(
            lambda: ([], "", "No active session"),
            outputs=[chatbot_ui, msg_input, session_info]
        )
        
        # Direct tool events
        init_btn.click(
            lambda n, t, m, am: mcp_server.initialize_meta_analysis(n, t, m, am),
            [init_name, init_type, init_measure, init_model],
            init_output
        )
        
        def handle_file_upload(file_path, text_data):
            if file_path:
                df = pd.read_csv(file_path)
                return mcp_server.upload_study_data(data=df)
            elif text_data:
                return mcp_server.upload_study_data(csv_text=text_data)
            return {"status": "error", "error": "No data provided"}
        
        upload_btn.click(
            handle_file_upload,
            [upload_file, upload_text],
            upload_output
        )
        
        analysis_btn.click(
            lambda h, b, s: mcp_server.perform_meta_analysis(
                heterogeneity_test=h,
                publication_bias=b,
                sensitivity_analysis=s
            ),
            [analysis_hetero, analysis_bias, analysis_sens],
            analysis_output
        )
        
        def generate_and_show_plot(style, conf):
            result = mcp_server.generate_forest_plot(
                plot_style=style,
                confidence_level=conf
            )
            
            # Load image if available
            image = None
            if result.get("plot_path") and Path(result["plot_path"]).exists():
                image = result["plot_path"]
            
            return result, image
        
        plot_btn.click(
            generate_and_show_plot,
            [plot_style, plot_conf],
            [plot_output, plot_image]
        )
        
        # File upload preview
        def preview_file(file_path):
            if file_path:
                if file_path.endswith('.csv'):
                    df = pd.read_csv(file_path)
                    return df.head(10)
            return None
        
        file_upload.change(
            preview_file,
            file_upload,
            file_preview
        )
        
        validate_btn.click(
            lambda f: mcp_server.upload_study_data(data=pd.read_csv(f)) if f else {"error": "No file"},
            file_upload,
            validation_output
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
    app.launch(server_name="0.0.0.0", server_port=7860)