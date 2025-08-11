
"""
Enhanced Meta-Analysis Chatbot - Unified Interface

This script merges the best features of the LangChain-powered agent
and the native Gradio MCP implementation into a single, powerful application.

Features:
- Tab 1: An advanced AI assistant using a LangChain agent for robust tool orchestration.
- Tab 2: A direct tool access interface for developers to test and debug the R backend.
- A unified backend class to ensure consistent R script execution for both tabs.
"""

import os
import json
import subprocess
import base64
from typing import Optional, List, Dict, Any
from pathlib import Path
import tempfile

import gradio as gr
import pandas as pd

# LangChain imports
from langchain.agents import AgentExecutor, create_openai_tools_agent
from langchain.memory import ConversationBufferMemory
from langchain_openai import ChatOpenAI
from langchain_anthropic import ChatAnthropic
from langchain.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain.tools import StructuredTool
from pydantic import BaseModel, Field

# --- Pydantic Models for LangChain Tool Schemas ---

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

class GenerateReportInput(BaseModel):
    session_id: Optional[str] = Field(description="Session ID. If None, uses the active session.", default=None)
    format: str = Field(default="html", description="Format: html, pdf, or word")
    include_code: bool = Field(default=False, description="Include R code in report")

# --- Unified Backend for R Integration ---

class MetaAnalysisBackend:
    """
    Unified backend to handle all R script executions.
    Serves both the LangChain agent and the direct tools UI.
    """
    def __init__(self):
        self.sessions: Dict[str, Dict] = {}
        self.current_session_id: Optional[str] = None
        self.scripts_path = Path(__file__).parent / "scripts"
        self.mcp_tools_path = self.scripts_path / "entry" / "mcp_tools.R"
        
        if not self.mcp_tools_path.exists():
            alt_path = Path("/app/scripts/entry/mcp_tools.R")
            if alt_path.exists():
                self.scripts_path = Path("/app/scripts")
                self.mcp_tools_path = alt_path
            else:
                raise FileNotFoundError(f"R scripts not found at {self.mcp_tools_path}")

    def execute_r_tool(self, tool_name: str, args: Dict[str, Any]) -> Dict[str, Any]:
        """Executes an R tool script, handling arguments and session management."""
        session_id = args.get("session_id") or self.current_session_id
        session_path = self.sessions.get(session_id, {}).get("path") if session_id else None
        if not session_path:
            session_path = tempfile.mkdtemp(prefix="meta_analysis_")

        fd, args_file = tempfile.mkstemp(suffix=".json")
        os.close(fd)
        with open(args_file, "w", encoding="utf-8") as f:
            json.dump(args, f)

        rscript = os.getenv("RSCRIPT_BIN", "Rscript")
        timeout = int(os.getenv("RSCRIPT_TIMEOUT_SEC", "300"))
        debug_r = os.getenv("DEBUG_R") == "1"

        try:
            result = subprocess.run(
                [rscript, "--vanilla", str(self.mcp_tools_path), tool_name, args_file, session_path],
                capture_output=True, text=True, encoding="utf-8", timeout=timeout
            )
        finally:
            if os.path.exists(args_file):
                os.remove(args_file)

        if result.returncode != 0:
            error_info = {"status": "error", "error": "R script failed"}
            if debug_r:
                error_info["stderr"] = (result.stderr or "").strip()
                error_info["stdout"] = (result.stdout or "").strip()
            return error_info

        try:
            return json.loads(result.stdout.strip())
        except json.JSONDecodeError:
            return {"status": "error", "error": "Invalid JSON from R", "raw_output": (result.stdout or "").strip()}

    # --- Tool Methods for LangChain Agent and Direct UI ---

    def initialize_meta_analysis(self, name: str, study_type: str, effect_measure: str, analysis_model: str) -> str:
        """Initialize a new meta-analysis session."""
        result = self.execute_r_tool("initialize_meta_analysis", {
            "name": name, "study_type": study_type, "effect_measure": effect_measure, "analysis_model": analysis_model
        })
        if result.get("status") == "success" and "session_id" in result:
            session_id = result["session_id"]
            self.current_session_id = session_id
            self.sessions[session_id] = {
                "name": name, "path": result.get("session_path"), "config": {
                    "study_type": study_type, "effect_measure": effect_measure, "analysis_model": analysis_model
                }
            }
            return f"✅ Meta-analysis initialized successfully! Session ID: {self.current_session_id}"
        return f"❌ Initialization failed: {json.dumps(result)}"

    def upload_study_data(self, csv_content: str, session_id: Optional[str] = None, validation_level: str = "comprehensive") -> str:
        """Upload study data from a CSV string."""
        active_session_id = session_id or self.current_session_id
        if not active_session_id:
            return "❌ Error: No active session. Please initialize a meta-analysis first."
        
        encoded_data = base64.b64encode(csv_content.encode()).decode()
        result = self.execute_r_tool("upload_study_data", {
            "session_id": active_session_id, "data_content": encoded_data,
            "data_format": "csv", "validation_level": validation_level
        })
        return f"✅ Data upload result: {json.dumps(result)}"

    def perform_meta_analysis(self, session_id: Optional[str] = None, **kwargs) -> str:
        """Perform the meta-analysis."""
        active_session_id = session_id or self.current_session_id
        if not active_session_id:
            return "❌ Error: No active session."
        
        args = {"session_id": active_session_id, **kwargs}
        result = self.execute_r_tool("perform_meta_analysis", args)
        return f"📊 Analysis completed! {json.dumps(result)}"

    def generate_forest_plot(self, session_id: Optional[str] = None, **kwargs) -> str:
        """Generate a forest plot."""
        active_session_id = session_id or self.current_session_id
        if not active_session_id:
            return "❌ Error: No active session."
            
        args = {"session_id": active_session_id, **kwargs}
        result = self.execute_r_tool("generate_forest_plot", args)
        
        if result.get("status") == "success":
            plot_path_str = result.get("forest_plot_path") or result.get("plot_file")
            if plot_path_str:
                session_path = self.sessions[active_session_id]["path"]
                plot_path = Path(session_path) / "results" / plot_path_str
                if plot_path.exists():
                    # Return a user-friendly message with the path for Gradio to find the image
                    return f"📈 Forest plot generated successfully! You can view it in the 'Direct Tools' tab. Path: {plot_path}"
        return f"❌ Plot generation failed: {json.dumps(result)}"

    def generate_report(self, session_id: Optional[str] = None, **kwargs) -> str:
        """Generate a comprehensive report."""
        active_session_id = session_id or self.current_session_id
        if not active_session_id:
            return "❌ Error: No active session."
        
        args = {"session_id": active_session_id, **kwargs}
        result = self.execute_r_tool("generate_report", args)
        return f"📄 Report generated! {json.dumps(result)}"

    def get_current_session_id(self) -> str:
        """Get the current session ID."""
        if self.current_session_id:
            return f"Current session ID is {self.current_session_id}"
        return "No active session. Please use 'initialize_meta_analysis' to start."

# --- LangChain Agent Setup ---

def create_langchain_agent(backend: MetaAnalysisBackend):
    """Creates a LangChain agent with tools wired to the unified backend."""
    tools = [
        StructuredTool.from_function(
            func=backend.initialize_meta_analysis, name="initialize_meta_analysis",
            description="Starts a new meta-analysis session. Always use this first.",
            args_schema=InitializeMetaAnalysisInput
        ),
        StructuredTool.from_function(
            func=backend.upload_study_data, name="upload_study_data",
            description="Uploads CSV data for the analysis. Requires an active session.",
            args_schema=UploadStudyDataInput
        ),
        StructuredTool.from_function(
            func=backend.perform_meta_analysis, name="perform_meta_analysis",
            description="Executes the statistical meta-analysis on uploaded data.",
            args_schema=PerformMetaAnalysisInput
        ),
        StructuredTool.from_function(
            func=backend.generate_forest_plot, name="generate_forest_plot",
            description="Creates a forest plot visualization of the results.",
            args_schema=GenerateForestPlotInput
        ),
        StructuredTool.from_function(
            func=backend.generate_report, name="generate_report",
            description="Generates a comprehensive report of the analysis.",
            args_schema=GenerateReportInput
        ),
        StructuredTool.from_function(
            func=backend.get_current_session_id, name="get_current_session_id",
            description="Gets the ID of the current active session."
        )
    ]

    prompt = ChatPromptTemplate.from_messages([
        ("system", "You are an expert meta-analysis assistant. Guide users through the analysis workflow using your available tools. Explain statistical concepts and interpret results clearly."),
        MessagesPlaceholder(variable_name="chat_history"),
        ("human", "{input}"),
        MessagesPlaceholder(variable_name="agent_scratchpad")
    ])

    try:
        llm = ChatOpenAI(model="gpt-4-turbo-preview", temperature=0.7, api_key=os.getenv("OPENAI_API_KEY"))
    except Exception:
        llm = ChatAnthropic(model="claude-3-opus-20240229", temperature=0.7, api_key=os.getenv("ANTHROPIC_API_KEY"))

    agent = create_openai_tools_agent(llm, tools, prompt)
    memory = ConversationBufferMemory(memory_key="chat_history", return_messages=True)
    agent_executor = AgentExecutor(
        agent=agent, tools=tools, memory=memory, verbose=True, handle_parsing_errors=True, max_iterations=5
    )
    return agent_executor

# --- Gradio UI Construction ---

def create_gradio_app():
    """Creates the unified Gradio application with multiple tabs."""
    backend = MetaAnalysisBackend()
    agent_executor = create_langchain_agent(backend)

    with gr.Blocks(title="Enhanced Meta-Analysis Assistant", theme=gr.themes.Soft()) as app:
        gr.Markdown("# 🧬 Enhanced Meta-Analysis AI Assistant")
        
        with gr.Tabs():
            # --- AI Assistant Tab (for End-Users) ---
            with gr.Tab("💬 AI Assistant"):
                gr.Markdown("### Chat with an AI to conduct your meta-analysis.")
                with gr.Row():
                    with gr.Column(scale=3):
                        chatbot_ui = gr.Chatbot(
                            height=650, show_label=False, bubble_full_width=False,
                            avatar_images=(None, "🤖")
                        )
                        msg_input = gr.Textbox(
                            label="Your message",
                            placeholder="e.g., 'Start a new meta-analysis for my clinical trial data'",
                            lines=3
                        )
                        with gr.Row():
                            submit_btn = gr.Button("Send", variant="primary")
                            clear_btn = gr.Button("Clear Chat")
                    
                    with gr.Column(scale=1):
                        session_display = gr.Textbox(label="📌 Current Session", value="No active session", interactive=False)
                        gr.Markdown("#### 💡 Quick Actions")
                        quick_actions = [
                            ("🚀 Start Analysis", "Start a new meta-analysis for clinical trial data"),
                            ("🔬 Run Analysis", "Perform the meta-analysis with heterogeneity tests"),
                            ("📈 Forest Plot", "Generate a modern forest plot"),
                            ("📄 Generate Report", "Create an HTML report")
                        ]
                        for label, prompt in quick_actions:
                            gr.Button(label, size="sm").click(lambda p=prompt: p, outputs=[msg_input])
                        
                        with gr.Accordion("📋 Sample Data", open=False):
                            sample_csv = gr.Code(
                                value="study_id,effect_size,se\nSmith2020,0.45,0.12\nJohnson2021,0.38,0.15",
                                language="csv", interactive=False
                            )
                            upload_sample = gr.Button("Use this sample data")
                            upload_sample.click(
                                lambda: "Please upload this CSV data for analysis:\n```csv\nstudy_id,effect_size,se\nSmith2020,0.45,0.12\nJohnson2021,0.38,0.15\n```",
                                outputs=[msg_input]
                            )

            # --- Direct Tools Tab (for Developers) ---
            with gr.Tab("🛠️ Direct Tools"):
                gr.Markdown("### Direct access to backend tools for testing and debugging.")
                with gr.Row():
                    with gr.Column():
                        gr.Markdown("#### Initialize Meta-Analysis")
                        init_name = gr.Textbox(label="Project Name", value="My Test Analysis")
                        init_type = gr.Dropdown(["clinical_trial", "observational"], label="Study Type", value="clinical_trial")
                        init_measure = gr.Dropdown(["OR", "RR", "MD"], label="Effect Measure", value="OR")
                        init_model = gr.Dropdown(["fixed", "random"], label="Analysis Model", value="random")
                        init_btn = gr.Button("Initialize")
                        init_output = gr.JSON(label="Result")
                    
                    with gr.Column():
                        gr.Markdown("#### Upload Study Data")
                        upload_text = gr.Textbox(label="Paste CSV data", lines=5, placeholder="study_id,effect_size,se\n...")
                        upload_btn = gr.Button("Upload Data")
                        upload_output = gr.JSON(label="Result")

                with gr.Row():
                    with gr.Column():
                        gr.Markdown("#### Perform Analysis")
                        analysis_btn = gr.Button("Run Analysis")
                        analysis_output = gr.JSON(label="Result")
                    
                    with gr.Column():
                        gr.Markdown("#### Generate Forest Plot")
                        plot_btn = gr.Button("Generate Plot")
                        plot_output = gr.JSON(label="Result")
                        plot_image = gr.Image(label="Forest Plot")

        # --- Event Handlers ---
        
        # AI Assistant Tab Handlers
        def respond(message, history):
            if not message:
                return "", history, "No active session"
            response = agent_executor.invoke({"input": message})
            history.append((message, response["output"]))
            session_text = f"Session: {backend.current_session_id[:8]}..." if backend.current_session_id else "No active session"
            return "", history, session_text

        submit_btn.click(respond, [msg_input, chatbot_ui], [msg_input, chatbot_ui, session_display])
        msg_input.submit(respond, [msg_input, chatbot_ui], [msg_input, chatbot_ui, session_display])
        clear_btn.click(lambda: ("", [], "No active session"), outputs=[msg_input, chatbot_ui, session_display]).then(
            lambda: agent_executor.memory.clear()
        )

        # Direct Tools Tab Handlers
        def direct_initialize(name, study_type, effect_measure, analysis_model):
            # This call also sets the backend's current_session_id
            result = backend.execute_r_tool("initialize_meta_analysis", {
                "name": name, "study_type": study_type, 
                "effect_measure": effect_measure, "analysis_model": analysis_model
            })
            if result.get("status") == "success" and "session_id" in result:
                backend.current_session_id = result["session_id"]
                backend.sessions[result["session_id"]] = {"path": result.get("session_path")}
            return result

        def direct_upload(csv_content):
            if not backend.current_session_id:
                return {"status": "error", "error": "Please initialize a session first."}
            if not csv_content:
                return {"status": "error", "error": "CSV content cannot be empty."}
            encoded_data = base64.b64encode(csv_content.encode()).decode()
            return backend.execute_r_tool("upload_study_data", {
                "session_id": backend.current_session_id,
                "data_content": encoded_data,
                "data_format": "csv",
                "validation_level": "comprehensive"
            })

        def direct_analyze():
            if not backend.current_session_id:
                return {"status": "error", "error": "Please initialize a session first."}
            return backend.execute_r_tool("perform_meta_analysis", {"session_id": backend.current_session_id})

        init_btn.click(direct_initialize, [init_name, init_type, init_measure, init_model], init_output)
        upload_btn.click(direct_upload, [upload_text], upload_output)
        analysis_btn.click(direct_analyze, [], analysis_output)
        
        def generate_and_show_plot():
            if not backend.current_session_id:
                return {"status": "error", "error": "Please initialize a session first."}, None
            
            result = backend.execute_r_tool("generate_forest_plot", {"session_id": backend.current_session_id})
            image = None
            if result.get("status") == "success":
                plot_path_str = result.get("forest_plot_path") or result.get("plot_file")
                if plot_path_str:
                    session_path = backend.sessions[backend.current_session_id]["path"]
                    plot_path = Path(session_path) / "results" / plot_path_str
                    if plot_path.exists():
                        image = str(plot_path)
            return result, image

        plot_btn.click(generate_and_show_plot, [], [plot_output, plot_image])

    return app

if __name__ == "__main__":
    if not os.getenv("OPENAI_API_KEY") and not os.getenv("ANTHROPIC_API_KEY"):
        print("⚠️ WARNING: No LLM API key found. Please set OPENAI_API_KEY or ANTHROPIC_API_KEY.")
    
    print("🚀 Launching Enhanced Meta-Analysis AI Assistant...")
    app = create_gradio_app()
    app.launch(server_name="0.0.0.0", server_port=7860)
