"""
Advanced Meta-Analysis Chatbot using LangChain for better tool orchestration
This version uses LangChain's agent framework for more reliable tool calling
"""

import os
import json
import subprocess
import base64
from typing import Optional, List, Dict, Any, Tuple
from datetime import datetime

import gradio as gr
from mcp import ClientSession, StdioTransport

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


# Pydantic models for tool parameters
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


class MCPToolWrapper:
    """Wrapper for MCP tools to work with LangChain"""
    
    def __init__(self):
        self.current_session_id = None
        self.server_proc = None
    
    def start_server(self):
        """Start MCP server if not running"""
        global server_proc
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
        if server_proc and server_proc.poll() is None:
            server_proc.terminate()
            try:
                server_proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                server_proc.kill()
        server_proc = None
        self.server_proc = None
    
    def call_tool(self, tool_name: str, args: dict) -> str:
        """Generic tool caller for MCP"""
        self.start_server()
        try:
            transport = StdioTransport(self.server_proc.stdin, self.server_proc.stdout)
            with ClientSession(transport) as session:
                result = session.call_tool(tool_name, args)
                return json.dumps(result, indent=2)
        except Exception as e:
            return f"Error calling {tool_name}: {str(e)}"
        finally:
            self.stop_server()
    
    def initialize_meta_analysis(self, name: str, study_type: str, effect_measure: str, analysis_model: str) -> str:
        """Initialize a new meta-analysis session"""
        result_json = self.call_tool("initialize_meta_analysis", {
            "name": name,
            "study_type": study_type,
            "effect_measure": effect_measure,
            "analysis_model": analysis_model
        })
        
        # Try to extract session_id
        try:
            result = json.loads(result_json)
            if "content" in result and len(result["content"]) > 0:
                content = json.loads(result["content"][0].get("text", "{}"))
                if "session_id" in content:
                    self.current_session_id = content["session_id"]
                    return f"✅ Meta-analysis initialized successfully!\nSession ID: {self.current_session_id}\nName: {name}\nType: {study_type}\nEffect Measure: {effect_measure}\nModel: {analysis_model}"
        except:
            pass
        
        return f"Initialization result: {result_json}"
    
    def upload_study_data(self, session_id: str, csv_content: str, data_format: str = "csv", validation_level: str = "comprehensive") -> str:
        """Upload study data"""
        # Use current session if not provided
        if not session_id and self.current_session_id:
            session_id = self.current_session_id
        
        # Encode CSV content
        encoded_data = base64.b64encode(csv_content.encode()).decode()
        
        result = self.call_tool("upload_study_data", {
            "session_id": session_id,
            "data_content": encoded_data,
            "data_format": data_format,
            "validation_level": validation_level
        })
        
        return f"✅ Data uploaded successfully!\n{result}"
    
    def perform_meta_analysis(self, session_id: str, heterogeneity_test: bool = True, 
                             publication_bias: bool = True, sensitivity_analysis: bool = False) -> str:
        """Perform the meta-analysis"""
        if not session_id and self.current_session_id:
            session_id = self.current_session_id
        
        result = self.call_tool("perform_meta_analysis", {
            "session_id": session_id,
            "heterogeneity_test": heterogeneity_test,
            "publication_bias": publication_bias,
            "sensitivity_analysis": sensitivity_analysis
        })
        
        return f"📊 Analysis completed!\n{result}"
    
    def generate_forest_plot(self, session_id: str, plot_style: str = "modern", confidence_level: float = 0.95) -> str:
        """Generate forest plot"""
        if not session_id and self.current_session_id:
            session_id = self.current_session_id
        
        result = self.call_tool("generate_forest_plot", {
            "session_id": session_id,
            "plot_style": plot_style,
            "confidence_level": confidence_level
        })
        
        return f"📈 Forest plot generated!\n{result}"
    
    def assess_publication_bias(self, session_id: str, methods: List[str] = None) -> str:
        """Assess publication bias"""
        if not session_id and self.current_session_id:
            session_id = self.current_session_id
        
        if methods is None:
            methods = ["funnel_plot", "egger_test", "begg_test"]
        
        result = self.call_tool("assess_publication_bias", {
            "session_id": session_id,
            "methods": methods
        })
        
        return f"🔍 Publication bias assessment completed!\n{result}"
    
    def generate_report(self, session_id: str, format: str = "html", include_code: bool = False) -> str:
        """Generate comprehensive report"""
        if not session_id and self.current_session_id:
            session_id = self.current_session_id
        
        result = self.call_tool("generate_report", {
            "session_id": session_id,
            "format": format,
            "include_code": include_code
        })
        
        return f"📄 Report generated!\n{result}"
    
    def get_current_session(self) -> str:
        """Get current session ID"""
        if self.current_session_id:
            return f"Current session: {self.current_session_id}"
        return "No active session. Please initialize a meta-analysis first."


def create_langchain_agent():
    """Create a LangChain agent with MCP tools"""
    
    # Initialize the MCP wrapper
    mcp_wrapper = MCPToolWrapper()
    
    # Create structured tools for LangChain
    tools = [
        StructuredTool.from_function(
            func=mcp_wrapper.initialize_meta_analysis,
            name="initialize_meta_analysis",
            description="Start a new meta-analysis session. Use this first before any other analysis.",
            args_schema=InitializeMetaAnalysisInput
        ),
        StructuredTool.from_function(
            func=mcp_wrapper.upload_study_data,
            name="upload_study_data",
            description="Upload CSV data for the meta-analysis. Requires a session_id from initialization.",
            args_schema=UploadStudyDataInput
        ),
        StructuredTool.from_function(
            func=mcp_wrapper.perform_meta_analysis,
            name="perform_meta_analysis",
            description="Execute the statistical meta-analysis on uploaded data.",
            args_schema=PerformMetaAnalysisInput
        ),
        StructuredTool.from_function(
            func=mcp_wrapper.generate_forest_plot,
            name="generate_forest_plot",
            description="Create a forest plot visualization of the meta-analysis results.",
            args_schema=GenerateForestPlotInput
        ),
        StructuredTool.from_function(
            func=mcp_wrapper.assess_publication_bias,
            name="assess_publication_bias",
            description="Check for publication bias using various statistical tests.",
            args_schema=AssessPublicationBiasInput
        ),
        StructuredTool.from_function(
            func=mcp_wrapper.generate_report,
            name="generate_report",
            description="Generate a comprehensive report of the meta-analysis.",
            args_schema=GenerateReportInput
        ),
        Tool(
            func=mcp_wrapper.get_current_session,
            name="get_current_session",
            description="Get the current session ID if one is active."
        )
    ]
    
    # Create prompt template
    prompt = ChatPromptTemplate.from_messages([
        ("system", """You are an expert meta-analysis assistant. You help researchers conduct comprehensive meta-analyses using statistical tools.

Key responsibilities:
1. Guide users through the meta-analysis workflow step by step
2. Explain statistical concepts in accessible language
3. Interpret results and provide actionable insights
4. Suggest appropriate statistical methods based on the data
5. Ensure proper methodology and reporting standards

Always maintain the session_id after initialization for all subsequent operations.
When users provide CSV data, help them upload it properly.
Explain what you're doing and why at each step.
"""),
        MessagesPlaceholder(variable_name="chat_history"),
        ("human", "{input}"),
        MessagesPlaceholder(variable_name="agent_scratchpad")
    ])
    
    # Initialize LLM (try OpenAI first, then Anthropic)
    try:
        llm = ChatOpenAI(
            model="gpt-4-turbo-preview",
            temperature=0.7,
            api_key=os.getenv("OPENAI_API_KEY")
        )
    except:
        try:
            llm = ChatAnthropic(
                model="claude-3-opus-20240229",
                temperature=0.7,
                api_key=os.getenv("ANTHROPIC_API_KEY")
            )
        except:
            raise ValueError("No LLM API key found. Please set OPENAI_API_KEY or ANTHROPIC_API_KEY")
    
    # Create the agent
    agent = create_openai_tools_agent(llm, tools, prompt)
    
    # Create memory
    memory = ConversationBufferMemory(
        memory_key="chat_history",
        return_messages=True
    )
    
    # Create agent executor
    agent_executor = AgentExecutor(
        agent=agent,
        tools=tools,
        memory=memory,
        verbose=True,
        handle_parsing_errors=True,
        max_iterations=5
    )
    
    return agent_executor, mcp_wrapper


def create_gradio_interface():
    """Create the Gradio interface with LangChain agent"""
    
    # Initialize the agent
    agent_executor, mcp_wrapper = create_langchain_agent()
    
    with gr.Blocks(title="🧬 Meta-Analysis AI Assistant", theme=gr.themes.Soft()) as demo:
        gr.Markdown("""
        # 🧬 Meta-Analysis AI Assistant (LangChain Enhanced)
        
        This AI assistant helps you conduct comprehensive meta-analyses through natural conversation.
        It uses advanced tool orchestration to handle complex multi-step analyses automatically.
        
        ### What I can do:
        - 📊 Initialize and manage analysis sessions
        - 📁 Upload and validate your study data
        - 🔬 Perform statistical meta-analyses
        - 📈 Generate forest plots and visualizations
        - 🔍 Assess publication bias
        - 📄 Create comprehensive reports
        - 💡 Explain statistical concepts and interpret results
        """)
        
        with gr.Row():
            with gr.Column(scale=3):
                chatbot = gr.Chatbot(
                    height=650,
                    show_label=False,
                    bubble_full_width=False,
                    avatar_images=(None, "🤖")
                )
                
                msg = gr.Textbox(
                    label="Ask me anything about meta-analysis",
                    placeholder="Example: 'Start a new meta-analysis for my clinical trial data using odds ratios'",
                    lines=3
                )
                
                with gr.Row():
                    submit = gr.Button("Send", variant="primary")
                    clear = gr.Button("Clear Chat")
                    
            with gr.Column(scale=1):
                session_display = gr.Textbox(
                    label="📌 Current Session",
                    value="No active session",
                    interactive=False,
                    lines=2
                )
                
                gr.Markdown("### 💡 Quick Actions")
                
                quick_actions = [
                    ("🚀 Start Analysis", "Start a new meta-analysis for clinical trial data using odds ratios with a random effects model"),
                    ("📁 Upload Data", "I have CSV data to upload for analysis"),
                    ("🔬 Run Analysis", "Perform the meta-analysis with heterogeneity and publication bias tests"),
                    ("📈 Forest Plot", "Generate a modern forest plot with 95% confidence intervals"),
                    ("📄 Generate Report", "Create a comprehensive HTML report of the analysis")
                ]
                
                for label, prompt in quick_actions:
                    gr.Button(label, size="sm").click(
                        lambda p=prompt: p,
                        outputs=[msg]
                    )
                
                gr.Markdown("### 📋 Sample Data")
                with gr.Accordion("View sample CSV format", open=False):
                    sample_csv = gr.Code(
                        value="""study_id,effect_size,se,year,n_treatment,n_control
Smith2020,0.45,0.12,2020,150,148
Johnson2021,0.38,0.15,2021,200,195
Williams2019,0.52,0.10,2019,175,180
Brown2022,0.41,0.14,2022,225,220
Davis2021,0.48,0.11,2021,160,165""",
                        language="csv",
                        interactive=False
                    )
                    upload_sample = gr.Button("Use this sample data")
                    
                    upload_sample.click(
                        lambda: "Please upload this CSV data for analysis:\n```csv\nstudy_id,effect_size,se,year,n_treatment,n_control\nSmith2020,0.45,0.12,2020,150,148\nJohnson2021,0.38,0.15,2021,200,195\nWilliams2019,0.52,0.10,2019,175,180\nBrown2022,0.41,0.14,2022,225,220\nDavis2021,0.48,0.11,2021,160,165\n```",
                        outputs=[msg]
                    )
        
        def respond(message, history):
            """Process user message through LangChain agent"""
            if not message:
                return "", history
            
            # Add user message to chat history
            history.append((message, None))
            
            try:
                # Run the agent
                response = agent_executor.invoke({"input": message})
                assistant_message = response["output"]
                
                # Update history
                history[-1] = (message, assistant_message)
                
                # Update session display
                session_text = f"Session: {mcp_wrapper.current_session_id[:8]}..." if mcp_wrapper.current_session_id else "No active session"
                
                return "", history, session_text
                
            except Exception as e:
                error_msg = f"❌ Error: {str(e)}"
                history[-1] = (message, error_msg)
                return "", history, session_display.value
        
        # Event handlers
        msg.submit(respond, [msg, chatbot, session_display], [msg, chatbot, session_display])
        submit.click(respond, [msg, chatbot, session_display], [msg, chatbot, session_display])
        
        clear.click(
            lambda: ("", [], "No active session"),
            outputs=[msg, chatbot, session_display]
        ).then(
            lambda: agent_executor.memory.clear()
        )
        
        # Load example on startup
        demo.load(
            lambda: [
                [],
                "No active session",
                "Try: 'Start a new meta-analysis for clinical trials'"
            ],
            outputs=[chatbot, session_display, msg]
        )
    
    return demo


if __name__ == "__main__":
    import sys
    
    # Check for required packages
    try:
        import langchain
        import openai
    except ImportError:
        print("❌ Required packages not installed!")
        print("Please run: pip install -r requirements-chatbot.txt")
        sys.exit(1)
    
    # Check for API keys
    if not os.getenv("OPENAI_API_KEY") and not os.getenv("ANTHROPIC_API_KEY"):
        print("⚠️ No API key found!")
        print("Please set either OPENAI_API_KEY or ANTHROPIC_API_KEY environment variable")
        sys.exit(1)
    
    # Launch the interface
    print("🚀 Launching Meta-Analysis AI Assistant...")
    demo = create_gradio_interface()
    demo.launch(server_name="0.0.0.0", server_port=7860, share=False)