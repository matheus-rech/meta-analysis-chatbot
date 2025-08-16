import json
import sys
import os
import base64
import tempfile
import subprocess
import time
# from utils.security_integration import apply_security_patches
# apply_security_patches()  # Temporarily disabled due to compatibility issues
import uuid
import shlex
from typing import Any, Dict
from utils.validators import InputValidator, ValidationError

# Minimal MCP server in Python over stdio
# It dispatches tool calls to the existing R scripts via Rscript mcp_tools.R

_HERE = os.path.dirname(__file__)
_LOCAL_ENTRY = os.path.join(_HERE, 'scripts', 'entry', 'mcp_tools.R')
_DOCKER_ENTRY = '/app/scripts/entry/mcp_tools.R'
SCRIPTS_ENTRY = _LOCAL_ENTRY if os.path.exists(_LOCAL_ENTRY) else _DOCKER_ENTRY
RSCRIPT_BIN = os.getenv('RSCRIPT_BIN', 'Rscript')
DEFAULT_TIMEOUT = int(os.getenv('RSCRIPT_TIMEOUT_SEC', '300'))
DEBUG_R = os.getenv('DEBUG_R') == '1'

# Whitelist of allowed tools to prevent command injection
ALLOWED_TOOLS = {
    'health_check',
    'initialize_meta_analysis',
    'upload_study_data',
    'perform_meta_analysis',
    'generate_forest_plot',
    'assess_publication_bias',
    'generate_report',
    'get_session_status',
    'execute_r_code',
}

TOOLS = list(ALLOWED_TOOLS)


def execute_r(tool: str, args: Dict[str, Any], session_path: str = None, timeout: int = DEFAULT_TIMEOUT) -> Dict[str, Any]:
    try:
        # Validate tool name against whitelist to prevent command injection
        if tool not in ALLOWED_TOOLS:
            return {'status': 'error', 'message': f'Invalid tool name: {tool}'}
        
        # Validate tool name format for extra safety
        tool = InputValidator.validate_string(tool, min_length=1, max_length=50, pattern='alphanumeric')
        
        # Validate and sanitize session path
        if session_path:
            session_path = os.path.abspath(session_path)
            # Ensure path is within allowed directory structure
            allowed_root = os.path.abspath(os.environ.get('SESSIONS_DIR', os.getcwd()))
            if not session_path.startswith(allowed_root):
                return {'status': 'error', 'message': 'Invalid session path'}
        
        # Validate args is a proper dictionary
        if not isinstance(args, dict):
            return {'status': 'error', 'message': 'Arguments must be a dictionary'}
        
        # Basic validation of common argument keys
        if 'session_id' in args:
            try:
                args['session_id'] = InputValidator.validate_session_id(args['session_id'])
            except ValidationError as e:
                return {'status': 'error', 'message': f'Invalid session_id: {e}'}
        
    except ValidationError as e:
        return {'status': 'error', 'message': f'Validation error: {e}'}
    except Exception as e:
        return {'status': 'error', 'message': f'Unexpected validation error: {e}'}
    
    session_dir = session_path or os.getcwd()
    # Write JSON args to a temp file to avoid OS arg-length limits
    args_file = None
    try:
        os.makedirs(os.path.join(session_dir, 'tmp'), exist_ok=True)
        args_file = os.path.join(session_dir, 'tmp', f'args_{tool}.json')
        with open(args_file, 'w', encoding='utf-8') as f:
            json.dump(args, f)
    except Exception:
        fd, args_file = tempfile.mkstemp(suffix='.json')
        os.close(fd)
        with open(args_file, 'w', encoding='utf-8') as f:
            json.dump(args, f)

    # Use shlex.quote to safely escape arguments
    proc = subprocess.Popen(
        [RSCRIPT_BIN, '--vanilla', SCRIPTS_ENTRY, shlex.quote(tool), shlex.quote(args_file), shlex.quote(session_dir)],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding='utf-8',
    )
    try:
        stdout, stderr = proc.communicate(timeout=timeout)
    except subprocess.TimeoutExpired:
        proc.kill()
        return {'status': 'error', 'message': 'R script execution timed out'}
    finally:
        try:
            if args_file and os.path.exists(args_file):
                os.remove(args_file)
        except Exception:
            pass

    if proc.returncode != 0:
        # Keep details behind DEBUG_R to avoid leaking in prod
        resp = {'status': 'error', 'message': 'R script failed to execute.'}
        if DEBUG_R:
            resp['stderr'] = (stderr or '').strip()
            resp['stdout'] = (stdout or '').strip()
        return resp

    try:
        return json.loads(stdout.strip())
    except Exception:
        resp = {'status': 'error', 'message': 'Invalid JSON from R', 'raw_output': (stdout or '').strip()}
        if DEBUG_R:
            resp['stderr'] = (stderr or '').strip()
        return resp


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
            'execute_r_code',
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
    # Compute session dir
    session_id = arguments.get('session_id')
    session_path = None
    sessions_root = os.environ.get('SESSIONS_DIR', os.path.join(os.getcwd(), 'sessions'))
    os.makedirs(sessions_root, exist_ok=True)
    if name == 'initialize_meta_analysis' and not session_id:
        session_id = uuid.uuid4().hex
        session_path = os.path.join(sessions_root, session_id)
        os.makedirs(session_path, exist_ok=True)
        arguments['session_id'] = session_id  # Pass it to R
    elif session_id:
        session_path = os.path.join(sessions_root, session_id)
        os.makedirs(session_path, exist_ok=True)

    try:
        print(f"Executing R tool: {name}", file=sys.stderr)
        result = execute_r(name, arguments, session_path)
        print(f"R tool {name} finished.", file=sys.stderr)
        # Ensure init returns session identifiers
        if name == 'initialize_meta_analysis':
            if isinstance(result, dict):
                result.setdefault('session_id', session_id)
                result.setdefault('session_path', session_path)
        return {
            'jsonrpc': '2.0',
            'id': request_id,
            'result': {'content': [{'type': 'text', 'text': json.dumps(result)}]},
        }
    except Exception as e:
        print(f"Error executing R tool {name}: {e}", file=sys.stderr)
        return {
            'jsonrpc': '2.0',
            'id': request_id,
            'result': {'content': [{'type': 'text', 'text': json.dumps({'status': 'error', 'message': str(e)})}]},
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
        if method == 'health':
            # Direct health check endpoint
            resp = {
                'jsonrpc': '2.0',
                'id': request_id,
                'result': {
                    'status': 'healthy',
                    'server': 'meta-analysis-mcp',
                    'version': '1.0.0',
                    'timestamp': str(time.time())
                }
            }
        elif method == 'tools/list':
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
