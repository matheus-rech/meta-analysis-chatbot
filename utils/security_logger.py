"""
Lightweight security logging and audit trail system.
Optimized for performance while maintaining comprehensive security event tracking.
"""

import os
import json
import logging
import hashlib
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional, Union, List
from functools import wraps
import threading
import queue
import atexit
from collections import deque

# Configure base logger
logger = logging.getLogger(__name__)

class SecurityEvent:
    """Represents a security event"""
    
    # Event severity levels
    INFO = 'INFO'
    WARNING = 'WARNING'
    ERROR = 'ERROR'
    CRITICAL = 'CRITICAL'
    
    # Event categories
    AUTHENTICATION = 'AUTHENTICATION'
    AUTHORIZATION = 'AUTHORIZATION'
    FILE_UPLOAD = 'FILE_UPLOAD'
    SUBPROCESS = 'SUBPROCESS'
    INPUT_VALIDATION = 'INPUT_VALIDATION'
    DATA_ACCESS = 'DATA_ACCESS'
    CONFIGURATION = 'CONFIGURATION'
    
    def __init__(self,
                 event_type: str,
                 category: str,
                 severity: str,
                 details: Dict[str, Any],
                 user_id: Optional[str] = None,
                 session_id: Optional[str] = None,
                 ip_address: Optional[str] = None):
        self.event_id = self._generate_event_id()
        self.timestamp = datetime.utcnow()
        self.event_type = event_type
        self.category = category
        self.severity = severity
        self.details = details
        self.user_id = user_id
        self.session_id = session_id
        self.ip_address = ip_address
    
    def _generate_event_id(self) -> str:
        """Generate unique event ID"""
        timestamp = datetime.utcnow().isoformat()
        random_data = os.urandom(8).hex()
        return hashlib.sha256(f"{timestamp}{random_data}".encode()).hexdigest()[:16]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert event to dictionary"""
        return {
            'event_id': self.event_id,
            'timestamp': self.timestamp.isoformat(),
            'event_type': self.event_type,
            'category': self.category,
            'severity': self.severity,
            'user_id': self.user_id,
            'session_id': self.session_id,
            'ip_address': self.ip_address,
            'details': self.details
        }
    
    def to_json_line(self) -> str:
        """Convert to JSON line for log file"""
        return json.dumps(self.to_dict(), separators=(',', ':')) + '\n'


class SecurityLogger:
    """
    Lightweight security logger optimized for performance.
    Uses async write queue to minimize I/O blocking.
    """
    
    def __init__(self,
                 log_dir: Optional[str] = None,
                 max_queue_size: int = 10000,
                 batch_size: int = 100,
                 flush_interval: float = 1.0):
        """
        Initialize security logger.
        
        Args:
            log_dir: Directory for security logs
            max_queue_size: Maximum events in queue before blocking
            batch_size: Number of events to write in batch
            flush_interval: Seconds between automatic flushes
        """
        self.log_dir = Path(log_dir or os.getenv('SECURITY_LOG_DIR', './logs/security'))
        self.log_dir.mkdir(exist_ok=True, parents=True)
        
        # Set restrictive permissions on log directory
        os.chmod(self.log_dir, 0o700)
        
        self.max_queue_size = max_queue_size
        self.batch_size = batch_size
        self.flush_interval = flush_interval
        
        # Event queue for async writing
        self.event_queue = queue.Queue(maxsize=max_queue_size)
        self.recent_events = deque(maxlen=1000)  # Keep recent events in memory
        
        # Start background writer thread
        self.writer_thread = threading.Thread(target=self._writer_loop, daemon=True)
        self.writer_thread.start()
        
        # Register cleanup on exit
        atexit.register(self.shutdown)
        
        # Log initialization
        self.log_event(
            event_type='LOGGER_STARTED',
            category=SecurityEvent.CONFIGURATION,
            severity=SecurityEvent.INFO,
            details={'log_dir': str(self.log_dir)}
        )
    
    def _get_log_file_path(self) -> Path:
        """Get current log file path (rotated daily)"""
        date_str = datetime.utcnow().strftime('%Y-%m-%d')
        return self.log_dir / f'security_{date_str}.jsonl'
    
    def _writer_loop(self):
        """Background thread that writes events to disk"""
        buffer = []
        last_flush = datetime.utcnow()
        
        while True:
            try:
                # Try to get event with timeout
                timeout = self.flush_interval
                event = self.event_queue.get(timeout=timeout)
                
                if event is None:  # Shutdown signal
                    break
                
                buffer.append(event)
                
                # Write batch if buffer is full or timeout reached
                now = datetime.utcnow()
                if (len(buffer) >= self.batch_size or 
                    (now - last_flush).total_seconds() >= self.flush_interval):
                    self._write_batch(buffer)
                    buffer.clear()
                    last_flush = now
                    
            except queue.Empty:
                # Timeout - flush any pending events
                if buffer:
                    self._write_batch(buffer)
                    buffer.clear()
                    last_flush = datetime.utcnow()
            except Exception as e:
                logger.error(f"Security logger writer error: {e}")
    
    def _write_batch(self, events: List[SecurityEvent]):
        """Write batch of events to log file"""
        if not events:
            return
        
        log_file = self._get_log_file_path()
        
        try:
            # Append to log file
            with open(log_file, 'a', encoding='utf-8') as f:
                for event in events:
                    f.write(event.to_json_line())
            
            # Set restrictive permissions
            os.chmod(log_file, 0o600)
            
        except Exception as e:
            logger.error(f"Failed to write security log batch: {e}")
    
    def log_event(self,
                  event_type: str,
                  category: str,
                  severity: str,
                  details: Dict[str, Any],
                  user_id: Optional[str] = None,
                  session_id: Optional[str] = None,
                  ip_address: Optional[str] = None) -> str:
        """
        Log a security event.
        
        Returns:
            Event ID
        """
        event = SecurityEvent(
            event_type=event_type,
            category=category,
            severity=severity,
            details=details,
            user_id=user_id,
            session_id=session_id,
            ip_address=ip_address
        )
        
        # Add to recent events
        self.recent_events.append(event)
        
        # Add to write queue (non-blocking if queue is full)
        try:
            self.event_queue.put_nowait(event)
        except queue.Full:
            logger.warning("Security event queue full, dropping event")
        
        # Also log to standard logger for immediate visibility
        log_level = getattr(logging, severity, logging.INFO)
        logger.log(log_level, f"Security Event: {event_type} - {details}")
        
        return event.event_id
    
    # Convenience methods for common security events
    
    def log_authentication_attempt(self,
                                  success: bool,
                                  username: Optional[str] = None,
                                  method: str = 'unknown',
                                  ip_address: Optional[str] = None,
                                  details: Optional[Dict] = None) -> str:
        """Log authentication attempt"""
        event_details = {
            'success': success,
            'username': username,
            'method': method,
            **(details or {})
        }
        
        return self.log_event(
            event_type='AUTH_ATTEMPT',
            category=SecurityEvent.AUTHENTICATION,
            severity=SecurityEvent.INFO if success else SecurityEvent.WARNING,
            details=event_details,
            ip_address=ip_address
        )
    
    def log_file_upload(self,
                       filename: str,
                       size: int,
                       file_type: str,
                       validation_result: str,
                       session_id: Optional[str] = None,
                       details: Optional[Dict] = None) -> str:
        """Log file upload event"""
        event_details = {
            'filename': filename,
            'size': size,
            'file_type': file_type,
            'validation_result': validation_result,
            **(details or {})
        }
        
        severity = (SecurityEvent.INFO if validation_result == 'success' 
                   else SecurityEvent.WARNING)
        
        return self.log_event(
            event_type='FILE_UPLOAD',
            category=SecurityEvent.FILE_UPLOAD,
            severity=severity,
            details=event_details,
            session_id=session_id
        )
    
    def log_subprocess_execution(self,
                               command: List[str],
                               success: bool,
                               return_code: Optional[int] = None,
                               session_id: Optional[str] = None,
                               details: Optional[Dict] = None) -> str:
        """Log subprocess execution"""
        event_details = {
            'command': command[0] if command else 'unknown',
            'args_count': len(command) - 1 if command else 0,
            'success': success,
            'return_code': return_code,
            **(details or {})
        }
        
        return self.log_event(
            event_type='SUBPROCESS_EXEC',
            category=SecurityEvent.SUBPROCESS,
            severity=SecurityEvent.INFO if success else SecurityEvent.ERROR,
            details=event_details,
            session_id=session_id
        )
    
    def log_input_validation_failure(self,
                                   field: str,
                                   reason: str,
                                   value_type: str,
                                   session_id: Optional[str] = None,
                                   details: Optional[Dict] = None) -> str:
        """Log input validation failure"""
        event_details = {
            'field': field,
            'reason': reason,
            'value_type': value_type,
            **(details or {})
        }
        
        return self.log_event(
            event_type='VALIDATION_FAILED',
            category=SecurityEvent.INPUT_VALIDATION,
            severity=SecurityEvent.WARNING,
            details=event_details,
            session_id=session_id
        )
    
    def get_recent_events(self,
                         category: Optional[str] = None,
                         severity: Optional[str] = None,
                         limit: int = 100) -> List[Dict[str, Any]]:
        """
        Get recent events from memory.
        
        Args:
            category: Filter by category
            severity: Filter by severity
            limit: Maximum events to return
            
        Returns:
            List of event dictionaries
        """
        events = list(self.recent_events)
        
        # Apply filters
        if category:
            events = [e for e in events if e.category == category]
        if severity:
            events = [e for e in events if e.severity == severity]
        
        # Sort by timestamp (newest first) and limit
        events.sort(key=lambda e: e.timestamp, reverse=True)
        
        return [e.to_dict() for e in events[:limit]]
    
    def search_logs(self,
                   start_time: datetime,
                   end_time: datetime,
                   filters: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """
        Search logs within time range.
        Note: This reads from disk, use sparingly.
        
        Args:
            start_time: Start of time range
            end_time: End of time range
            filters: Additional filters to apply
            
        Returns:
            List of matching events
        """
        results = []
        
        # Determine which log files to search
        current_date = start_time.date()
        end_date = end_time.date()
        
        while current_date <= end_date:
            log_file = self.log_dir / f'security_{current_date}.jsonl'
            
            if log_file.exists():
                try:
                    with open(log_file, 'r', encoding='utf-8') as f:
                        for line in f:
                            try:
                                event = json.loads(line.strip())
                                event_time = datetime.fromisoformat(event['timestamp'])
                                
                                # Check time range
                                if start_time <= event_time <= end_time:
                                    # Apply filters
                                    if filters:
                                        match = all(
                                            event.get(k) == v 
                                            for k, v in filters.items()
                                        )
                                        if not match:
                                            continue
                                    
                                    results.append(event)
                                    
                            except (json.JSONDecodeError, KeyError, ValueError):
                                continue
                                
                except Exception as e:
                    logger.error(f"Error searching log file {log_file}: {e}")
            
            current_date += timedelta(days=1)
        
        return results
    
    def shutdown(self):
        """Shutdown logger and flush remaining events"""
        # Signal writer thread to stop
        self.event_queue.put(None)
        
        # Wait for writer to finish
        if self.writer_thread.is_alive():
            self.writer_thread.join(timeout=5)


def security_logged(event_type: str,
                   category: str,
                   severity: str = SecurityEvent.INFO):
    """
    Decorator to automatically log function calls.
    
    Args:
        event_type: Type of security event
        category: Event category
        severity: Event severity
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Extract context from kwargs
            session_id = kwargs.get('session_id')
            user_id = kwargs.get('user_id')
            
            # Log function call
            details = {
                'function': func.__name__,
                'args_count': len(args),
                'kwargs_keys': list(kwargs.keys())
            }
            
            event_id = security_logger.log_event(
                event_type=f"{event_type}_START",
                category=category,
                severity=SecurityEvent.INFO,
                details=details,
                session_id=session_id,
                user_id=user_id
            )
            
            try:
                # Execute function
                result = func(*args, **kwargs)
                
                # Log success
                security_logger.log_event(
                    event_type=f"{event_type}_SUCCESS",
                    category=category,
                    severity=SecurityEvent.INFO,
                    details={'parent_event_id': event_id},
                    session_id=session_id,
                    user_id=user_id
                )
                
                return result
                
            except Exception as e:
                # Log failure
                security_logger.log_event(
                    event_type=f"{event_type}_FAILED",
                    category=category,
                    severity=severity,
                    details={
                        'parent_event_id': event_id,
                        'error': str(e),
                        'error_type': type(e).__name__
                    },
                    session_id=session_id,
                    user_id=user_id
                )
                raise
        
        return wrapper
    return decorator


# Global instance
security_logger = SecurityLogger()

# Export main components
__all__ = [
    'SecurityLogger',
    'SecurityEvent',
    'security_logger',
    'security_logged'
]