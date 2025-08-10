"""
Comprehensive error handling and recovery system for Meta-Analysis Chatbot
"""

import os
import json
import traceback
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional, Callable
from functools import wraps
import hashlib
import pickle

# Configure logging
logging.basicConfig(
    level=os.getenv('LOG_LEVEL', 'INFO'),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class SessionRecoveryManager:
    """Manages session persistence and recovery"""
    
    def __init__(self, sessions_dir: str = "./sessions"):
        self.sessions_dir = Path(sessions_dir)
        self.sessions_dir.mkdir(exist_ok=True)
        self.recovery_dir = self.sessions_dir / ".recovery"
        self.recovery_dir.mkdir(exist_ok=True)
    
    def save_session_state(self, session_id: str, state: Dict[str, Any]) -> bool:
        """Save session state for recovery"""
        try:
            recovery_file = self.recovery_dir / f"{session_id}.json"
            with open(recovery_file, 'w') as f:
                json.dump({
                    'session_id': session_id,
                    'timestamp': datetime.now().isoformat(),
                    'state': state
                }, f, indent=2, default=str)
            return True
        except Exception as e:
            logger.error(f"Failed to save session state: {e}")
            return False
    
    def recover_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Recover a session from saved state"""
        try:
            recovery_file = self.recovery_dir / f"{session_id}.json"
            if recovery_file.exists():
                with open(recovery_file, 'r') as f:
                    data = json.load(f)
                    logger.info(f"Recovered session {session_id} from {data['timestamp']}")
                    return data['state']
        except Exception as e:
            logger.error(f"Failed to recover session: {e}")
        return None
    
    def list_recoverable_sessions(self) -> list:
        """List all sessions that can be recovered"""
        sessions = []
        for file in self.recovery_dir.glob("*.json"):
            try:
                with open(file, 'r') as f:
                    data = json.load(f)
                    sessions.append({
                        'session_id': data['session_id'],
                        'timestamp': data['timestamp']
                    })
            except Exception as e:
                logger.warning(f"Could not read recovery file {file}: {e}")
        return sorted(sessions, key=lambda x: x['timestamp'], reverse=True)
    
    def cleanup_old_sessions(self, max_age_hours: int = 24):
        """Remove old recovery files"""
        from datetime import timedelta
        cutoff = datetime.now() - timedelta(hours=max_age_hours)
        
        for file in self.recovery_dir.glob("*.json"):
            try:
                with open(file, 'r') as f:
                    data = json.load(f)
                    timestamp = datetime.fromisoformat(data['timestamp'])
                    if timestamp < cutoff:
                        file.unlink()
                        logger.info(f"Cleaned up old session: {file.name}")
            except Exception as e:
                logger.warning(f"Error cleaning up {file}: {e}")

class ErrorHandler:
    """Centralized error handling with recovery strategies"""
    
    def __init__(self):
        self.error_log = []
        self.recovery_strategies = {}
        self.max_retries = 3
    
    def register_recovery_strategy(self, error_type: str, strategy: Callable):
        """Register a recovery strategy for specific error types"""
        self.recovery_strategies[error_type] = strategy
    
    def handle_error(self, error: Exception, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """Handle an error with appropriate recovery strategy"""
        error_info = {
            'type': type(error).__name__,
            'message': str(error),
            'traceback': traceback.format_exc(),
            'timestamp': datetime.now().isoformat(),
            'context': context or {}
        }
        
        self.error_log.append(error_info)
        logger.error(f"Error occurred: {error_info['type']} - {error_info['message']}")
        
        # Try recovery strategy if available
        if error_info['type'] in self.recovery_strategies:
            try:
                recovery_result = self.recovery_strategies[error_info['type']](error, context)
                if recovery_result:
                    logger.info(f"Successfully recovered from {error_info['type']}")
                    return {'status': 'recovered', 'result': recovery_result}
            except Exception as recovery_error:
                logger.error(f"Recovery strategy failed: {recovery_error}")
        
        return {
            'status': 'error',
            'error': error_info,
            'user_message': self.get_user_friendly_message(error)
        }
    
    def get_user_friendly_message(self, error: Exception) -> str:
        """Convert technical errors to user-friendly messages"""
        error_messages = {
            'FileNotFoundError': "The requested file could not be found. Please check the file path.",
            'PermissionError': "Permission denied. Please check file permissions.",
            'JSONDecodeError': "Invalid data format. Please check your input.",
            'TimeoutError': "The operation timed out. Please try again.",
            'ConnectionError': "Connection failed. Please check your internet connection.",
            'ValueError': "Invalid input value. Please check your data.",
            'MemoryError': "Out of memory. Please try with smaller data.",
            'KeyError': "Missing required field in data.",
        }
        
        error_type = type(error).__name__
        return error_messages.get(error_type, f"An unexpected error occurred: {str(error)}")

def with_error_handling(recovery_manager: SessionRecoveryManager = None):
    """Decorator for automatic error handling and session recovery"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            error_handler = ErrorHandler()
            session_id = kwargs.get('session_id')
            
            try:
                # Save state before operation if session_id provided
                if session_id and recovery_manager:
                    state = {
                        'function': func.__name__,
                        'args': str(args)[:1000],  # Truncate for storage
                        'kwargs': str(kwargs)[:1000]
                    }
                    recovery_manager.save_session_state(session_id, state)
                
                # Execute function
                result = func(*args, **kwargs)
                
                # Clear recovery state on success
                if session_id and recovery_manager:
                    recovery_file = recovery_manager.recovery_dir / f"{session_id}.json"
                    if recovery_file.exists():
                        recovery_file.unlink()
                
                return result
                
            except Exception as e:
                # Handle error
                context = {
                    'function': func.__name__,
                    'session_id': session_id
                }
                error_result = error_handler.handle_error(e, context)
                
                # Try to recover if session exists
                if session_id and recovery_manager:
                    recovered_state = recovery_manager.recover_session(session_id)
                    if recovered_state:
                        error_result['recovered_state'] = recovered_state
                
                return error_result
        
        return wrapper
    return decorator

class RProcessManager:
    """Manages R subprocess with automatic recovery"""
    
    def __init__(self):
        self.process = None
        self.restart_count = 0
        self.max_restarts = 5
    
    def start_r_process(self, cmd: list):
        """Start R process with monitoring"""
        import subprocess
        
        try:
            self.process = subprocess.Popen(
                cmd,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1
            )
            logger.info(f"Started R process with PID {self.process.pid}")
            return True
        except Exception as e:
            logger.error(f"Failed to start R process: {e}")
            return False
    
    def check_health(self) -> bool:
        """Check if R process is healthy"""
        if not self.process:
            return False
        return self.process.poll() is None
    
    def restart_if_needed(self, cmd: list) -> bool:
        """Restart R process if it has crashed"""
        if not self.check_health():
            if self.restart_count < self.max_restarts:
                logger.warning(f"R process crashed, attempting restart {self.restart_count + 1}/{self.max_restarts}")
                self.restart_count += 1
                return self.start_r_process(cmd)
            else:
                logger.error("Max restart attempts reached for R process")
                return False
        return True
    
    def execute_with_retry(self, request: str, max_retries: int = 3) -> Optional[str]:
        """Execute R command with automatic retry on failure"""
        for attempt in range(max_retries):
            try:
                if not self.check_health():
                    logger.warning("R process not healthy, skipping execution")
                    return None
                
                self.process.stdin.write(request + "\n")
                self.process.stdin.flush()
                
                # Read response with timeout
                import select
                ready = select.select([self.process.stdout], [], [], 10)  # 10 second timeout
                if ready[0]:
                    response = self.process.stdout.readline()
                    return response
                else:
                    logger.warning(f"R process timeout on attempt {attempt + 1}")
                    
            except Exception as e:
                logger.error(f"R execution failed on attempt {attempt + 1}: {e}")
                
        return None

class InputValidator:
    """Validates and sanitizes user inputs"""
    
    @staticmethod
    def validate_file_upload(file_path: str, max_size_mb: int = 50) -> Dict[str, Any]:
        """Validate uploaded files"""
        from pathlib import Path
        
        path = Path(file_path)
        
        # Check existence
        if not path.exists():
            return {'valid': False, 'error': 'File does not exist'}
        
        # Check size
        size_mb = path.stat().st_size / (1024 * 1024)
        if size_mb > max_size_mb:
            return {'valid': False, 'error': f'File too large ({size_mb:.1f}MB > {max_size_mb}MB)'}
        
        # Check extension
        allowed_extensions = os.getenv('ALLOWED_EXTENSIONS', '.csv,.xlsx,.xls,.pdf,.png,.jpg,.jpeg,.gif').split(',')
        if path.suffix.lower() not in allowed_extensions:
            return {'valid': False, 'error': f'File type {path.suffix} not allowed'}
        
        # Check for malicious content (basic check)
        if path.suffix.lower() in ['.exe', '.dll', '.sh', '.bat', '.cmd']:
            return {'valid': False, 'error': 'Potentially malicious file type'}
        
        return {'valid': True, 'size_mb': size_mb, 'extension': path.suffix}
    
    @staticmethod
    def sanitize_text_input(text: str, max_length: int = 10000) -> str:
        """Sanitize text input to prevent injection attacks"""
        # Remove null bytes
        text = text.replace('\x00', '')
        
        # Truncate if too long
        if len(text) > max_length:
            text = text[:max_length]
        
        # Remove potentially dangerous characters for R/shell execution
        dangerous_chars = ['`', '$', '\\', ';', '&&', '||', '>', '<', '|']
        for char in dangerous_chars:
            text = text.replace(char, '')
        
        return text.strip()
    
    @staticmethod
    def validate_session_id(session_id: str) -> bool:
        """Validate session ID format"""
        import re
        # Allow only alphanumeric and hyphens, 8-64 characters
        pattern = r'^[a-zA-Z0-9\-]{8,64}$'
        return bool(re.match(pattern, session_id))

# Export main components
__all__ = [
    'SessionRecoveryManager',
    'ErrorHandler',
    'RProcessManager',
    'InputValidator',
    'with_error_handling'
]