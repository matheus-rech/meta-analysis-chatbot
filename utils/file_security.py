"""
Secure file upload validation and sandboxing system.
Provides comprehensive file validation, content scanning, and sandboxed processing.
"""

import os
import shutil
import tempfile
import hashlib
import mimetypes
import magic
from pathlib import Path
from typing import Optional, Dict, Any, List, Tuple
import zipfile
import tarfile
import logging
from datetime import datetime
import json

from .validators import InputValidator, ValidationError

logger = logging.getLogger(__name__)

class FileSecurityError(Exception):
    """Custom exception for file security violations"""
    pass

class SecureFileHandler:
    """
    Handles file uploads with comprehensive security checks.
    Features:
    - File type validation (extension and content-based)
    - Size limits enforcement
    - Malware pattern detection
    - Sandboxed processing
    - Quarantine for suspicious files
    """
    
    # Default configuration
    DEFAULT_MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB
    DEFAULT_MAX_FILES = 100  # Max files per session
    
    # Allowed file extensions and their MIME types
    ALLOWED_EXTENSIONS = {
        '.csv': ['text/csv', 'text/plain', 'application/csv'],
        '.xlsx': ['application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'],
        '.xls': ['application/vnd.ms-excel'],
        '.txt': ['text/plain'],
        '.json': ['application/json', 'text/json'],
        '.rds': ['application/octet-stream'],  # R data files
        '.pdf': ['application/pdf'],
        '.png': ['image/png'],
        '.jpg': ['image/jpeg'],
        '.jpeg': ['image/jpeg'],
    }
    
    # Dangerous patterns in file content
    DANGEROUS_PATTERNS = [
        b'<script',  # JavaScript
        b'<?php',    # PHP
        b'#!/bin/',  # Shell scripts
        b'\x4d\x5a', # PE executables (MZ header)
        b'\x7fELF',  # ELF executables
        b'%!PS',     # PostScript (can be dangerous)
    ]
    
    # CSV formula injection patterns
    CSV_INJECTION_PATTERNS = [
        r'^[\s]*=',
        r'^[\s]*\+',
        r'^[\s]*-',
        r'^[\s]*@',
        r'^[\s]*\|',
    ]
    
    def __init__(self, 
                 upload_dir: Optional[str] = None,
                 quarantine_dir: Optional[str] = None,
                 max_file_size: int = DEFAULT_MAX_FILE_SIZE,
                 allowed_extensions: Optional[Dict[str, List[str]]] = None):
        """
        Initialize secure file handler.
        
        Args:
            upload_dir: Directory for validated uploads
            quarantine_dir: Directory for suspicious files
            max_file_size: Maximum allowed file size in bytes
            allowed_extensions: Custom allowed extensions and MIME types
        """
        self.upload_dir = Path(upload_dir or tempfile.mkdtemp(prefix='uploads_'))
        self.quarantine_dir = Path(quarantine_dir or tempfile.mkdtemp(prefix='quarantine_'))
        self.sandbox_dir = Path(tempfile.mkdtemp(prefix='sandbox_'))
        
        # Create directories
        for dir_path in [self.upload_dir, self.quarantine_dir, self.sandbox_dir]:
            dir_path.mkdir(exist_ok=True, parents=True)
            # Set restrictive permissions (owner only)
            os.chmod(dir_path, 0o700)
        
        self.max_file_size = max_file_size
        self.allowed_extensions = allowed_extensions or self.ALLOWED_EXTENSIONS
        self.validator = InputValidator()
        
        # Initialize magic for content-type detection
        try:
            self.magic = magic.Magic(mime=True)
        except Exception as e:
            logger.warning(f"python-magic not available: {e}")
            self.magic = None
    
    def validate_filename(self, filename: str) -> str:
        """
        Validate and sanitize filename.
        
        Args:
            filename: Original filename
            
        Returns:
            Sanitized filename
            
        Raises:
            FileSecurityError: If filename is invalid
        """
        # Basic validation
        if not filename:
            raise FileSecurityError("Empty filename")
        
        # Remove path components
        filename = os.path.basename(filename)
        
        # Check for directory traversal
        if '..' in filename or '/' in filename or '\\' in filename:
            raise FileSecurityError("Invalid filename: contains path separators")
        
        # Validate with InputValidator
        try:
            safe_filename = self.validator.validate_filename(
                filename,
                allowed_extensions=list(self.allowed_extensions.keys())
            )
        except ValidationError as e:
            raise FileSecurityError(f"Invalid filename: {e}")
        
        # Additional sanitization
        # Replace spaces and special chars
        safe_filename = safe_filename.replace(' ', '_')
        safe_filename = ''.join(c for c in safe_filename 
                               if c.isalnum() or c in '._-')
        
        # Ensure it has an extension
        if '.' not in safe_filename:
            raise FileSecurityError("Filename must have an extension")
        
        return safe_filename
    
    def check_file_size(self, file_path: Path) -> int:
        """
        Check if file size is within limits.
        
        Args:
            file_path: Path to file
            
        Returns:
            File size in bytes
            
        Raises:
            FileSecurityError: If file is too large
        """
        file_size = file_path.stat().st_size
        
        if file_size > self.max_file_size:
            raise FileSecurityError(
                f"File too large: {file_size} bytes (max: {self.max_file_size})"
            )
        
        if file_size == 0:
            raise FileSecurityError("Empty file not allowed")
        
        return file_size
    
    def detect_content_type(self, file_path: Path) -> str:
        """
        Detect file content type using multiple methods.
        
        Args:
            file_path: Path to file
            
        Returns:
            Detected MIME type
        """
        # Method 1: Use python-magic if available
        if self.magic:
            try:
                return self.magic.from_file(str(file_path))
            except Exception as e:
                logger.warning(f"Magic detection failed: {e}")
        
        # Method 2: Use mimetypes
        mime_type, _ = mimetypes.guess_type(str(file_path))
        if mime_type:
            return mime_type
        
        # Method 3: Check file headers
        with open(file_path, 'rb') as f:
            header = f.read(512)
            
        if header.startswith(b'%PDF'):
            return 'application/pdf'
        elif header.startswith(b'\x89PNG'):
            return 'image/png'
        elif header.startswith(b'\xff\xd8\xff'):
            return 'image/jpeg'
        elif header.startswith(b'PK\x03\x04'):
            # Could be zip or Office format
            if file_path.suffix == '.xlsx':
                return 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
            return 'application/zip'
        
        return 'application/octet-stream'
    
    def validate_content_type(self, file_path: Path, expected_ext: str) -> None:
        """
        Validate that file content matches expected type.
        
        Args:
            file_path: Path to file
            expected_ext: Expected file extension
            
        Raises:
            FileSecurityError: If content type doesn't match
        """
        if expected_ext not in self.allowed_extensions:
            raise FileSecurityError(f"Extension not allowed: {expected_ext}")
        
        detected_type = self.detect_content_type(file_path)
        allowed_types = self.allowed_extensions[expected_ext]
        
        if detected_type not in allowed_types:
            logger.warning(
                f"Content type mismatch: detected {detected_type}, "
                f"expected one of {allowed_types}"
            )
            # For some formats, this might be too strict
            # Log but don't always reject
            if expected_ext not in ['.txt', '.csv', '.rds']:
                raise FileSecurityError(
                    f"File content ({detected_type}) doesn't match extension {expected_ext}"
                )
    
    def scan_for_malware_patterns(self, file_path: Path) -> List[str]:
        """
        Scan file for dangerous patterns.
        
        Args:
            file_path: Path to file
            
        Returns:
            List of detected issues
        """
        issues = []
        
        with open(file_path, 'rb') as f:
            content = f.read(1024 * 1024)  # Read first 1MB
        
        # Check for dangerous binary patterns
        for pattern in self.DANGEROUS_PATTERNS:
            if pattern in content:
                issues.append(f"Dangerous pattern detected: {pattern}")
        
        # For text files, check for script injections
        if file_path.suffix in ['.csv', '.txt', '.json']:
            try:
                text_content = content.decode('utf-8', errors='ignore')
                lines = text_content.split('\n')[:1000]  # Check first 1000 lines
                
                # Check for CSV injection
                if file_path.suffix == '.csv':
                    import re
                    for i, line in enumerate(lines):
                        for pattern in self.CSV_INJECTION_PATTERNS:
                            if re.match(pattern, line.strip()):
                                issues.append(f"CSV injection pattern on line {i+1}")
                                break
                
                # Check for script tags in any text file
                if '<script' in text_content.lower():
                    issues.append("Script tag detected in text file")
                    
            except Exception as e:
                logger.warning(f"Text scanning error: {e}")
        
        return issues
    
    def calculate_file_hash(self, file_path: Path) -> Dict[str, str]:
        """
        Calculate multiple hashes for file integrity.
        
        Args:
            file_path: Path to file
            
        Returns:
            Dictionary of hash algorithms and their values
        """
        hashes = {
            'md5': hashlib.md5(),
            'sha1': hashlib.sha1(),
            'sha256': hashlib.sha256()
        }
        
        with open(file_path, 'rb') as f:
            while chunk := f.read(8192):
                for hash_obj in hashes.values():
                    hash_obj.update(chunk)
        
        return {name: hash_obj.hexdigest() for name, hash_obj in hashes.items()}
    
    def sandbox_process_file(self, file_path: Path, filename: str) -> Tuple[Path, Dict[str, Any]]:
        """
        Process file in sandboxed environment.
        
        Args:
            file_path: Path to uploaded file
            filename: Original filename
            
        Returns:
            Tuple of (sandboxed file path, metadata)
        """
        # Create unique sandbox subdirectory
        sandbox_subdir = self.sandbox_dir / f"{datetime.now().timestamp()}_{os.getpid()}"
        sandbox_subdir.mkdir(exist_ok=True)
        
        # Copy file to sandbox
        sandbox_file = sandbox_subdir / filename
        shutil.copy2(file_path, sandbox_file)
        
        # Set restrictive permissions
        os.chmod(sandbox_file, 0o600)
        
        # Collect metadata
        metadata = {
            'original_name': filename,
            'size': self.check_file_size(sandbox_file),
            'content_type': self.detect_content_type(sandbox_file),
            'hashes': self.calculate_file_hash(sandbox_file),
            'upload_time': datetime.now().isoformat(),
        }
        
        return sandbox_file, metadata
    
    def validate_and_store_file(self, 
                               file_path: str,
                               original_filename: str,
                               session_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Main method to validate and securely store an uploaded file.
        
        Args:
            file_path: Path to uploaded file (temporary location)
            original_filename: Original filename from upload
            session_id: Optional session ID for organization
            
        Returns:
            Dictionary with file metadata and storage location
            
        Raises:
            FileSecurityError: If validation fails
        """
        file_path = Path(file_path)
        
        # Step 1: Validate filename
        safe_filename = self.validate_filename(original_filename)
        
        # Step 2: Check file size
        file_size = self.check_file_size(file_path)
        
        # Step 3: Sandbox processing
        sandbox_file, metadata = self.sandbox_process_file(file_path, safe_filename)
        
        try:
            # Step 4: Validate content type
            ext = Path(safe_filename).suffix.lower()
            self.validate_content_type(sandbox_file, ext)
            
            # Step 5: Scan for malware patterns
            issues = self.scan_for_malware_patterns(sandbox_file)
            
            if issues:
                # Move to quarantine
                quarantine_path = self.quarantine_dir / f"SUSPICIOUS_{safe_filename}"
                shutil.move(str(sandbox_file), str(quarantine_path))
                
                metadata['status'] = 'quarantined'
                metadata['issues'] = issues
                metadata['quarantine_path'] = str(quarantine_path)
                
                logger.warning(f"File quarantined: {safe_filename} - {issues}")
                raise FileSecurityError(f"File failed security scan: {', '.join(issues)}")
            
            # Step 6: Move to final storage
            if session_id:
                session_dir = self.upload_dir / session_id
                session_dir.mkdir(exist_ok=True)
                final_path = session_dir / safe_filename
            else:
                final_path = self.upload_dir / safe_filename
            
            # Ensure unique filename
            if final_path.exists():
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                name_parts = safe_filename.rsplit('.', 1)
                safe_filename = f"{name_parts[0]}_{timestamp}.{name_parts[1]}"
                final_path = final_path.parent / safe_filename
            
            shutil.move(str(sandbox_file), str(final_path))
            os.chmod(final_path, 0o600)
            
            # Update metadata
            metadata['status'] = 'validated'
            metadata['storage_path'] = str(final_path)
            metadata['filename'] = safe_filename
            
            logger.info(f"File validated and stored: {safe_filename}")
            
            return metadata
            
        finally:
            # Cleanup sandbox
            if sandbox_file.parent.exists():
                shutil.rmtree(sandbox_file.parent, ignore_errors=True)
    
    def cleanup_old_files(self, max_age_hours: int = 24) -> int:
        """
        Clean up old files from upload and quarantine directories.
        
        Args:
            max_age_hours: Maximum age of files to keep
            
        Returns:
            Number of files cleaned up
        """
        from datetime import timedelta
        cutoff_time = datetime.now() - timedelta(hours=max_age_hours)
        cleaned = 0
        
        for directory in [self.upload_dir, self.quarantine_dir, self.sandbox_dir]:
            for file_path in directory.rglob('*'):
                if file_path.is_file():
                    file_time = datetime.fromtimestamp(file_path.stat().st_mtime)
                    if file_time < cutoff_time:
                        try:
                            file_path.unlink()
                            cleaned += 1
                        except Exception as e:
                            logger.warning(f"Failed to clean up {file_path}: {e}")
        
        logger.info(f"Cleaned up {cleaned} old files")
        return cleaned

# Global instance for convenience
secure_file_handler = SecureFileHandler()

# Export main components
__all__ = [
    'SecureFileHandler',
    'FileSecurityError',
    'secure_file_handler'
]