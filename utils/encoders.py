"""
Context-aware output encoding system for different output contexts.
Prevents XSS, injection attacks, and ensures safe output rendering.
"""

import html
import json
import re
import urllib.parse
from typing import Any, Dict, List, Optional, Union
import base64
import csv
import io
import logging

logger = logging.getLogger(__name__)

class EncodingError(Exception):
    """Custom exception for encoding errors"""
    pass

class OutputEncoder:
    """
    Provides context-aware encoding for different output formats.
    Prevents XSS, SQL injection, and other output-based vulnerabilities.
    """
    
    @staticmethod
    def encode_html(value: Any, 
                   attribute: bool = False,
                   allow_safe_tags: bool = False) -> str:
        """
        Encode value for safe HTML output.
        
        Args:
            value: Value to encode
            attribute: Whether encoding for HTML attribute (more strict)
            allow_safe_tags: Whether to allow certain safe tags (b, i, em, strong)
            
        Returns:
            HTML-encoded string
        """
        if value is None:
            return ''
        
        str_value = str(value)
        
        # Basic HTML encoding
        encoded = html.escape(str_value, quote=True)
        
        # Additional encoding for attributes
        if attribute:
            # Encode additional characters that can break out of attributes
            encoded = encoded.replace("'", '&#x27;')
            encoded = encoded.replace('"', '&quot;')
            encoded = encoded.replace('/', '&#x2F;')
            encoded = encoded.replace('=', '&#x3D;')
            encoded = encoded.replace('`', '&#x60;')
            
            # Remove newlines and tabs in attributes
            encoded = encoded.replace('\n', ' ').replace('\r', ' ').replace('\t', ' ')
        
        # Optionally allow some safe tags
        if allow_safe_tags and not attribute:
            safe_tags = ['b', 'i', 'em', 'strong', 'u']
            for tag in safe_tags:
                # Only allow properly closed tags
                encoded = encoded.replace(f'&lt;{tag}&gt;', f'<{tag}>')
                encoded = encoded.replace(f'&lt;/{tag}&gt;', f'</{tag}>')
        
        return encoded
    
    @staticmethod
    def encode_javascript(value: Any) -> str:
        """
        Encode value for safe JavaScript output.
        
        Args:
            value: Value to encode
            
        Returns:
            JavaScript-encoded string
        """
        if value is None:
            return 'null'
        
        # Use JSON encoding as base (handles most cases)
        try:
            encoded = json.dumps(value)
        except (TypeError, ValueError):
            encoded = json.dumps(str(value))
        
        # Additional encoding for script context
        # Prevent script tag breakout
        encoded = encoded.replace('</', '<\\/')
        encoded = encoded.replace('<!--', '<\\!--')
        encoded = encoded.replace('-->', '--\\>')
        
        # Encode dangerous Unicode characters
        encoded = encoded.replace('\u2028', '\\u2028')  # Line separator
        encoded = encoded.replace('\u2029', '\\u2029')  # Paragraph separator
        
        return encoded
    
    @staticmethod
    def encode_json(value: Any, 
                   ensure_ascii: bool = True,
                   escape_forward_slashes: bool = True) -> str:
        """
        Encode value as safe JSON.
        
        Args:
            value: Value to encode
            ensure_ascii: Whether to escape non-ASCII characters
            escape_forward_slashes: Whether to escape forward slashes
            
        Returns:
            JSON-encoded string
        """
        try:
            encoded = json.dumps(value, ensure_ascii=ensure_ascii, separators=(',', ':'))
        except (TypeError, ValueError) as e:
            raise EncodingError(f"JSON encoding failed: {e}")
        
        # Escape forward slashes to prevent </script> injection
        if escape_forward_slashes:
            encoded = encoded.replace('/', '\\/')
        
        return encoded
    
    @staticmethod
    def encode_csv(data: List[List[Any]], 
                  prevent_injection: bool = True) -> str:
        """
        Encode data as CSV with injection prevention.
        
        Args:
            data: List of rows (each row is a list)
            prevent_injection: Whether to prevent formula injection
            
        Returns:
            CSV-encoded string
        """
        output = io.StringIO()
        writer = csv.writer(output, quoting=csv.QUOTE_MINIMAL)
        
        for row in data:
            if prevent_injection:
                # Sanitize cells that could contain formulas
                sanitized_row = []
                for cell in row:
                    cell_str = str(cell) if cell is not None else ''
                    
                    # Prevent formula injection
                    if cell_str and cell_str[0] in ['=', '+', '-', '@', '|']:
                        # Prefix with single quote to prevent formula execution
                        cell_str = "'" + cell_str
                    
                    sanitized_row.append(cell_str)
                
                writer.writerow(sanitized_row)
            else:
                writer.writerow(row)
        
        return output.getvalue()
    
    @staticmethod
    def encode_url_parameter(value: Any) -> str:
        """
        Encode value for safe URL parameter use.
        
        Args:
            value: Value to encode
            
        Returns:
            URL-encoded string
        """
        if value is None:
            return ''
        
        return urllib.parse.quote(str(value), safe='')
    
    @staticmethod
    def encode_shell_argument(value: Any) -> str:
        """
        Encode value for safe shell argument use.
        Note: Prefer using subprocess with list arguments instead.
        
        Args:
            value: Value to encode
            
        Returns:
            Shell-escaped string
        """
        import shlex
        
        if value is None:
            return ''
        
        return shlex.quote(str(value))
    
    @staticmethod
    def encode_sql_identifier(identifier: str) -> str:
        """
        Encode SQL identifier (table/column name).
        Note: Use parameterized queries for values!
        
        Args:
            identifier: SQL identifier
            
        Returns:
            Quoted identifier
        """
        # Remove any existing quotes
        identifier = identifier.replace('"', '').replace('`', '').replace("'", '')
        
        # Only allow alphanumeric and underscore
        if not re.match(r'^[a-zA-Z_][a-zA-Z0-9_]*$', identifier):
            raise EncodingError(f"Invalid SQL identifier: {identifier}")
        
        # Use double quotes (ANSI SQL standard)
        return f'"{identifier}"'
    
    @staticmethod
    def encode_base64(data: bytes, urlsafe: bool = False) -> str:
        """
        Encode binary data as base64.
        
        Args:
            data: Binary data to encode
            urlsafe: Whether to use URL-safe encoding
            
        Returns:
            Base64-encoded string
        """
        if urlsafe:
            return base64.urlsafe_b64encode(data).decode('ascii')
        else:
            return base64.b64encode(data).decode('ascii')
    
    @staticmethod
    def encode_filename(filename: str, 
                       max_length: int = 255,
                       allow_unicode: bool = False) -> str:
        """
        Encode filename for safe filesystem use.
        
        Args:
            filename: Original filename
            max_length: Maximum length
            allow_unicode: Whether to allow Unicode characters
            
        Returns:
            Safe filename
        """
        # Remove path separators
        filename = filename.replace('/', '_').replace('\\', '_')
        
        # Remove null bytes
        filename = filename.replace('\x00', '')
        
        # Replace problematic characters
        if not allow_unicode:
            # Keep only ASCII alphanumeric, dots, hyphens, underscores
            filename = re.sub(r'[^a-zA-Z0-9._-]', '_', filename)
        else:
            # Remove control characters but keep Unicode
            filename = ''.join(c if c.isprintable() or c == ' ' else '_' for c in filename)
        
        # Remove leading/trailing dots and spaces
        filename = filename.strip('. ')
        
        # Ensure not empty
        if not filename:
            filename = 'unnamed'
        
        # Truncate if too long (preserve extension)
        if len(filename) > max_length:
            name, ext = os.path.splitext(filename)
            max_name_length = max_length - len(ext)
            filename = name[:max_name_length] + ext
        
        return filename
    
    @staticmethod
    def sanitize_markdown(text: str, 
                         allow_html: bool = False,
                         allow_images: bool = True,
                         allow_links: bool = True) -> str:
        """
        Sanitize Markdown content for safe rendering.
        
        Args:
            text: Markdown text
            allow_html: Whether to allow inline HTML
            allow_images: Whether to allow image syntax
            allow_links: Whether to allow link syntax
            
        Returns:
            Sanitized Markdown
        """
        if not allow_html:
            # Escape HTML tags
            text = re.sub(r'<([^>]+)>', r'&lt;\1&gt;', text)
        
        if not allow_images:
            # Remove image syntax ![alt](url)
            text = re.sub(r'!\[([^\]]*)\]\([^\)]+\)', r'\1', text)
        
        if not allow_links:
            # Remove link syntax [text](url)
            text = re.sub(r'\[([^\]]+)\]\([^\)]+\)', r'\1', text)
        
        # Prevent script execution in code blocks
        text = text.replace('```javascript', '```text')
        text = text.replace('```js', '```text')
        text = text.replace('```html', '```text')
        
        return text

class ResponseEncoder:
    """
    Encodes complete responses based on content type.
    """
    
    def __init__(self):
        self.encoder = OutputEncoder()
    
    def encode_html_response(self, data: Dict[str, Any]) -> str:
        """
        Encode data for HTML response.
        
        Args:
            data: Response data
            
        Returns:
            HTML-safe response
        """
        encoded_data = {}
        
        for key, value in data.items():
            if isinstance(value, dict):
                encoded_data[key] = self.encode_html_response(value)
            elif isinstance(value, list):
                encoded_data[key] = [
                    self.encode_html_response(item) if isinstance(item, dict) 
                    else self.encoder.encode_html(item)
                    for item in value
                ]
            else:
                encoded_data[key] = self.encoder.encode_html(value)
        
        return encoded_data
    
    def encode_json_response(self, data: Any) -> str:
        """
        Encode data for JSON response.
        
        Args:
            data: Response data
            
        Returns:
            JSON string
        """
        return self.encoder.encode_json(data)
    
    def encode_gradio_response(self, data: Any) -> Any:
        """
        Encode data for Gradio interface output.
        
        Args:
            data: Response data
            
        Returns:
            Safely encoded data for Gradio
        """
        if isinstance(data, str):
            # Gradio handles basic HTML escaping, but we add extra safety
            return self.encoder.encode_html(data, allow_safe_tags=True)
        elif isinstance(data, dict):
            # For JSON display in Gradio
            return self.encoder.encode_json(data, ensure_ascii=False)
        elif isinstance(data, list):
            # For table display
            return [[self.encoder.encode_html(cell) for cell in row] for row in data]
        else:
            return data
    
    def encode_file_download(self, 
                           content: Union[str, bytes],
                           filename: str,
                           content_type: str) -> Dict[str, Any]:
        """
        Prepare safe file download response.
        
        Args:
            content: File content
            filename: Suggested filename
            content_type: MIME type
            
        Returns:
            Download response data
        """
        safe_filename = self.encoder.encode_filename(filename)
        
        # Set security headers
        headers = {
            'Content-Type': content_type,
            'Content-Disposition': f'attachment; filename="{safe_filename}"',
            'X-Content-Type-Options': 'nosniff',
            'Cache-Control': 'no-cache, no-store, must-revalidate',
        }
        
        return {
            'content': content,
            'filename': safe_filename,
            'headers': headers
        }

# Global instances for convenience
output_encoder = OutputEncoder()
response_encoder = ResponseEncoder()

# Export main components
__all__ = [
    'OutputEncoder',
    'ResponseEncoder',
    'EncodingError',
    'output_encoder',
    'response_encoder'
]