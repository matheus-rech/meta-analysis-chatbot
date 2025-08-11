# Critical Security Fixes - Code Examples

## 1. Command Injection Fix in server.py

### Current Vulnerable Code:
```python
# server.py line 49
proc = subprocess.Popen(
    [RSCRIPT_BIN, '--vanilla', SCRIPTS_ENTRY, tool_name, args_file, session_dir],
    stdin=subprocess.PIPE,
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE,
    text=True,
    encoding='utf-8',
)
```

### Fixed Code:
```python
import shlex
import os

# Whitelist of allowed tools
ALLOWED_TOOLS = {
    'health_check',
    'initialize_meta_analysis',
    'upload_study_data',
    'perform_meta_analysis',
    'generate_forest_plot',
    'assess_publication_bias',
    'generate_report',
    'get_session_status',
}

def execute_r(tool: str, args: Dict[str, Any], session_path: str = None, timeout: int = DEFAULT_TIMEOUT) -> Dict[str, Any]:
    # Validate tool name
    if tool not in ALLOWED_TOOLS:
        return {'status': 'error', 'message': f'Invalid tool name: {tool}'}
    
    # Validate and sanitize session path
    if session_path:
        session_path = os.path.abspath(session_path)
        # Ensure path is within allowed directory
        allowed_root = os.path.abspath(os.environ.get('SESSIONS_DIR', os.getcwd()))
        if not session_path.startswith(allowed_root):
            return {'status': 'error', 'message': 'Invalid session path'}
    
    session_dir = session_path or os.getcwd()
    
    # ... rest of function with sanitized inputs
    
    # Use shlex.quote for any shell-like operations
    cmd = [
        RSCRIPT_BIN, 
        '--vanilla', 
        SCRIPTS_ENTRY, 
        shlex.quote(tool), 
        shlex.quote(args_file), 
        shlex.quote(session_dir)
    ]
    
    proc = subprocess.Popen(
        cmd,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding='utf-8',
    )
```

## 2. Path Traversal Fix in upload_data.R

### Current Vulnerable Code:
```r
# upload_data.R line 40
raw_data_path <- file.path(input_dir, paste0("raw_data.", args$data_format))
```

### Fixed Code:
```r
# Validate data format
ALLOWED_FORMATS <- c("csv", "excel", "revman")
if (!args$data_format %in% ALLOWED_FORMATS) {
  stop("Invalid data format. Allowed: csv, excel, revman")
}

# Sanitize filename
safe_filename <- gsub("[^a-zA-Z0-9._-]", "", paste0("raw_data.", args$data_format))

# Ensure path stays within input directory
raw_data_path <- file.path(input_dir, safe_filename)
normalized_path <- normalizePath(raw_data_path, mustWork = FALSE)
normalized_input_dir <- normalizePath(input_dir, mustWork = TRUE)

# Check that normalized path is within input directory
if (!startsWith(normalized_path, normalized_input_dir)) {
  stop("Invalid file path detected")
}
```

## 3. Authentication Implementation

### Add to api_server.py:
```python
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import jwt
from datetime import datetime, timedelta

# Security setup
security = HTTPBearer()
SECRET_KEY = os.getenv("JWT_SECRET_KEY", "your-secret-key-change-in-production")
ALGORITHM = "HS256"

def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(hours=24)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    token = credentials.credentials
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except jwt.PyJWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

# Add to each endpoint:
@app.post("/api/initialize_meta_analysis")
def initialize_meta_analysis(req: InitializeRequest, auth: dict = Depends(verify_token)):
    # Existing code...
```

## 4. Race Condition Fix

### Current Vulnerable Code:
```python
# app.py line 54
def start_server() -> None:
    global server_proc
    with server_lock:
        if server_proc and server_proc.poll() is None:
            return
        server_proc = subprocess.Popen(...)
```

### Fixed Code:
```python
import threading
import time

class ServerManager:
    def __init__(self):
        self._lock = threading.RLock()
        self._proc = None
        self._starting = False
        
    def start_server(self) -> None:
        with self._lock:
            # Check if already starting
            if self._starting:
                # Wait for other thread to finish starting
                timeout = time.time() + 5
                while self._starting and time.time() < timeout:
                    time.sleep(0.1)
                return
                
            # Check if already running
            if self._proc and self._proc.poll() is None:
                return
                
            # Mark as starting
            self._starting = True
            
        try:
            # Start process outside lock to avoid holding lock during I/O
            proc = subprocess.Popen(
                SERVER_CMD,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1,
            )
            
            # Wait briefly to ensure process started
            time.sleep(0.5)
            
            # Check if process is still running
            if proc.poll() is not None:
                raise RuntimeError("Server process died immediately")
                
            with self._lock:
                self._proc = proc
        finally:
            with self._lock:
                self._starting = False

server_manager = ServerManager()
```

## 5. Input Validation with Size Limits

### Add to upload_data.R:
```r
# Enhanced validation with proper size checking
validate_and_decode_data <- function(data_content, max_size_mb = 50) {
  # Check if base64
  if (grepl("^[A-Za-z0-9+/=]+$", data_content) && nchar(data_content) %% 4 == 0) {
    # Estimate decoded size (base64 is ~33% larger)
    estimated_size <- nchar(data_content) * 0.75
    
    if (estimated_size > max_size_mb * 1024 * 1024) {
      stop(sprintf("Estimated file size (%.1fMB) exceeds limit (%dMB)", 
                   estimated_size / (1024*1024), max_size_mb))
    }
    
    # Decode in chunks to avoid memory issues
    decoded <- tryCatch({
      base64enc::base64decode(data_content)
    }, error = function(e) {
      stop("Failed to decode base64 data: ", e$message)
    })
    
    # Verify actual size
    if (length(decoded) > max_size_mb * 1024 * 1024) {
      stop(sprintf("Decoded file size exceeds limit of %dMB", max_size_mb))
    }
    
    return(decoded)
  } else {
    # Plain text
    if (nchar(data_content, type = "bytes") > max_size_mb * 1024 * 1024) {
      stop(sprintf("File size exceeds limit of %dMB", max_size_mb))
    }
    return(data_content)
  }
}
```

## 6. Memory Leak Prevention

### Fix for chatbot_enhanced.py:
```python
from functools import lru_cache
from datetime import datetime, timedelta
import weakref

class SessionManager:
    def __init__(self, max_sessions=100, ttl_hours=24):
        self._sessions = {}
        self._access_times = {}
        self._max_sessions = max_sessions
        self._ttl = timedelta(hours=ttl_hours)
        self._lock = threading.Lock()
        
        # Start cleanup thread
        self._cleanup_thread = threading.Thread(target=self._cleanup_loop, daemon=True)
        self._cleanup_thread.start()
    
    def get_session(self, session_id: str) -> Optional[Dict]:
        with self._lock:
            if session_id in self._sessions:
                self._access_times[session_id] = datetime.now()
                return self._sessions[session_id]
            return None
    
    def create_session(self, session_id: str, data: Dict) -> None:
        with self._lock:
            # Check if we need to evict old sessions
            if len(self._sessions) >= self._max_sessions:
                self._evict_oldest()
            
            self._sessions[session_id] = data
            self._access_times[session_id] = datetime.now()
    
    def _evict_oldest(self):
        """Evict least recently used session"""
        if not self._access_times:
            return
            
        oldest_id = min(self._access_times.items(), key=lambda x: x[1])[0]
        del self._sessions[oldest_id]
        del self._access_times[oldest_id]
    
    def _cleanup_loop(self):
        """Background thread to clean up expired sessions"""
        while True:
            time.sleep(300)  # Check every 5 minutes
            self._cleanup_expired()
    
    def _cleanup_expired(self):
        with self._lock:
            now = datetime.now()
            expired = [
                sid for sid, last_access in self._access_times.items()
                if now - last_access > self._ttl
            ]
            for sid in expired:
                del self._sessions[sid]
                del self._access_times[sid]
```

## 7. Rate Limiting Implementation

### Add rate limiting middleware:
```python
from collections import defaultdict
from datetime import datetime, timedelta
import asyncio

class RateLimiter:
    def __init__(self, requests_per_minute=30):
        self.requests_per_minute = requests_per_minute
        self.requests = defaultdict(list)
        self._lock = asyncio.Lock()
    
    async def check_rate_limit(self, identifier: str) -> bool:
        async with self._lock:
            now = datetime.now()
            minute_ago = now - timedelta(minutes=1)
            
            # Clean old requests
            self.requests[identifier] = [
                req_time for req_time in self.requests[identifier]
                if req_time > minute_ago
            ]
            
            # Check if limit exceeded
            if len(self.requests[identifier]) >= self.requests_per_minute:
                return False
            
            # Record this request
            self.requests[identifier].append(now)
            return True

# Use in FastAPI:
rate_limiter = RateLimiter()

@app.middleware("http")
async def rate_limit_middleware(request: Request, call_next):
    # Use IP address as identifier
    client_ip = request.client.host
    
    if not await rate_limiter.check_rate_limit(client_ip):
        return JSONResponse(
            status_code=429,
            content={"detail": "Rate limit exceeded"},
            headers={"Retry-After": "60"}
        )
    
    response = await call_next(request)
    return response
```

## 8. Logging Enhancement

### Add structured logging:
```python
import logging
import json
from datetime import datetime

class StructuredLogger:
    def __init__(self, name):
        self.logger = logging.getLogger(name)
        handler = logging.StreamHandler()
        handler.setFormatter(self.JsonFormatter())
        self.logger.addHandler(handler)
        self.logger.setLevel(logging.INFO)
    
    class JsonFormatter(logging.Formatter):
        def format(self, record):
            log_obj = {
                'timestamp': datetime.utcnow().isoformat(),
                'level': record.levelname,
                'logger': record.name,
                'message': record.getMessage(),
                'module': record.module,
                'function': record.funcName,
                'line': record.lineno
            }
            if hasattr(record, 'user_id'):
                log_obj['user_id'] = record.user_id
            if hasattr(record, 'session_id'):
                log_obj['session_id'] = record.session_id
            if record.exc_info:
                log_obj['exception'] = self.formatException(record.exc_info)
            return json.dumps(log_obj)
    
    def log_api_request(self, method, path, user_id=None, session_id=None, status_code=None):
        extra = {'user_id': user_id, 'session_id': session_id}
        self.logger.info(f"API Request: {method} {path} -> {status_code}", extra=extra)
    
    def log_security_event(self, event_type, details, user_id=None):
        extra = {'user_id': user_id}
        self.logger.warning(f"Security Event: {event_type} - {details}", extra=extra)

# Usage:
logger = StructuredLogger(__name__)
logger.log_api_request("POST", "/api/analyze", user_id="user123", status_code=200)
```

These fixes address the most critical security and reliability issues. Implement them in order of priority, starting with security fixes.