"""
Secure subprocess execution wrapper to prevent command injection attacks.
All subprocess calls should use this wrapper instead of direct subprocess.Popen
"""

import subprocess
import shlex
import os
import logging
from typing import List, Dict, Any, Optional, Union, Tuple
from pathlib import Path
import threading
import time

logger = logging.getLogger(__name__)

# Whitelist of allowed commands
ALLOWED_COMMANDS = {
    'python': {'allowed_args_prefix': ['-m', '--version', '--help']},
    'python3': {'allowed_args_prefix': ['-m', '--version', '--help']},
    'Rscript': {'allowed_args_prefix': ['--vanilla', '--version', '--help']},
    'node': {'allowed_args_prefix': ['--version', '--help']},
    'npm': {'allowed_args_prefix': ['--version', 'install', 'run']},
    'npx': {'allowed_args_prefix': []},
}

# Dangerous patterns that should never appear in commands
DANGEROUS_PATTERNS = [
    ';', '&&', '||', '|', '>', '<', '>>', '<<',  # Shell operators
    '`', '$', '$(', '${',  # Command substitution
    '\\n', '\\r', '\\t',  # Newlines and special chars
    '../', '..\\',  # Directory traversal
    'rm ', 'del ', 'format',  # Dangerous commands
    'eval', 'exec', 'system',  # Code execution
]

class SecureSubprocessError(Exception):
    """Custom exception for subprocess security violations"""
    pass

class SecureSubprocess:
    """
    Secure wrapper for subprocess execution with:
    - Command whitelisting
    - Argument sanitization
    - Timeout protection
    - No shell execution
    - Resource limits
    """
    
    def __init__(self, 
                 timeout: int = 300,
                 max_output_size: int = 50 * 1024 * 1024,  # 50MB
                 allowed_commands: Dict[str, Dict] = None):
        self.timeout = timeout
        self.max_output_size = max_output_size
        self.allowed_commands = allowed_commands or ALLOWED_COMMANDS
        self._running_processes = {}
        self._lock = threading.Lock()
    
    def validate_command(self, cmd: List[str]) -> None:
        """Validate command against whitelist and security rules"""
        if not cmd:
            raise SecureSubprocessError("Empty command")
        
        # Extract the base command
        base_cmd = os.path.basename(cmd[0])
        
        # Check if command is in whitelist
        if base_cmd not in self.allowed_commands:
            raise SecureSubprocessError(f"Command '{base_cmd}' not in whitelist")
        
        # Check for dangerous patterns in all arguments
        for arg in cmd:
            for pattern in DANGEROUS_PATTERNS:
                if pattern in str(arg):
                    raise SecureSubprocessError(f"Dangerous pattern '{pattern}' detected in arguments")
        
        # Validate command arguments if restrictions exist
        if len(cmd) > 1:
            allowed_prefixes = self.allowed_commands[base_cmd].get('allowed_args_prefix', [])
            if allowed_prefixes:
                # Check if first argument matches any allowed prefix
                first_arg = cmd[1]
                if not any(first_arg.startswith(prefix) for prefix in allowed_prefixes):
                    # Special handling for file paths (common case)
                    if not (os.path.exists(first_arg) or first_arg.endswith('.R') or first_arg.endswith('.py')):
                        logger.warning(f"Argument '{first_arg}' not in allowed prefixes for {base_cmd}")
    
    def sanitize_arguments(self, args: List[str]) -> List[str]:
        """Sanitize command arguments to prevent injection"""
        sanitized = []
        for arg in args:
            # Convert to string and strip whitespace
            arg_str = str(arg).strip()
            
            # Use shlex.quote for proper escaping
            quoted = shlex.quote(arg_str)
            
            # Additional validation for file paths
            if '/' in arg_str or '\\' in arg_str:
                # Normalize and validate paths
                try:
                    path = Path(arg_str)
                    # Prevent directory traversal
                    if '..' in path.parts:
                        raise SecureSubprocessError(f"Directory traversal detected in path: {arg_str}")
                    # Use resolved path
                    quoted = shlex.quote(str(path))
                except Exception:
                    # If not a valid path, keep the quoted version
                    pass
            
            sanitized.append(quoted)
        
        return sanitized
    
    def run(self, 
            cmd: Union[str, List[str]], 
            input_data: Optional[str] = None,
            cwd: Optional[str] = None,
            env: Optional[Dict[str, str]] = None,
            capture_output: bool = True,
            text: bool = True,
            check: bool = True) -> subprocess.CompletedProcess:
        """
        Secure replacement for subprocess.run
        
        Args:
            cmd: Command to execute (list preferred, string will be split)
            input_data: Input to send to process stdin
            cwd: Working directory
            env: Environment variables (merged with current env)
            capture_output: Whether to capture stdout/stderr
            text: Whether to return output as text
            check: Whether to raise exception on non-zero exit
            
        Returns:
            subprocess.CompletedProcess object
        """
        # Convert string command to list
        if isinstance(cmd, str):
            cmd = shlex.split(cmd)
        
        # Validate command
        self.validate_command(cmd)
        
        # Sanitize arguments (skip the command itself)
        if len(cmd) > 1:
            cmd = [cmd[0]] + self.sanitize_arguments(cmd[1:])
        
        # Prepare environment
        if env:
            full_env = os.environ.copy()
            full_env.update(env)
        else:
            full_env = None
        
        # Log execution for audit trail
        logger.info(f"Executing command: {' '.join(cmd)}")
        
        try:
            # Never use shell=True
            result = subprocess.run(
                cmd,
                input=input_data,
                cwd=cwd,
                env=full_env,
                capture_output=capture_output,
                text=text,
                timeout=self.timeout,
                check=False  # We'll handle errors ourselves
            )
            
            # Check output size if captured
            if capture_output:
                output_size = len(result.stdout or '') + len(result.stderr or '')
                if output_size > self.max_output_size:
                    raise SecureSubprocessError(f"Output size ({output_size}) exceeds maximum ({self.max_output_size})")
            
            # Check return code if requested
            if check and result.returncode != 0:
                raise subprocess.CalledProcessError(result.returncode, cmd, result.stdout, result.stderr)
            
            return result
            
        except subprocess.TimeoutExpired as e:
            logger.error(f"Command timed out after {self.timeout}s: {' '.join(cmd)}")
            raise SecureSubprocessError(f"Command execution timed out after {self.timeout} seconds") from e
        except Exception as e:
            logger.error(f"Command execution failed: {' '.join(cmd)} - {str(e)}")
            raise
    
    def popen(self,
              cmd: Union[str, List[str]],
              stdin=None,
              stdout=None,
              stderr=None,
              cwd: Optional[str] = None,
              env: Optional[Dict[str, str]] = None,
              text: bool = True) -> subprocess.Popen:
        """
        Secure replacement for subprocess.Popen
        
        Args:
            cmd: Command to execute
            stdin, stdout, stderr: Standard streams
            cwd: Working directory
            env: Environment variables
            text: Whether to use text mode
            
        Returns:
            subprocess.Popen object
        """
        # Convert string command to list
        if isinstance(cmd, str):
            cmd = shlex.split(cmd)
        
        # Validate command
        self.validate_command(cmd)
        
        # Sanitize arguments
        if len(cmd) > 1:
            cmd = [cmd[0]] + self.sanitize_arguments(cmd[1:])
        
        # Prepare environment
        if env:
            full_env = os.environ.copy()
            full_env.update(env)
        else:
            full_env = None
        
        # Log execution
        logger.info(f"Starting process: {' '.join(cmd)}")
        
        # Create process (never use shell=True)
        proc = subprocess.Popen(
            cmd,
            stdin=stdin,
            stdout=stdout,
            stderr=stderr,
            cwd=cwd,
            env=full_env,
            text=text,
            bufsize=1 if text else -1,
            shell=False  # Explicitly set to False
        )
        
        # Track running process
        with self._lock:
            self._running_processes[proc.pid] = {
                'proc': proc,
                'cmd': cmd,
                'start_time': time.time()
            }
        
        # Start a monitoring thread for timeout
        threading.Thread(target=self._monitor_process, args=(proc,), daemon=True).start()
        
        return proc
    
    def _monitor_process(self, proc: subprocess.Popen) -> None:
        """Monitor process for timeout"""
        start_time = time.time()
        
        while proc.poll() is None:
            if time.time() - start_time > self.timeout:
                logger.warning(f"Process {proc.pid} exceeded timeout, terminating")
                proc.terminate()
                try:
                    proc.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    proc.kill()
                break
            time.sleep(1)
        
        # Clean up tracking
        with self._lock:
            self._running_processes.pop(proc.pid, None)

# Global instance for easy access
secure_subprocess = SecureSubprocess()

# Convenience functions that mirror subprocess API
def run(*args, **kwargs) -> subprocess.CompletedProcess:
    """Secure replacement for subprocess.run"""
    return secure_subprocess.run(*args, **kwargs)

def popen(*args, **kwargs) -> subprocess.Popen:
    """Secure replacement for subprocess.Popen"""
    return secure_subprocess.popen(*args, **kwargs)

def check_output(cmd: Union[str, List[str]], **kwargs) -> str:
    """Secure replacement for subprocess.check_output"""
    kwargs['capture_output'] = True
    kwargs['check'] = True
    kwargs['text'] = True
    result = secure_subprocess.run(cmd, **kwargs)
    return result.stdout

def check_call(cmd: Union[str, List[str]], **kwargs) -> int:
    """Secure replacement for subprocess.check_call"""
    kwargs['check'] = True
    result = secure_subprocess.run(cmd, **kwargs)
    return result.returncode