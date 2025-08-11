"""
Centralized input validation module with comprehensive validators.
Uses whitelisting approach for maximum security.
"""

import re
import os
from typing import Any, Dict, List, Optional, Union, Tuple
from pathlib import Path
import json
import base64
from datetime import datetime
import hashlib

class ValidationError(Exception):
    """Custom exception for validation errors"""
    pass

class InputValidator:
    """
    Comprehensive input validation with whitelisting approach.
    All validators return sanitized values or raise ValidationError.
    """
    
    # Regex patterns for common validations
    PATTERNS = {
        'session_id': re.compile(r'^[a-zA-Z0-9\-]{8,64}$'),
        'alphanumeric': re.compile(r'^[a-zA-Z0-9]+$'),
        'alpha': re.compile(r'^[a-zA-Z]+$'),
        'numeric': re.compile(r'^[0-9]+$'),
        'decimal': re.compile(r'^-?\d+\.?\d*$'),
        'email': re.compile(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'),
        'filename': re.compile(r'^[a-zA-Z0-9\-_\.]+$'),
        'safe_text': re.compile(r'^[a-zA-Z0-9\s\-_\.,!?()\'"]+$'),
    }
    
    # Allowed values for enums
    ALLOWED_VALUES = {
        'study_type': ['clinical_trial', 'observational', 'diagnostic'],
        'effect_measure': ['OR', 'RR', 'MD', 'SMD', 'HR', 'PROP', 'MEAN'],
        'analysis_model': ['fixed', 'random', 'auto'],
        'data_format': ['csv', 'excel', 'revman'],
        'validation_level': ['basic', 'comprehensive'],
        'plot_style': ['classic', 'modern', 'journal_specific'],
        'report_format': ['html', 'pdf', 'word'],
        'file_extension': ['.csv', '.xlsx', '.xls', '.rds', '.png', '.jpg', '.pdf'],
        'bias_methods': ['funnel_plot', 'egger_test', 'begg_test', 'trim_fill'],
    }
    
    # Maximum lengths for different input types
    MAX_LENGTHS = {
        'name': 255,
        'session_id': 64,
        'filename': 255,
        'text': 10000,
        'csv_content': 10 * 1024 * 1024,  # 10MB
        'base64_content': 50 * 1024 * 1024,  # 50MB encoded
    }
    
    @classmethod
    def validate_string(cls, value: Any, 
                       min_length: int = 0, 
                       max_length: Optional[int] = None,
                       pattern: Optional[str] = None,
                       allowed_chars: Optional[str] = None) -> str:
        """
        Validate and sanitize string input.
        
        Args:
            value: Input value to validate
            min_length: Minimum required length
            max_length: Maximum allowed length
            pattern: Regex pattern name from PATTERNS or custom pattern
            allowed_chars: String of allowed characters
            
        Returns:
            Sanitized string value
            
        Raises:
            ValidationError: If validation fails
        """
        if value is None:
            raise ValidationError("Value cannot be None")
        
        # Convert to string and strip
        str_value = str(value).strip()
        
        # Check length
        if len(str_value) < min_length:
            raise ValidationError(f"String too short (min: {min_length})")
        
        if max_length and len(str_value) > max_length:
            raise ValidationError(f"String too long (max: {max_length})")
        
        # Check pattern
        if pattern:
            if isinstance(pattern, str) and pattern in cls.PATTERNS:
                regex = cls.PATTERNS[pattern]
            else:
                regex = re.compile(pattern)
            
            if not regex.match(str_value):
                raise ValidationError(f"String does not match required pattern: {pattern}")
        
        # Check allowed characters
        if allowed_chars:
            for char in str_value:
                if char not in allowed_chars:
                    raise ValidationError(f"Character '{char}' not allowed")
        
        return str_value
    
    @classmethod
    def validate_enum(cls, value: Any, enum_name: str) -> str:
        """Validate value against allowed enum values"""
        if enum_name not in cls.ALLOWED_VALUES:
            raise ValidationError(f"Unknown enum type: {enum_name}")
        
        str_value = str(value).lower() if value else ''
        allowed = cls.ALLOWED_VALUES[enum_name]
        
        if str_value not in allowed:
            raise ValidationError(f"Value '{str_value}' not in allowed values: {allowed}")
        
        return str_value
    
    @classmethod
    def validate_number(cls, value: Any, 
                       min_value: Optional[float] = None,
                       max_value: Optional[float] = None,
                       allow_negative: bool = True,
                       allow_decimal: bool = True) -> Union[int, float]:
        """Validate numeric input"""
        try:
            if allow_decimal:
                num_value = float(value)
            else:
                num_value = int(value)
        except (ValueError, TypeError):
            raise ValidationError(f"Invalid number: {value}")
        
        if not allow_negative and num_value < 0:
            raise ValidationError("Negative numbers not allowed")
        
        if min_value is not None and num_value < min_value:
            raise ValidationError(f"Number too small (min: {min_value})")
        
        if max_value is not None and num_value > max_value:
            raise ValidationError(f"Number too large (max: {max_value})")
        
        return num_value
    
    @classmethod
    def validate_boolean(cls, value: Any) -> bool:
        """Validate boolean input"""
        if isinstance(value, bool):
            return value
        
        if isinstance(value, str):
            lower_val = value.lower()
            if lower_val in ('true', '1', 'yes', 'on'):
                return True
            elif lower_val in ('false', '0', 'no', 'off'):
                return False
        
        raise ValidationError(f"Invalid boolean value: {value}")
    
    @classmethod
    def validate_session_id(cls, session_id: Any) -> str:
        """Validate session ID format"""
        return cls.validate_string(
            session_id,
            min_length=8,
            max_length=cls.MAX_LENGTHS['session_id'],
            pattern='session_id'
        )
    
    @classmethod
    def validate_filename(cls, filename: Any, 
                         allowed_extensions: Optional[List[str]] = None) -> str:
        """Validate filename for safety"""
        filename_str = cls.validate_string(
            filename,
            min_length=1,
            max_length=cls.MAX_LENGTHS['filename'],
            pattern='filename'
        )
        
        # Check for directory traversal
        if '..' in filename_str or '/' in filename_str or '\\' in filename_str:
            raise ValidationError("Invalid filename: contains path separators")
        
        # Check extension
        if allowed_extensions:
            ext = Path(filename_str).suffix.lower()
            if ext not in allowed_extensions:
                raise ValidationError(f"File extension '{ext}' not allowed")
        
        return filename_str
    
    @classmethod
    def validate_base64(cls, value: Any, max_decoded_size: Optional[int] = None) -> str:
        """Validate base64 encoded data"""
        if not value:
            raise ValidationError("Empty base64 data")
        
        str_value = str(value).strip()
        
        # Check if it looks like base64
        if not re.match(r'^[A-Za-z0-9+/]*={0,2}$', str_value):
            raise ValidationError("Invalid base64 format")
        
        # Check encoded size
        if len(str_value) > cls.MAX_LENGTHS['base64_content']:
            raise ValidationError("Base64 data too large")
        
        # Try to decode to validate
        try:
            decoded = base64.b64decode(str_value)
            
            # Check decoded size
            if max_decoded_size and len(decoded) > max_decoded_size:
                raise ValidationError(f"Decoded data too large (max: {max_decoded_size} bytes)")
            
        except Exception:
            raise ValidationError("Invalid base64 encoding")
        
        return str_value
    
    @classmethod
    def validate_csv_content(cls, content: Any, max_rows: int = 10000) -> str:
        """Validate CSV content"""
        str_content = cls.validate_string(
            content,
            max_length=cls.MAX_LENGTHS['csv_content']
        )
        
        # Basic CSV validation
        lines = str_content.strip().split('\n')
        if len(lines) > max_rows:
            raise ValidationError(f"CSV has too many rows (max: {max_rows})")
        
        # Check for suspicious patterns
        dangerous_patterns = ['=', '@', '+', '-', '|']
        first_chars = {line[0] for line in lines if line}
        if any(char in dangerous_patterns for char in first_chars):
            raise ValidationError("CSV contains potentially dangerous formula injection")
        
        return str_content
    
    @classmethod
    def validate_json(cls, value: Any) -> Dict[str, Any]:
        """Validate JSON data"""
        if isinstance(value, dict):
            return value
        
        if isinstance(value, str):
            try:
                parsed = json.loads(value)
                if not isinstance(parsed, dict):
                    raise ValidationError("JSON must be an object")
                return parsed
            except json.JSONDecodeError as e:
                raise ValidationError(f"Invalid JSON: {e}")
        
        raise ValidationError("Value must be JSON object or string")
    
    @classmethod
    def validate_list(cls, value: Any, 
                     allowed_values: Optional[List[str]] = None,
                     min_items: int = 0,
                     max_items: Optional[int] = None) -> List[str]:
        """Validate list input"""
        if isinstance(value, str):
            # Try to parse comma-separated
            items = [item.strip() for item in value.split(',') if item.strip()]
        elif isinstance(value, list):
            items = [str(item).strip() for item in value]
        else:
            raise ValidationError("Value must be list or comma-separated string")
        
        # Check counts
        if len(items) < min_items:
            raise ValidationError(f"Too few items (min: {min_items})")
        
        if max_items and len(items) > max_items:
            raise ValidationError(f"Too many items (max: {max_items})")
        
        # Check allowed values
        if allowed_values:
            for item in items:
                if item not in allowed_values:
                    raise ValidationError(f"Value '{item}' not allowed")
        
        return items

class MetaAnalysisValidator:
    """
    Specialized validators for meta-analysis specific inputs
    """
    
    @staticmethod
    def validate_study_data(data: Dict[str, Any], effect_measure: str) -> Dict[str, Any]:
        """Validate study data structure for meta-analysis"""
        validator = InputValidator()
        
        # Validate effect measure
        effect_measure = validator.validate_enum(effect_measure, 'effect_measure')
        
        # Define required fields per effect measure
        required_fields = {
            'OR': ['study', 'event1', 'n1', 'event2', 'n2'],
            'RR': ['study', 'event1', 'n1', 'event2', 'n2'],
            'MD': ['study', 'mean1', 'sd1', 'n1', 'mean2', 'sd2', 'n2'],
            'SMD': ['study', 'mean1', 'sd1', 'n1', 'mean2', 'sd2', 'n2'],
            'HR': ['study', 'hr', 'se_hr'],
            'PROP': ['study', 'events', 'n'],
            'MEAN': ['study', 'n', 'mean', 'sd'],
        }
        
        if effect_measure not in required_fields:
            raise ValidationError(f"Unknown effect measure: {effect_measure}")
        
        # Check required fields exist
        for field in required_fields[effect_measure]:
            if field not in data:
                raise ValidationError(f"Missing required field: {field}")
        
        # Validate numeric fields
        numeric_fields = ['event1', 'n1', 'event2', 'n2', 'mean1', 'sd1', 
                         'mean2', 'sd2', 'events', 'n', 'mean', 'sd', 'hr', 'se_hr']
        
        for field in numeric_fields:
            if field in data:
                data[field] = validator.validate_number(
                    data[field],
                    min_value=0,
                    allow_negative=field.startswith('mean')
                )
        
        return data
    
    @staticmethod
    def validate_confidence_level(value: Any) -> float:
        """Validate confidence level (0.5 to 0.99)"""
        validator = InputValidator()
        level = validator.validate_number(
            value,
            min_value=0.5,
            max_value=0.99,
            allow_decimal=True
        )
        return float(level)

# Convenience function for sanitizing R inputs
def sanitize_for_r(value: str) -> str:
    """
    Sanitize string for safe R execution.
    Removes characters that could cause code injection in R.
    """
    # Remove R-specific dangerous characters
    dangerous_chars = ['`', '$', '@', '!', '#', '%', '^', '&', '*', 
                      '(', ')', '[', ']', '{', '}', '|', '\\', ';', 
                      ':', '"', "'", '<', '>', '?', '\n', '\r', '\t']
    
    sanitized = value
    for char in dangerous_chars:
        sanitized = sanitized.replace(char, '')
    
    # Limit length
    if len(sanitized) > 1000:
        sanitized = sanitized[:1000]
    
    return sanitized.strip()

# Export main components
__all__ = [
    'InputValidator',
    'MetaAnalysisValidator',
    'ValidationError',
    'sanitize_for_r'
]