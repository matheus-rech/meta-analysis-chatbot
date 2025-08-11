"""
Security integration module to apply security measures across the codebase.
Provides easy-to-use wrappers, decorators, and drop-in replacements for secure operations.
"""

import os
import functools
from typing import Any, Dict, List, Optional, Union, Callable, Tuple
from pathlib import Path
import json
import subprocess

# Import all security modules
from .secure_subprocess import SecureSubprocess, SecureSubprocessError
from .validators import InputValidator, MetaAnalysisValidator, ValidationError, sanitize_for_r
from .r_sanitizer import RScriptSanitizer, RSanitizerError
from .file_security import SecureFileHandler, FileSecurityError
from .encoders import OutputEncoder, ResponseEncoder, EncodingError
from .security_logger import security_logger, SecurityEvent, security_logged
from .error_handler import ErrorHandler, SessionRecoveryManager, RProcessManager

# Global instances
secure_subprocess = SecureSubprocess()
input_validator = InputValidator()
meta_validator = MetaAnalysisValidator()
r_sanitizer = RScriptSanitizer()
file_handler = SecureFileHandler()
output_encoder = OutputEncoder()
response_encoder = ResponseEncoder()
error_handler = ErrorHandler()
session_recovery = SessionRecoveryManager()
r_process_manager = RProcessManager()

class SecurityConfig:
    """Central security configuration"""
    
    # Default security settings
    DEFAULTS = {
        'max_file_size': 50 * 1024 * 1024,  # 50MB
        'max_request_size': 100 * 1024 * 1024,  # 100MB
        'max_csv_rows': 10000,
        'session_timeout': 3600,  # 1 hour
        'subprocess_timeout': 300,  # 5 minutes
        'allowed_file_extensions': ['.csv', '.xlsx', '.xls', '.json', '.txt'],
        'enable_security_logging': True,
        'enable_input_validation': True,
        'enable_output_encoding': True,
        'strict_mode': False,  # Strict mode rejects suspicious inputs instead of sanitizing
    }
    
    def __init__(self):
        self.settings = self.DEFAULTS.copy()
        self._load_from_env()
    
    def _load_from_env(self):
        """Load settings from environment variables"""
        env_mappings = {
            'SECURITY_MAX_FILE_SIZE': ('max_file_size', int),
            'SECURITY_MAX_REQUEST_SIZE': ('max_request_size', int),
            'SECURITY_MAX_CSV_ROWS': ('max_csv_rows', int),
            'SECURITY_SESSION_TIMEOUT': ('session_timeout', int),
            'SECURITY_SUBPROCESS_TIMEOUT': ('subprocess_timeout', int),
            'SECURITY_STRICT_MODE': ('strict_mode', lambda x: x.lower() == 'true'),
        }
        
        for env_var, (setting, converter) in env_mappings.items():
            value = os.getenv(env_var)
            if value:
                try:
                    self.settings[setting] = converter(value)
                except ValueError:
                    pass
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get configuration value"""
        return self.settings.get(key, default)

# Global configuration instance
security_config = SecurityConfig()

# Decorators for automatic security

def validate_inputs(**validators):
    """
    Decorator to automatically validate function inputs.
    
    Usage:
        @validate_inputs(
            session_id='session_id',
            effect_measure='effect_measure',
            confidence_level=('number', {'min_value': 0.5, 'max_value': 0.99})
        )
        def my_function(session_id, effect_measure, confidence_level):
            # Function body
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # Get function signature
            import inspect
            sig = inspect.signature(func)
            bound_args = sig.bind(*args, **kwargs)
            bound_args.apply_defaults()
            
            # Validate each configured parameter
            for param_name, validator_config in validators.items():
                if param_name in bound_args.arguments:
                    value = bound_args.arguments[param_name]
                    
                    try:
                        # Simple validator (enum name)
                        if isinstance(validator_config, str):
                            if hasattr(input_validator, f'validate_{validator_config}'):
                                # Use specific validator method
                                validated = getattr(input_validator, f'validate_{validator_config}')(value)
                            else:
                                # Assume it's an enum
                                validated = input_validator.validate_enum(value, validator_config)
                            bound_args.arguments[param_name] = validated
                        
                        # Complex validator (type, options)
                        elif isinstance(validator_config, tuple):
                            validator_type, options = validator_config
                            if validator_type == 'string':
                                validated = input_validator.validate_string(value, **options)
                            elif validator_type == 'number':
                                validated = input_validator.validate_number(value, **options)
                            elif validator_type == 'boolean':
                                validated = input_validator.validate_boolean(value)
                            elif validator_type == 'list':
                                validated = input_validator.validate_list(value, **options)
                            elif validator_type == 'json':
                                validated = input_validator.validate_json(value)
                            elif validator_type == 'filename':
                                validated = input_validator.validate_filename(value, **options)
                            elif validator_type == 'csv':
                                validated = input_validator.validate_csv_content(value, **options)
                            elif validator_type == 'base64':
                                validated = input_validator.validate_base64(value, **options)
                            else:
                                raise ValueError(f"Unknown validator type: {validator_type}")
                            bound_args.arguments[param_name] = validated
                        
                    except ValidationError as e:
                        security_logger.log_input_validation_failure(
                            field=param_name,
                            reason=str(e),
                            value_type=type(value).__name__,
                            session_id=kwargs.get('session_id')
                        )
                        
                        if security_config.get('strict_mode'):
                            raise
                        else:
                            # In non-strict mode, use default or None
                            param = sig.parameters[param_name]
                            if param.default is not param.empty:
                                bound_args.arguments[param_name] = param.default
                            else:
                                bound_args.arguments[param_name] = None
            
            # Call function with validated arguments
            return func(*bound_args.args, **bound_args.kwargs)
        
        return wrapper
    return decorator

def secure_subprocess_call(log_category: str = SecurityEvent.SUBPROCESS):
    """
    Decorator to automatically use secure subprocess for command execution.
    
    Usage:
        @secure_subprocess_call()
        def run_analysis(cmd: List[str]):
            return subprocess.run(cmd)  # Will be intercepted and secured
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # Override subprocess module temporarily
            import subprocess as _subprocess
            original_run = _subprocess.run
            original_popen = _subprocess.Popen
            
            def secure_run(cmd, **run_kwargs):
                # Log the attempt
                security_logger.log_subprocess_execution(
                    command=cmd if isinstance(cmd, list) else [cmd],
                    success=False,  # Not yet executed
                    session_id=kwargs.get('session_id')
                )
                
                # Use secure subprocess
                try:
                    result = secure_subprocess.run(cmd, **run_kwargs)
                    security_logger.log_subprocess_execution(
                        command=cmd if isinstance(cmd, list) else [cmd],
                        success=True,
                        return_code=result.returncode,
                        session_id=kwargs.get('session_id')
                    )
                    return result
                except Exception as e:
                    security_logger.log_subprocess_execution(
                        command=cmd if isinstance(cmd, list) else [cmd],
                        success=False,
                        session_id=kwargs.get('session_id'),
                        details={'error': str(e)}
                    )
                    raise
            
            def secure_popen(cmd, **popen_kwargs):
                # Remove shell=True if present
                popen_kwargs.pop('shell', None)
                return secure_subprocess.popen(cmd, **popen_kwargs)
            
            # Monkey patch subprocess
            _subprocess.run = secure_run
            _subprocess.Popen = secure_popen
            
            try:
                return func(*args, **kwargs)
            finally:
                # Restore original subprocess
                _subprocess.run = original_run
                _subprocess.Popen = original_popen
        
        return wrapper
    return decorator

def encode_output(output_type: str = 'json'):
    """
    Decorator to automatically encode function output.
    
    Usage:
        @encode_output('html')
        def get_report():
            return {"title": "Report", "content": "<script>alert('xss')</script>"}
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            result = func(*args, **kwargs)
            
            if output_type == 'json':
                return response_encoder.encode_json_response(result)
            elif output_type == 'html':
                return response_encoder.encode_html_response(result)
            elif output_type == 'gradio':
                return response_encoder.encode_gradio_response(result)
            elif output_type == 'csv':
                if isinstance(result, list):
                    return output_encoder.encode_csv(result)
                else:
                    raise ValueError("CSV encoding requires list of rows")
            else:
                return result
        
        return wrapper
    return decorator

# Secure wrapper functions

def secure_r_execution(script_path: str, 
                      args: Dict[str, Any],
                      session_id: Optional[str] = None,
                      timeout: Optional[int] = None) -> Dict[str, Any]:
    """
    Securely execute an R script with sanitized inputs.
    
    Args:
        script_path: Path to R script
        args: Arguments to pass to script
        session_id: Session ID for tracking
        timeout: Execution timeout
        
    Returns:
        Execution result
    """
    # Validate script path
    safe_script = r_sanitizer.validate_r_script_path(script_path)
    
    # Prepare safe arguments
    safe_args = r_sanitizer.prepare_r_arguments(args)
    
    # Add session info
    if session_id:
        safe_args['session_id'] = input_validator.validate_session_id(session_id)
    
    # Create command
    cmd = r_sanitizer.create_safe_r_command(safe_script, safe_args)
    
    # Execute with secure subprocess
    timeout = timeout or security_config.get('subprocess_timeout')
    
    try:
        result = secure_subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=True
        )
        
        # Parse output
        try:
            return json.loads(result.stdout)
        except json.JSONDecodeError:
            return {
                'status': 'success',
                'output': result.stdout,
                'stderr': result.stderr
            }
            
    except subprocess.CalledProcessError as e:
        return {
            'status': 'error',
            'error': f"R script failed with code {e.returncode}",
            'stdout': e.stdout,
            'stderr': e.stderr
        }
    except Exception as e:
        return {
            'status': 'error',
            'error': str(e)
        }
    finally:
        # Cleanup temp files
        temp_files = [v for k, v in safe_args.items() if k.endswith('_file')]
        r_sanitizer.cleanup_temp_files(temp_files)

def secure_file_upload(file_path: str,
                      original_filename: str,
                      session_id: Optional[str] = None,
                      allowed_extensions: Optional[List[str]] = None) -> Dict[str, Any]:
    """
    Securely process file upload with validation and sandboxing.
    
    Args:
        file_path: Path to uploaded file
        original_filename: Original filename
        session_id: Session ID
        allowed_extensions: Override allowed extensions
        
    Returns:
        File metadata including secure storage path
    """
    # Configure file handler if needed
    if allowed_extensions:
        handler = SecureFileHandler(
            allowed_extensions={ext: file_handler.allowed_extensions.get(ext, ['application/octet-stream']) 
                               for ext in allowed_extensions}
        )
    else:
        handler = file_handler
    
    try:
        # Validate and store file
        metadata = handler.validate_and_store_file(
            file_path=file_path,
            original_filename=original_filename,
            session_id=session_id
        )
        
        # Log successful upload
        security_logger.log_file_upload(
            filename=metadata['filename'],
            size=metadata['size'],
            file_type=metadata['content_type'],
            validation_result='success',
            session_id=session_id,
            details=metadata
        )
        
        return metadata
        
    except FileSecurityError as e:
        # Log failed upload
        security_logger.log_file_upload(
            filename=original_filename,
            size=0,
            file_type='unknown',
            validation_result='failed',
            session_id=session_id,
            details={'error': str(e)}
        )
        raise

def secure_response(data: Any,
                   response_type: str = 'json',
                   encode_html: bool = True) -> Union[str, Dict[str, Any]]:
    """
    Create secure response with proper encoding.
    
    Args:
        data: Response data
        response_type: Type of response (json, html, csv, file)
        encode_html: Whether to HTML-encode strings
        
    Returns:
        Encoded response
    """
    if response_type == 'json':
        return response_encoder.encode_json_response(data)
    elif response_type == 'html' and encode_html:
        return response_encoder.encode_html_response(data)
    elif response_type == 'csv' and isinstance(data, list):
        return output_encoder.encode_csv(data)
    elif response_type == 'file' and isinstance(data, dict):
        return response_encoder.encode_file_download(
            content=data.get('content', ''),
            filename=data.get('filename', 'download'),
            content_type=data.get('content_type', 'application/octet-stream')
        )
    else:
        return data

# Drop-in replacements for common insecure patterns

class SecurePatterns:
    """Drop-in replacements for common insecure patterns"""
    
    @staticmethod
    def safe_subprocess_run(cmd: Union[str, List[str]], **kwargs) -> subprocess.CompletedProcess:
        """Safe replacement for subprocess.run"""
        kwargs.pop('shell', None)  # Never allow shell=True
        return secure_subprocess.run(cmd, **kwargs)
    
    @staticmethod
    def safe_subprocess_popen(cmd: Union[str, List[str]], **kwargs) -> subprocess.Popen:
        """Safe replacement for subprocess.Popen"""
        kwargs.pop('shell', None)  # Never allow shell=True
        return secure_subprocess.popen(cmd, **kwargs)
    
    @staticmethod
    def safe_json_loads(json_str: str) -> Any:
        """Safe JSON parsing with validation"""
        return input_validator.validate_json(json_str)
    
    @staticmethod
    def safe_file_open(filename: str, mode: str = 'r', **kwargs):
        """Safe file opening with validation"""
        # Validate filename
        safe_filename = input_validator.validate_filename(filename)
        
        # Check if file exists and is within allowed paths
        file_path = Path(safe_filename).resolve()
        
        # Add your allowed directories here
        allowed_dirs = [
            Path.cwd(),
            Path(os.getenv('UPLOAD_DIR', './uploads')),
            Path(os.getenv('DATA_DIR', './data')),
        ]
        
        if not any(str(file_path).startswith(str(d.resolve())) for d in allowed_dirs):
            raise PermissionError(f"Access to file outside allowed directories: {filename}")
        
        return open(file_path, mode, **kwargs)

# Initialize security in existing modules

def apply_security_patches():
    """Apply security patches to existing modules"""
    import sys
    
    # Create secure subprocess module
    class SecureSubprocessModule:
        run = SecurePatterns.safe_subprocess_run
        Popen = SecurePatterns.safe_subprocess_popen
        check_output = secure_subprocess.check_output
        check_call = secure_subprocess.check_call
        
        # Copy other attributes from original subprocess
        def __getattr__(self, name):
            import subprocess
            return getattr(subprocess, name)
    
    # Patch subprocess in all loaded modules
    secure_subprocess_module = SecureSubprocessModule()
    
    for module_name, module in sys.modules.items():
        if module and hasattr(module, 'subprocess'):
            # Replace subprocess imports
            setattr(module, 'subprocess', secure_subprocess_module)

# Export main components
__all__ = [
    'security_config',
    'validate_inputs',
    'secure_subprocess_call',
    'encode_output',
    'secure_r_execution',
    'secure_file_upload',
    'secure_response',
    'SecurePatterns',
    'apply_security_patches',
    # Re-export security modules
    'secure_subprocess',
    'input_validator',
    'meta_validator',
    'r_sanitizer',
    'file_handler',
    'output_encoder',
    'response_encoder',
    'security_logger',
    'error_handler',
]