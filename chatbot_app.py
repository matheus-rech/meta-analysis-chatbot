"""
Meta-Analysis AI Assistant - True Chatbot Implementation
A conversational interface for conducting meta-analyses using natural language
"""

import os
import json
import subprocess
import threading
from typing import Optional, List, Dict, Any, Tuple
import re
from datetime import datetime

import gradio as gr
from mcp import ClientSession, StdioTransport
import base64
import traceback

# LLM imports - supporting both OpenAI and Anthropic
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

# Initialize MCP server components
SERVER_SCRIPT_PATH = os.path.join(os.path.dirname(__file__), "server.py")
SERVER_CMD = ["python", SERVER_SCRIPT_PATH]

server_proc: Optional[subprocess.Popen] = None
server_lock = threading.Lock()

# System prompt for the AI assistant
SYSTEM_PROMPT = """You are an expert meta-analysis assistant with deep knowledge of statistical methods and R programming. 
You help researchers conduct comprehensive meta-analyses through natural conversation.

You have access to the following MCP tools for meta-analysis:
1. initialize_meta_analysis - Start a new analysis session
2. upload_study_data - Upload CSV/Excel data for analysis
3. perform_meta_analysis - Run the statistical analysis
4. generate_forest_plot - Create forest plots
5. assess_publication_bias - Check for publication bias
6. generate_report - Create comprehensive reports
7. get_session_status - Check analysis progress

When users ask you to perform analyses, you should:
- Ask clarifying questions if needed
- Explain what you're doing at each step
- Interpret results in plain language
- Suggest next steps based on findings
- Provide educational context about statistical concepts

Always maintain the session_id after initialization for subsequent operations.
Format your responses with clear sections and use markdown for better readability.
"""

# Tool descriptions for the LLM
TOOL_DESCRIPTIONS = {
    "initialize_meta_analysis": {
        "description": "Start a new meta-analysis session",
        "parameters": {
            "name": "Project name",
            "study_type": "Type of study (clinical_trial, observational, diagnostic)",
            "effect_measure": "Effect measure (OR, RR, MD, SMD, HR, PROP, MEAN)",
            "analysis_model": "Analysis model (fixed, random, auto)"
        }
    },
    "upload_study_data": {
        "description": "Upload study data for analysis",
        "parameters": {
            "session_id": "Session ID from initialization",
            "data_content": "Base64 encoded CSV/Excel content",
            "data_format": "Format (csv, excel, revman)",
            "validation_level": "Validation level (basic, comprehensive)"
        }
    },
    "perform_meta_analysis": {
        "description": "Execute the meta-analysis",
        "parameters": {
            "session_id": "Session ID",
            "heterogeneity_test": "Test for heterogeneity (boolean)",
            "publication_bias": "Test for publication bias (boolean)",
            "sensitivity_analysis": "Perform sensitivity analysis (boolean)"
        }
    },
    "generate_forest_plot": {
        "description": "Generate a forest plot visualization",
        "parameters": {
            "session_id": "Session ID",
            "plot_style": "Style (classic, modern, journal_specific)",
            "confidence_level": "Confidence level (0.90, 0.95, 0.99)"
        }
    },
    "assess_publication_bias": {
        "description": "Assess publication bias",
        "parameters": {
            "session_id": "Session ID",
            "methods": "List of methods (funnel_plot, egger_test, begg_test, trim_fill)"
        }
    },
    "generate_report": {
        "description": "Generate comprehensive report",
        "parameters": {
            "session_id": "Session ID",
            "format": "Output format (html, pdf, word)",
            "include_code": "Include R code (boolean)"
        }
    }
}

class MetaAnalysisAssistant:
    """AI Assistant for Meta-Analysis with MCP tool integration"""
    
    def __init__(self, llm_provider="openai"):
        self.llm_provider = llm_provider
        self.current_session_id = None
        self.conversation_history = []
        
        # Initialize LLM client
        if llm_provider == "openai" and OPENAI_AVAILABLE:
            self.client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
            self.model = "gpt-4-turbo-preview"
        elif llm_provider == "anthropic" and ANTHROPIC_AVAILABLE:
            self.client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
            self.model = "claude-3-opus-20240229"
        else:
            raise ValueError(f"LLM provider {llm_provider} not available. Please install required packages.")
    
    def start_mcp_server(self) -> None:
        """Start the MCP server process"""
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
                bufsize=1,
            )
    
    def stop_mcp_server(self) -> None:
        """Stop the MCP server process"""
        global server_proc
        with server_lock:
            if server_proc and server_proc.poll() is None:
                server_proc.terminate()
                try:
                    server_proc.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    server_proc.kill()
            server_proc = None
    
    def call_mcp_tool(self, tool: str, args: dict) -> dict:
        """Call an MCP tool through the server"""
        self.start_mcp_server()
        assert server_proc is not None
        try:
            transport = StdioTransport(server_proc.stdin, server_proc.stdout)
            with ClientSession(transport) as session:
                tools = session.list_tools()
                if all(t.name != tool for t in tools):
                    return {"error": f"Tool {tool} not available"}
                result = session.call_tool(tool, args)
            return result
        except Exception as e:
            return {"error": str(e)}
        finally:
            self.stop_mcp_server()
    
    def extract_tool_calls(self, message: str) -> List[Dict[str, Any]]:
        """Extract tool calls from LLM response"""
        tool_calls = []
        
        # Look for tool call patterns in the message
        for tool_name in TOOL_DESCRIPTIONS.keys():
            if tool_name in message:
                # Extract parameters based on context
                # This is a simplified version - in production, use proper function calling
                tool_call = {"tool": tool_name, "args": {}}
                
                # Extract session_id if mentioned
                session_match = re.search(r'session[_\s]?id[:\s]+([a-f0-9-]+)', message, re.IGNORECASE)
                if session_match:
                    tool_call["args"]["session_id"] = session_match.group(1)
                elif self.current_session_id and "session_id" in TOOL_DESCRIPTIONS[tool_name]["parameters"]:
                    tool_call["args"]["session_id"] = self.current_session_id
                
                tool_calls.append(tool_call)
        
        return tool_calls
    
    def process_message(self, message: str, history: List[Tuple[str, str]]) -> Tuple[str, List[Tuple[str, str]]]:
        """Process user message and generate response"""
        
        # Add user message to history
        history.append((message, None))
        
        # Prepare conversation context
        messages = [{"role": "system", "content": SYSTEM_PROMPT}]
        
        # Add conversation history
        for user_msg, assistant_msg in history[:-1]:
            if user_msg:
                messages.append({"role": "user", "content": user_msg})
            if assistant_msg:
                messages.append({"role": "assistant", "content": assistant_msg})
        
        # Add current message
        messages.append({"role": "user", "content": message})
        
        # Get LLM response
        response_text = self.get_llm_response(messages)
        
        # Check if we need to call any tools
        tool_results = []
        if any(tool in response_text.lower() for tool in ["initialize", "upload", "perform", "generate", "assess"]):
            # Parse the response for tool calls
            tool_calls = self.extract_tool_calls_from_response(response_text, message)
            
            for tool_call in tool_calls:
                result = self.call_mcp_tool(tool_call["tool"], tool_call["args"])
                tool_results.append({
                    "tool": tool_call["tool"],
                    "result": result
                })
                
                # Update session_id if initialization was successful
                if tool_call["tool"] == "initialize_meta_analysis" and "session_id" in str(result):
                    try:
                        result_data = json.loads(result.get("content", [{}])[0].get("text", "{}"))
                        self.current_session_id = result_data.get("session_id")
                        response_text += f"\n\n✅ **Session initialized:** `{self.current_session_id}`"
                    except:
                        pass
        
        # Format tool results into the response
        if tool_results:
            response_text += "\n\n### 🔧 Tool Execution Results:\n"
            for tr in tool_results:
                response_text += f"\n**{tr['tool']}:**\n```json\n{json.dumps(tr['result'], indent=2)}\n```\n"
        
        # Update history with assistant response
        history[-1] = (message, response_text)
        
        return "", history
    
    def get_llm_response(self, messages: List[Dict[str, str]]) -> str:
        """Get response from LLM"""
        try:
            if self.llm_provider == "openai":
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    temperature=0.7,
                    max_tokens=2000
                )
                return response.choices[0].message.content
            
            elif self.llm_provider == "anthropic":
                # Convert messages format for Anthropic
                system_msg = messages[0]["content"] if messages[0]["role"] == "system" else ""
                claude_messages = [m for m in messages[1:] if m["role"] != "system"]
                
                response = self.client.messages.create(
                    model=self.model,
                    system=system_msg,
                    messages=claude_messages,
                    max_tokens=2000,
                    temperature=0.7
                )
                return response.content[0].text
            
        except Exception as e:
            return f"❌ Error getting LLM response: {str(e)}"
    
    def extract_tool_calls_from_response(self, response: str, user_message: str) -> List[Dict[str, Any]]:
        """Extract and prepare tool calls based on LLM response and user intent"""
        tool_calls = []
        
        # Detect initialization intent
        if any(word in user_message.lower() for word in ["start", "begin", "initialize", "new"]) and not self.current_session_id:
            tool_calls.append({
                "tool": "initialize_meta_analysis",
                "args": {
                    "name": "Meta-Analysis Project",
                    "study_type": "clinical_trial",
                    "effect_measure": "OR",
                    "analysis_model": "random"
                }
            })
        
        # Detect data upload intent
        if any(word in user_message.lower() for word in ["upload", "load", "import", "csv", "data"]):
            # Check if user provided CSV data
            csv_match = re.search(r'```(?:csv)?\n(.*?)\n```', user_message, re.DOTALL)
            if csv_match:
                csv_data = csv_match.group(1)
                encoded_data = base64.b64encode(csv_data.encode()).decode()
                
                tool_calls.append({
                    "tool": "upload_study_data",
                    "args": {
                        "session_id": self.current_session_id,
                        "data_content": encoded_data,
                        "data_format": "csv",
                        "validation_level": "comprehensive"
                    }
                })
        
        # Detect analysis intent
        if any(word in user_message.lower() for word in ["analyze", "run", "perform", "calculate"]):
            tool_calls.append({
                "tool": "perform_meta_analysis",
                "args": {
                    "session_id": self.current_session_id,
                    "heterogeneity_test": True,
                    "publication_bias": True,
                    "sensitivity_analysis": False
                }
            })
        
        # Detect visualization intent
        if any(word in user_message.lower() for word in ["forest", "plot", "visualize", "graph"]):
            tool_calls.append({
                "tool": "generate_forest_plot",
                "args": {
                    "session_id": self.current_session_id,
                    "plot_style": "modern",
                    "confidence_level": 0.95
                }
            })
        
        # Detect report generation intent
        if any(word in user_message.lower() for word in ["report", "summary", "document"]):
            tool_calls.append({
                "tool": "generate_report",
                "args": {
                    "session_id": self.current_session_id,
                    "format": "html",
                    "include_code": False
                }
            })
        
        return tool_calls


def create_chatbot_interface():
    """Create the Gradio chatbot interface"""
    
    # Initialize the assistant
    assistant = MetaAnalysisAssistant(
        llm_provider="openai" if OPENAI_AVAILABLE else "anthropic"
    )
    
    with gr.Blocks(title="Meta-Analysis AI Assistant", theme=gr.themes.Soft()) as demo:
        gr.Markdown("""
        # 🧬 Meta-Analysis AI Assistant
        
        Welcome! I'm your AI assistant for conducting meta-analyses. I can help you:
        - Initialize and manage analysis sessions
        - Upload and validate study data
        - Perform statistical analyses
        - Generate visualizations and reports
        - Interpret results and suggest next steps
        
        Just describe what you want to do in natural language!
        """)
        
        with gr.Row():
            with gr.Column(scale=2):
                chatbot = gr.Chatbot(
                    height=600,
                    show_label=False,
                    elem_id="chatbot",
                    bubble_full_width=False,
                    avatar_images=(None, "🤖")
                )
                
                with gr.Row():
                    msg = gr.Textbox(
                        label="Your message",
                        placeholder="Try: 'Start a new meta-analysis for clinical trials using odds ratios'",
                        lines=2,
                        scale=4
                    )
                    submit = gr.Button("Send", variant="primary", scale=1)
                
                with gr.Row():
                    clear = gr.Button("Clear Chat")
                    session_info = gr.Textbox(
                        label="Current Session ID",
                        value="No active session",
                        interactive=False
                    )
            
            with gr.Column(scale=1):
                gr.Markdown("### 💡 Example Prompts")
                
                example_prompts = [
                    "Start a new meta-analysis for clinical trials",
                    "Upload my CSV data and validate it",
                    "Perform a random effects meta-analysis",
                    "Generate a forest plot with 95% confidence intervals",
                    "Check for publication bias using Egger's test",
                    "Create a comprehensive HTML report",
                    "Explain what heterogeneity means in my results",
                    "What's the difference between fixed and random effects?"
                ]
                
                for prompt in example_prompts:
                    gr.Button(prompt, size="sm").click(
                        lambda p=prompt: (p, None),
                        outputs=[msg, None]
                    )
                
                gr.Markdown("### 📊 Data Format")
                gr.Markdown("""
                Upload CSV data with columns:
                - `study_id`: Study identifier
                - `effect_size`: Effect size
                - `variance` or `se`: Variance or standard error
                - Additional columns as needed
                """)
        
        # Event handlers
        def update_session_display():
            if assistant.current_session_id:
                return f"Session: {assistant.current_session_id[:8]}..."
            return "No active session"
        
        def respond(message, history):
            if not message:
                return "", history
            
            new_msg, updated_history = assistant.process_message(message, history)
            session_display = update_session_display()
            return new_msg, updated_history, session_display
        
        msg.submit(respond, [msg, chatbot], [msg, chatbot, session_info])
        submit.click(respond, [msg, chatbot], [msg, chatbot, session_info])
        
        clear.click(
            lambda: ("", [], "No active session", None),
            outputs=[msg, chatbot, session_info, None]
        ).then(
            lambda: setattr(assistant, 'current_session_id', None)
        )
        
        # Add sample data upload area
        with gr.Accordion("📁 Upload Sample Data", open=False):
            gr.Markdown("Paste your CSV data here and click 'Send to Chat'")
            sample_data = gr.Textbox(
                lines=10,
                value="""study_id,effect_size,se
Study1,0.5,0.1
Study2,0.3,0.12
Study3,0.7,0.15
Study4,0.4,0.08
Study5,0.6,0.11""",
                label="CSV Data"
            )
            send_data = gr.Button("Send to Chat")
            
            send_data.click(
                lambda data: f"Please upload this CSV data:\n```csv\n{data}\n```",
                inputs=[sample_data],
                outputs=[msg]
            )
    
    return demo


if __name__ == "__main__":
    # Check for API keys
    if not OPENAI_AVAILABLE and not ANTHROPIC_AVAILABLE:
        print("⚠️ No LLM provider available. Please install openai or anthropic package.")
        print("pip install openai anthropic")
        exit(1)
    
    if OPENAI_AVAILABLE and not os.getenv("OPENAI_API_KEY"):
        print("⚠️ OPENAI_API_KEY not set. Please set it in your environment.")
        
    if ANTHROPIC_AVAILABLE and not os.getenv("ANTHROPIC_API_KEY"):
        print("⚠️ ANTHROPIC_API_KEY not set. Please set it in your environment.")
    
    # Launch the chatbot
    demo = create_chatbot_interface()
    demo.launch(server_name="0.0.0.0", server_port=7860, share=False)