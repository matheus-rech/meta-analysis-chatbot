import os
import json
import subprocess
from utils.security_integration import apply_security_patches
apply_security_patches()
import threading
from typing import Optional

import gradio as gr
from mcp import ClientSession, StdioTransport
import base64
import traceback

# Initialize R and Python interop eagerly to ensure environment is ready
R_READY = False
PY_READY = False
R_STATUS = ""
PY_STATUS = ""

try:
    from rpy2 import robjects
    robjects.r("library(jsonlite)")
    robjects.r("library(meta)")
    robjects.r("library(metafor)")
    robjects.r("library(ggplot2)")
    robjects.r("library(knitr)")
    robjects.r("library(rmarkdown)")
    robjects.r("library(readxl)")
    robjects.r("library(base64enc)")
    robjects.r("library(DT)")
    robjects.r("library(reticulate)")
    R_READY = True
    R_STATUS = "R packages loaded"
except Exception as e:
    R_READY = False
    R_STATUS = f"R init failed: {e}\n{traceback.format_exc()}"

try:
    import sys as _sys
    PY_STATUS = f"Python OK: {_sys.version.split()[0]}"
    PY_READY = True
except Exception as e:
    PY_READY = False
    PY_STATUS = f"Python init failed: {e}\n{traceback.format_exc()}"

SERVER_SCRIPT_PATH = os.path.join(os.path.dirname(__file__), "server.py")
SERVER_CMD = ["python", SERVER_SCRIPT_PATH]

server_proc: Optional[subprocess.Popen] = None
server_lock = threading.Lock()


def start_server() -> None:
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
        
        # Wait for server to be ready
        if not _wait_for_server_ready():
            print("Warning: Server may not be fully ready")


def _wait_for_server_ready(timeout: int = 15) -> bool:
    """Wait for server to be ready by polling health check"""
    import time
    import json
    
    start_time = time.time()
    
    while time.time() - start_time < timeout:
        try:
            # Try a simple health check
            request = {
                "jsonrpc": "2.0",
                "method": "tools/call",
                "params": {"name": "health_check", "arguments": {}},
                "id": "health_check_startup"
            }
            
            if server_proc and server_proc.poll() is None:
                server_proc.stdin.write(json.dumps(request) + "\n")
                server_proc.stdin.flush()
                
                # Short timeout for reading response
                import select
                ready, _, _ = select.select([server_proc.stdout], [], [], 2)
                
                if ready:
                    response_line = server_proc.stdout.readline()
                    if response_line:
                        try:
                            response = json.loads(response_line)
                            if response.get("result"):
                                return True
                        except json.JSONDecodeError:
                            pass
            
            time.sleep(1)
            
        except Exception:
            time.sleep(1)
            
    return False


def stop_server() -> None:
    global server_proc
    with server_lock:
        if server_proc and server_proc.poll() is None:
            server_proc.terminate()
            try:
                server_proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                server_proc.kill()
        server_proc = None


def call_tool(tool: str, args: dict) -> str:
    start_server()
    assert server_proc is not None
    try:
        transport = StdioTransport(server_proc.stdin, server_proc.stdout)
        with ClientSession(transport) as session:
            tools = session.list_tools()
            if all(t.name != tool for t in tools):
                return f"Tool {tool} not available"
            result = session.call_tool(tool, args)
        return json.dumps(result, indent=2)
    finally:
        # Ensure we don't leak a background server in PoC
        stop_server()


def ui_health_check(detailed: bool) -> str:
    return call_tool("health_check", {"detailed": detailed})


def ui_init(name: str, study_type: str, effect_measure: str, analysis_model: str) -> str:
    return call_tool(
        "initialize_meta_analysis",
        {
            "name": name,
            "study_type": study_type,
            "effect_measure": effect_measure,
            "analysis_model": analysis_model,
        },
    )


def ui_upload(session_id: str, data: str, data_format: str, validation_level: str) -> str:
    # Accept CSV content directly in the textbox for PoC
    encoded = base64.b64encode(data.encode("utf-8")).decode("ascii")
    return call_tool(
        "upload_study_data",
        {
            "session_id": session_id,
            "data_format": data_format,
            "data_content": encoded,
            "validation_level": validation_level,
        },
    )


def ui_analyze(session_id: str, heterogeneity_test: bool, publication_bias: bool, sensitivity: bool) -> str:
    return call_tool(
        "perform_meta_analysis",
        {
            "session_id": session_id,
            "heterogeneity_test": heterogeneity_test,
            "publication_bias": publication_bias,
            "sensitivity_analysis": sensitivity,
        },
    )


def ui_forest(session_id: str, style: str, conf: float) -> str:
    return call_tool(
        "generate_forest_plot",
        {
            "session_id": session_id,
            "plot_style": style,
            "confidence_level": conf,
        },
    )


def ui_bias(session_id: str, methods: str) -> str:
    methods_list = [m.strip() for m in methods.split(",") if m.strip()]
    return call_tool(
        "assess_publication_bias",
        {
            "session_id": session_id,
            "methods": methods_list,
        },
    )


def ui_report(session_id: str, fmt: str, include_code: bool) -> str:
    return call_tool(
        "generate_report",
        {
            "session_id": session_id,
            "format": fmt,
            "include_code": include_code,
        },
    )


def ui_status(session_id: str) -> str:
    return call_tool("get_session_status", {"session_id": session_id})


def build_ui() -> gr.Blocks:
    with gr.Blocks() as demo:
        gr.Markdown("## MCP Meta-Analysis PoC (Gradio)")

        with gr.Row():
            gr.Markdown(f"**R status:** {R_STATUS}")
            gr.Markdown(f"**Python status:** {PY_STATUS}")

        with gr.Tab("Health"):
            detailed = gr.Checkbox(label="Detailed", value=False)
            out = gr.Code(label="Result")
            gr.Button("Health check").click(ui_health_check, inputs=[detailed], outputs=[out])

        with gr.Tab("Init"):
            name = gr.Textbox(label="Name", value="Demo Meta Analysis")
            study_type = gr.Dropdown(["clinical_trial","observational","diagnostic"], value="clinical_trial")
            effect_measure = gr.Dropdown(["OR","RR","MD","SMD","HR","PROP","MEAN"], value="OR")
            analysis_model = gr.Dropdown(["fixed","random","auto"], value="random")
            out_init = gr.Code(label="Result")
            gr.Button("Initialize").click(ui_init, [name, study_type, effect_measure, analysis_model], [out_init])

        with gr.Tab("Upload"):
            session_id = gr.Textbox(label="Session ID")
            data_format = gr.Dropdown(["csv","excel","revman"], value="csv")
            validation_level = gr.Dropdown(["basic","comprehensive"], value="basic")
            data = gr.Textbox(label="CSV content", lines=8)
            out_upload = gr.Code(label="Result")
            gr.Button("Upload").click(ui_upload, [session_id, data, data_format, validation_level], [out_upload])

        with gr.Tab("Analyze"):
            heterogeneity = gr.Checkbox(label="Heterogeneity test", value=True)
            pub_bias = gr.Checkbox(label="Publication bias", value=True)
            sensitivity = gr.Checkbox(label="Sensitivity analysis", value=False)
            out_analyze = gr.Code(label="Result")
            gr.Button("Run Analysis").click(ui_analyze, [session_id, heterogeneity, pub_bias, sensitivity], [out_analyze])

        with gr.Tab("Forest"):
            style = gr.Dropdown(["classic","modern","journal_specific"], value="classic")
            conf = gr.Slider(0.50, 0.99, value=0.95, step=0.01)
            out_forest = gr.Code(label="Result")
            gr.Button("Generate Forest").click(ui_forest, [session_id, style, conf], [out_forest])

        with gr.Tab("Bias"):
            methods = gr.Textbox(label="Methods (comma-separated)", value="funnel_plot, egger_test, begg_test, trim_fill")
            out_bias = gr.Code(label="Result")
            gr.Button("Assess Bias").click(ui_bias, [session_id, methods], [out_bias])

        with gr.Tab("Report"):
            fmt = gr.Dropdown(["html","pdf","word"], value="html")
            include_code = gr.Checkbox(label="Include code", value=False)
            out_report = gr.Code(label="Result")
            gr.Button("Generate Report").click(ui_report, [session_id, fmt, include_code], [out_report])

        with gr.Tab("Status"):
            out_status = gr.Code(label="Result")
            gr.Button("Get Status").click(ui_status, [session_id], [out_status])
    return demo


if __name__ == "__main__":
    demo = build_ui()
    demo.queue().launch(server_name="0.0.0.0", server_port=int(os.getenv("PORT", 7860)))
