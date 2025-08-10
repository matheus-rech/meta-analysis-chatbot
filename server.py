import json
import sys
import os
import base64
import tempfile
import subprocess
from typing import Any, Dict

# Minimal MCP server in Python over stdio
# It dispatches tool calls to the existing R scripts via Rscript mcp_tools.R

_HERE = os.path.dirname(__file__)
_PROJ = os.path.abspath(os.path.join(_HERE, '..', '..'))
SCRIPTS_ENTRY = os.path.join('/app' if os.path.exists('/app/scripts') else _PROJ, 'scripts', 'entry', 'mcp_tools.R')

TOOLS = [
    'health_check',
    'initialize_meta_analysis',
    'upload_study_data',
    'perform_meta_analysis',
    'generate_forest_plot',
    'assess_publication_bias',
    'generate_report',
    'get_session_status',
]


def execute_r(tool: str, args: Dict[str, Any], session_path: str = None, timeout: int = 30000) -> Dict[str, Any]:
    r_args = [tool, json.dumps(args), session_path or os.getcwd()]
    proc = subprocess.Popen(
        ['Rscript', '--vanilla', SCRIPTS_ENTRY] + r_args,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    try:
        stdout, stderr = proc.communicate(timeout=timeout)
    except subprocess.TimeoutExpired:
        proc.kill()
        raise RuntimeError('R script execution timed out')

    if proc.returncode != 0:
        # Sanitize error output to avoid leaking sensitive information
        sanitized_error = "R script failed to execute. Please check your input or contact support."
        raise RuntimeError(sanitized_error)

    try:
        return json.loads(stdout.strip())
    except Exception:
        return {'output': stdout.strip(), 'stderr': (stderr or '').strip()}


# Very small JSON-RPC 2.0 loop for MCP-like behavior
# For PoC we implement only list_tools and call_tool methods

def list_tools_resp(request_id):
    tools = [
        {'name': name, 'description': name}
        for name in [
            'health_check',
            'initialize_meta_analysis',
            'upload_study_data',
            'perform_meta_analysis',
            'generate_forest_plot',
            'assess_publication_bias',
            'generate_report',
            'get_session_status',
        ]
    ]
    return {
        'jsonrpc': '2.0',
        'id': request_id,
        'result': {'tools': tools},
    }


def call_tool_resp(request_id, name: str, arguments: Dict[str, Any]):
    if name not in TOOLS:
        return {
            'jsonrpc': '2.0',
            'id': request_id,
            'error': {'code': -32601, 'message': f'Unknown tool: {name}'},
        }
    # session_id is required for most tools; pass session dir if present
    session_id = arguments.get('session_id')
    session_path = None
    if session_id:
        sessions_dir = os.environ.get('SESSIONS_DIR', os.path.join(os.getcwd(), 'sessions'))
        session_path = os.path.join(sessions_dir, session_id)
        os.makedirs(session_path, exist_ok=True)

    try:
        result = execute_r(name, arguments, session_path)
        return {
            'jsonrpc': '2.0',
            'id': request_id,
            'result': {'content': [{'type': 'text', 'text': json.dumps(result)}]},
        }
    except Exception as e:
        return {
            'jsonrpc': '2.0',
            'id': request_id,
            'result': {'content': [{'type': 'text', 'text': json.dumps({'status':'error','message':str(e)})}]},
        }


def main():
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            req = json.loads(line)
        except Exception:
            continue
        method = req.get('method')
        request_id = req.get('id')
        if method == 'tools/list':
            resp = list_tools_resp(request_id)
        elif method == 'tools/call':
            params = req.get('params', {})
            name = params.get('name')
            arguments = params.get('arguments') or {}
            resp = call_tool_resp(request_id, name, arguments)
        else:
            resp = {
                'jsonrpc': '2.0',
                'id': request_id,
                'error': {'code': -32601, 'message': 'Method not found'},
            }
        sys.stdout.write(json.dumps(resp) + '\n')
        sys.stdout.flush()


if __name__ == '__main__':
    main()
