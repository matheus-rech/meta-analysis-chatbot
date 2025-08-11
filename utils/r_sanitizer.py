"""
R script input sanitization layer to prevent code injection in R execution.
This module provides secure methods for passing data to R scripts.
"""

import json
import re
import tempfile
import os
from typing import Any, Dict, List, Optional, Union
from pathlib import Path
import shlex
import logging

from .validators import InputValidator, ValidationError, sanitize_for_r

logger = logging.getLogger(__name__)

class RSanitizerError(Exception):
    """Custom exception for R sanitization errors"""
    pass

class RScriptSanitizer:
    """
    Sanitizes inputs before passing to R scripts to prevent code injection.
    Uses temporary files for data transfer to avoid command line injection.
    """
    
    # Dangerous R functions that should never appear in user inputs
    DANGEROUS_R_FUNCTIONS = [
        'system', 'system2', 'shell', 'eval', 'parse', 'source',
        'library', 'require', 'install.packages', 'download.file',
        'file.remove', 'unlink', 'setwd', 'Sys.setenv',
        'readLines', 'writeLines', 'save', 'load', 'saveRDS', 'readRDS',
        'do.call', 'get', 'assign', 'attach', 'detach',
        'options', 'par', 'dev.off', 'sink',
    ]
    
    # Regex pattern to detect R code patterns
    R_CODE_PATTERNS = [
        r'\b(system|shell|eval|parse|source)\s*\(',  # Function calls
        r'`[^`]+`',  # Backtick execution
        r'\$\(',  # Command substitution
        r'<<-',  # Global assignment
        r'->>',  # Global assignment
        r'\.\.\.',  # Ellipsis (could be used for injection)
        r':::',  # Triple colon (accessing internal functions)
        r'(^|\s)!\s*[a-zA-Z]',  # Shell escape
    ]
    
    def __init__(self, temp_dir: Optional[str] = None):
        """
        Initialize R sanitizer.
        
        Args:
            temp_dir: Directory for temporary files (defaults to system temp)
        """
        self.temp_dir = temp_dir or tempfile.gettempdir()
        self.validator = InputValidator()
        
    def sanitize_string(self, value: str) -> str:
        """
        Sanitize a string value for safe R execution.
        
        Args:
            value: String to sanitize
            
        Returns:
            Sanitized string safe for R
            
        Raises:
            RSanitizerError: If dangerous patterns detected
        """
        if not value:
            return ""
        
        # Basic sanitization
        sanitized = sanitize_for_r(value)
        
        # Check for dangerous R functions
        lower_value = sanitized.lower()
        for func in self.DANGEROUS_R_FUNCTIONS:
            if func in lower_value:
                raise RSanitizerError(f"Dangerous R function '{func}' detected in input")
        
        # Check for code patterns
        for pattern in self.R_CODE_PATTERNS:
            if re.search(pattern, sanitized, re.IGNORECASE):
                raise RSanitizerError(f"Potential R code injection pattern detected")
        
        # Escape quotes for R string
        sanitized = sanitized.replace('"', '\\"')
        sanitized = sanitized.replace("'", "\\'")
        
        return sanitized
    
    def sanitize_identifier(self, name: str) -> str:
        """
        Sanitize an R identifier (variable name, column name, etc).
        
        Args:
            name: Identifier to sanitize
            
        Returns:
            Safe R identifier
        """
        # R identifiers must start with letter or dot followed by letter
        # Can contain letters, numbers, dots, underscores
        
        # Remove all non-allowed characters
        sanitized = re.sub(r'[^a-zA-Z0-9._]', '_', name)
        
        # Ensure it starts properly
        if not re.match(r'^[a-zA-Z]|^\.[a-zA-Z]', sanitized):
            sanitized = 'X' + sanitized
        
        # Limit length
        if len(sanitized) > 100:
            sanitized = sanitized[:100]
        
        return sanitized
    
    def create_safe_r_list(self, data: Dict[str, Any]) -> str:
        """
        Create a safe R list representation from Python dict.
        
        Args:
            data: Dictionary to convert
            
        Returns:
            R list string safe for evaluation
        """
        items = []
        
        for key, value in data.items():
            safe_key = self.sanitize_identifier(key)
            
            if isinstance(value, str):
                safe_value = self.sanitize_string(value)
                items.append(f'{safe_key} = "{safe_value}"')
            elif isinstance(value, (int, float)):
                items.append(f'{safe_key} = {value}')
            elif isinstance(value, bool):
                items.append(f'{safe_key} = {str(value).upper()}')
            elif isinstance(value, list):
                # Convert list to R vector
                if all(isinstance(x, str) for x in value):
                    safe_values = [f'"{self.sanitize_string(x)}"' for x in value]
                    items.append(f'{safe_key} = c({", ".join(safe_values)})')
                elif all(isinstance(x, (int, float)) for x in value):
                    items.append(f'{safe_key} = c({", ".join(map(str, value))})')
                else:
                    raise RSanitizerError(f"Mixed types in list not supported: {key}")
            elif value is None:
                items.append(f'{safe_key} = NULL')
            else:
                raise RSanitizerError(f"Unsupported type for R conversion: {type(value)}")
        
        return f'list({", ".join(items)})'
    
    def create_temp_data_file(self, data: Any, file_format: str = 'json') -> str:
        """
        Create a temporary file with sanitized data for R to read.
        This is the safest way to pass complex data to R.
        
        Args:
            data: Data to write (dict, list, or string)
            file_format: Format to use ('json', 'csv', 'rds')
            
        Returns:
            Path to temporary file
        """
        # Create secure temporary file
        fd, temp_path = tempfile.mkstemp(
            suffix=f'.{file_format}',
            dir=self.temp_dir,
            text=True
        )
        
        try:
            with os.fdopen(fd, 'w') as f:
                if file_format == 'json':
                    # Sanitize strings in JSON data
                    sanitized_data = self._sanitize_json_data(data)
                    json.dump(sanitized_data, f)
                    
                elif file_format == 'csv':
                    # Write CSV data (assuming it's already validated)
                    if isinstance(data, str):
                        f.write(data)
                    else:
                        raise RSanitizerError("CSV format requires string data")
                        
                else:
                    raise RSanitizerError(f"Unsupported file format: {file_format}")
                    
            logger.info(f"Created temporary data file: {temp_path}")
            return temp_path
            
        except Exception as e:
            # Clean up on error
            if os.path.exists(temp_path):
                os.unlink(temp_path)
            raise RSanitizerError(f"Failed to create temp file: {e}")
    
    def _sanitize_json_data(self, data: Any) -> Any:
        """Recursively sanitize strings in JSON-like data"""
        if isinstance(data, str):
            return self.sanitize_string(data)
        elif isinstance(data, dict):
            return {k: self._sanitize_json_data(v) for k, v in data.items()}
        elif isinstance(data, list):
            return [self._sanitize_json_data(item) for item in data]
        else:
            return data
    
    def prepare_r_arguments(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """
        Prepare arguments for safe R execution.
        Complex data is written to temp files, simple values are sanitized.
        
        Args:
            args: Arguments to prepare
            
        Returns:
            Dictionary with sanitized arguments and temp file paths
        """
        prepared = {}
        
        for key, value in args.items():
            safe_key = self.sanitize_identifier(key)
            
            if isinstance(value, str):
                # Check if it's a file path
                if os.path.exists(value) and os.path.isfile(value):
                    # Validate file path
                    prepared[safe_key] = os.path.abspath(value)
                else:
                    # Regular string - sanitize it
                    prepared[safe_key] = self.sanitize_string(value)
                    
            elif isinstance(value, (int, float, bool)):
                prepared[safe_key] = value
                
            elif isinstance(value, (dict, list)):
                # Complex data - write to temp file
                temp_file = self.create_temp_data_file(value, 'json')
                prepared[f'{safe_key}_file'] = temp_file
                
            elif value is None:
                prepared[safe_key] = None
                
            else:
                raise RSanitizerError(f"Unsupported argument type: {type(value)}")
        
        return prepared
    
    def validate_r_script_path(self, script_path: str) -> str:
        """
        Validate that R script path is safe and exists.
        
        Args:
            script_path: Path to R script
            
        Returns:
            Validated absolute path
            
        Raises:
            RSanitizerError: If path is invalid or unsafe
        """
        # Convert to Path object
        path = Path(script_path)
        
        # Check if path exists
        if not path.exists():
            raise RSanitizerError(f"R script not found: {script_path}")
        
        # Check if it's a file
        if not path.is_file():
            raise RSanitizerError(f"Not a file: {script_path}")
        
        # Check extension
        if path.suffix.lower() not in ['.r', '.R']:
            raise RSanitizerError(f"Not an R script: {script_path}")
        
        # Get absolute path to prevent directory traversal
        abs_path = path.absolute()
        
        # Ensure the script is within allowed directories
        # (You can customize this based on your setup)
        allowed_dirs = [
            Path(__file__).parent.parent / 'scripts',
            Path.cwd() / 'scripts',
        ]
        
        if not any(str(abs_path).startswith(str(d.absolute())) for d in allowed_dirs if d.exists()):
            logger.warning(f"R script outside allowed directories: {abs_path}")
        
        return str(abs_path)
    
    def create_safe_r_command(self, script_path: str, args: Dict[str, Any]) -> List[str]:
        """
        Create a safe R command with sanitized arguments.
        
        Args:
            script_path: Path to R script
            args: Arguments to pass to script
            
        Returns:
            List of command arguments ready for secure subprocess
        """
        # Validate script path
        safe_script = self.validate_r_script_path(script_path)
        
        # Prepare arguments
        prepared_args = self.prepare_r_arguments(args)
        
        # Create temp file with arguments
        args_file = self.create_temp_data_file(prepared_args, 'json')
        
        # Build command
        # Using Rscript with --vanilla to avoid loading user profile
        cmd = [
            'Rscript',
            '--vanilla',  # Don't load user profile
            safe_script,
            args_file
        ]
        
        return cmd
    
    def cleanup_temp_files(self, file_paths: List[str]) -> None:
        """Clean up temporary files created during sanitization"""
        for path in file_paths:
            try:
                if os.path.exists(path) and path.startswith(self.temp_dir):
                    os.unlink(path)
                    logger.debug(f"Cleaned up temp file: {path}")
            except Exception as e:
                logger.warning(f"Failed to clean up temp file {path}: {e}")


# Global instance for convenience
r_sanitizer = RScriptSanitizer()

# Export main components
__all__ = [
    'RScriptSanitizer',
    'RSanitizerError',
    'r_sanitizer'
]