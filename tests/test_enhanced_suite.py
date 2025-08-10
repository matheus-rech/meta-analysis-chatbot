#!/usr/bin/env python3
"""
Comprehensive test suite for Enhanced Meta-Analysis Chatbot
"""

import pytest
import os
import sys
import json
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import pandas as pd
import numpy as np

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Import modules to test
from utils.error_handler import (
    SessionRecoveryManager,
    ErrorHandler,
    RProcessManager,
    InputValidator,
    with_error_handling
)
from utils.health_check import HealthChecker

# ============================================
# Test Fixtures
# ============================================

@pytest.fixture
def temp_sessions_dir():
    """Create a temporary sessions directory"""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield tmpdir

@pytest.fixture
def session_recovery_manager(temp_sessions_dir):
    """Create a SessionRecoveryManager with temp directory"""
    return SessionRecoveryManager(temp_sessions_dir)

@pytest.fixture
def error_handler():
    """Create an ErrorHandler instance"""
    return ErrorHandler()

@pytest.fixture
def health_checker():
    """Create a HealthChecker instance"""
    return HealthChecker()

@pytest.fixture
def sample_csv_data():
    """Create sample CSV data for testing"""
    data = pd.DataFrame({
        'study_id': ['Study1', 'Study2', 'Study3'],
        'effect_size': [0.5, 0.3, 0.7],
        'se': [0.1, 0.15, 0.12],
        'n_treatment': [100, 150, 120],
        'n_control': [100, 150, 120]
    })
    return data

# ============================================
# Session Recovery Tests
# ============================================

class TestSessionRecovery:
    
    def test_save_session_state(self, session_recovery_manager):
        """Test saving session state"""
        session_id = "test-session-123"
        state = {
            'function': 'test_function',
            'data': {'key': 'value'},
            'timestamp': '2024-01-01T12:00:00'
        }
        
        result = session_recovery_manager.save_session_state(session_id, state)
        assert result is True
        
        # Verify file was created
        recovery_file = session_recovery_manager.recovery_dir / f"{session_id}.json"
        assert recovery_file.exists()
    
    def test_recover_session(self, session_recovery_manager):
        """Test recovering a saved session"""
        session_id = "test-session-456"
        original_state = {'data': 'test_data', 'value': 42}
        
        # Save state
        session_recovery_manager.save_session_state(session_id, original_state)
        
        # Recover state
        recovered_state = session_recovery_manager.recover_session(session_id)
        assert recovered_state == original_state
    
    def test_list_recoverable_sessions(self, session_recovery_manager):
        """Test listing recoverable sessions"""
        # Create multiple sessions
        for i in range(3):
            session_recovery_manager.save_session_state(
                f"session-{i}",
                {'data': f'data-{i}'}
            )
        
        sessions = session_recovery_manager.list_recoverable_sessions()
        assert len(sessions) == 3
        assert all('session_id' in s and 'timestamp' in s for s in sessions)
    
    def test_cleanup_old_sessions(self, session_recovery_manager):
        """Test cleanup of old sessions"""
        from datetime import datetime, timedelta
        
        # Create an old session
        session_id = "old-session"
        session_recovery_manager.save_session_state(session_id, {'data': 'old'})
        
        # Manually modify timestamp to make it old
        recovery_file = session_recovery_manager.recovery_dir / f"{session_id}.json"
        with open(recovery_file, 'r') as f:
            data = json.load(f)
        
        old_timestamp = (datetime.now() - timedelta(hours=48)).isoformat()
        data['timestamp'] = old_timestamp
        
        with open(recovery_file, 'w') as f:
            json.dump(data, f)
        
        # Run cleanup
        session_recovery_manager.cleanup_old_sessions(max_age_hours=24)
        
        # Verify old session was removed
        assert not recovery_file.exists()

# ============================================
# Error Handling Tests
# ============================================

class TestErrorHandler:
    
    def test_handle_error_with_recovery(self, error_handler):
        """Test error handling with recovery strategy"""
        def recovery_strategy(error, context):
            return "recovered_value"
        
        error_handler.register_recovery_strategy('ValueError', recovery_strategy)
        
        error = ValueError("Test error")
        result = error_handler.handle_error(error, {'test': 'context'})
        
        assert result['status'] == 'recovered'
        assert result['result'] == 'recovered_value'
    
    def test_handle_error_without_recovery(self, error_handler):
        """Test error handling without recovery strategy"""
        error = RuntimeError("Test runtime error")
        result = error_handler.handle_error(error)
        
        assert result['status'] == 'error'
        assert 'error' in result
        assert 'user_message' in result
    
    def test_get_user_friendly_message(self, error_handler):
        """Test user-friendly error messages"""
        test_cases = [
            (FileNotFoundError("test.txt"), "file could not be found"),
            (PermissionError("access denied"), "Permission denied"),
            (ValueError("invalid"), "Invalid input value"),
            (MemoryError(), "Out of memory"),
        ]
        
        for error, expected_substr in test_cases:
            message = error_handler.get_user_friendly_message(error)
            assert expected_substr in message

# ============================================
# Input Validation Tests
# ============================================

class TestInputValidation:
    
    def test_validate_file_upload_valid(self, tmp_path):
        """Test validation of valid file upload"""
        # Create a test CSV file
        test_file = tmp_path / "test.csv"
        test_file.write_text("col1,col2\n1,2\n3,4")
        
        result = InputValidator.validate_file_upload(str(test_file))
        assert result['valid'] is True
        assert result['extension'] == '.csv'
    
    def test_validate_file_upload_invalid_extension(self, tmp_path):
        """Test rejection of invalid file extension"""
        test_file = tmp_path / "test.exe"
        test_file.write_text("malicious")
        
        result = InputValidator.validate_file_upload(str(test_file))
        assert result['valid'] is False
        assert 'not allowed' in result['error']
    
    def test_validate_file_upload_too_large(self, tmp_path):
        """Test rejection of too large files"""
        test_file = tmp_path / "large.csv"
        # Create a file larger than limit
        test_file.write_bytes(b"x" * (51 * 1024 * 1024))  # 51MB
        
        result = InputValidator.validate_file_upload(str(test_file), max_size_mb=50)
        assert result['valid'] is False
        assert 'too large' in result['error']
    
    def test_sanitize_text_input(self):
        """Test text input sanitization"""
        dangerous_input = "test`command`;rm -rf /"
        sanitized = InputValidator.sanitize_text_input(dangerous_input)
        
        assert '`' not in sanitized
        assert ';' not in sanitized
        assert 'rm -rf /' not in sanitized
    
    def test_validate_session_id(self):
        """Test session ID validation"""
        valid_ids = [
            "session-123",
            "abc123def456",
            "TEST-SESSION-789"
        ]
        
        invalid_ids = [
            "short",  # Too short
            "session_with_underscore",  # Invalid character
            "session@123",  # Invalid character
            "a" * 65  # Too long
        ]
        
        for sid in valid_ids:
            assert InputValidator.validate_session_id(sid) is True
        
        for sid in invalid_ids:
            assert InputValidator.validate_session_id(sid) is False

# ============================================
# R Process Manager Tests
# ============================================

class TestRProcessManager:
    
    @patch('subprocess.Popen')
    def test_start_r_process(self, mock_popen):
        """Test starting R process"""
        mock_process = MagicMock()
        mock_process.pid = 12345
        mock_popen.return_value = mock_process
        
        manager = RProcessManager()
        result = manager.start_r_process(['Rscript', 'test.R'])
        
        assert result is True
        assert manager.process is not None
        mock_popen.assert_called_once()
    
    def test_check_health(self):
        """Test R process health check"""
        manager = RProcessManager()
        
        # No process
        assert manager.check_health() is False
        
        # Mock healthy process
        manager.process = MagicMock()
        manager.process.poll.return_value = None
        assert manager.check_health() is True
        
        # Mock crashed process
        manager.process.poll.return_value = 1
        assert manager.check_health() is False
    
    @patch('subprocess.Popen')
    def test_restart_if_needed(self, mock_popen):
        """Test automatic restart of crashed process"""
        mock_process = MagicMock()
        mock_process.pid = 12345
        mock_process.poll.return_value = 1  # Process crashed
        mock_popen.return_value = mock_process
        
        manager = RProcessManager()
        manager.process = mock_process
        
        result = manager.restart_if_needed(['Rscript', 'test.R'])
        assert result is True
        assert manager.restart_count == 1

# ============================================
# Health Check Tests
# ============================================

class TestHealthChecker:
    
    def test_check_api_keys(self, health_checker):
        """Test API key configuration check"""
        with patch.dict(os.environ, {'OPENAI_API_KEY': 'test-key'}):
            result = health_checker.check_api_keys()
            assert result['openai']['configured'] is True
            assert result['any_configured'] is True
    
    def test_check_directories(self, health_checker, tmp_path):
        """Test directory existence check"""
        with patch.dict(os.environ, {'SESSIONS_DIR': str(tmp_path)}):
            result = health_checker.check_directories()
            assert 'sessions' in result
            # Directory should be created if it doesn't exist
            assert result['sessions']['exists'] is True
    
    @patch('subprocess.run')
    def test_check_r_backend(self, mock_run, health_checker):
        """Test R backend availability check"""
        # Mock successful R check
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "OK"
        mock_result.stderr = "R version 4.3.0"
        mock_run.return_value = mock_result
        
        result = health_checker.check_r_backend()
        assert result['available'] is True
        assert result['status'] == 'ok'
    
    def test_get_simple_health_check(self, health_checker):
        """Test simple health check for load balancers"""
        with patch.object(health_checker, 'check_r_backend') as mock_r:
            mock_r.return_value = {'available': True, 'status': 'ok'}
            
            with patch.dict(os.environ, {'OPENAI_API_KEY': 'test'}):
                result = health_checker.get_simple_health_check()
                assert result['status'] == 'healthy'
                assert 'timestamp' in result
    
    @patch('psutil.cpu_percent')
    @patch('psutil.virtual_memory')
    @patch('psutil.disk_usage')
    def test_check_system_resources(self, mock_disk, mock_memory, mock_cpu, health_checker):
        """Test system resource monitoring"""
        mock_cpu.return_value = 50.0
        mock_memory.return_value = MagicMock(
            percent=60.0,
            available=4 * 1024**3  # 4GB
        )
        mock_disk.return_value = MagicMock(
            percent=70.0,
            free=10 * 1024**3  # 10GB
        )
        
        result = health_checker.check_system_resources()
        
        assert result['cpu']['percent'] == 50.0
        assert result['cpu']['status'] == 'ok'
        assert result['memory']['percent'] == 60.0
        assert result['memory']['status'] == 'ok'
        assert result['disk']['percent'] == 70.0
        assert result['disk']['status'] == 'ok'

# ============================================
# Integration Tests
# ============================================

class TestIntegration:
    
    def test_error_handling_decorator(self, session_recovery_manager):
        """Test the error handling decorator with session recovery"""
        
        @with_error_handling(recovery_manager=session_recovery_manager)
        def test_function(value, session_id=None):
            if value < 0:
                raise ValueError("Negative value not allowed")
            return value * 2
        
        # Test successful execution
        result = test_function(5, session_id="test-session")
        assert result == 10
        
        # Test error handling
        result = test_function(-5, session_id="test-session")
        assert result['status'] == 'error'
        assert 'user_message' in result
        
        # Verify session was saved for recovery
        recovered = session_recovery_manager.recover_session("test-session")
        assert recovered is not None
    
    def test_full_health_status(self, health_checker):
        """Test comprehensive health status check"""
        with patch.object(health_checker, 'check_system_resources') as mock_sys:
            mock_sys.return_value = {'status': 'ok'}
            
            with patch.object(health_checker, 'check_r_backend') as mock_r:
                mock_r.return_value = {'status': 'ok'}
                
                with patch.object(health_checker, 'check_dependencies') as mock_deps:
                    mock_deps.return_value = {'status': 'ok', 'all_installed': True}
                    
                    result = health_checker.get_full_health_status()
                    
                    assert 'timestamp' in result
                    assert 'overall_status' in result
                    assert result['checks_performed'] == 1

# ============================================
# Performance Tests
# ============================================

class TestPerformance:
    
    def test_session_recovery_performance(self, session_recovery_manager):
        """Test performance of session recovery with many sessions"""
        import time
        
        # Create 100 sessions
        start_time = time.time()
        for i in range(100):
            session_recovery_manager.save_session_state(
                f"perf-session-{i}",
                {'data': f'test-data-{i}' * 100}  # Some data
            )
        save_time = time.time() - start_time
        
        # List all sessions
        start_time = time.time()
        sessions = session_recovery_manager.list_recoverable_sessions()
        list_time = time.time() - start_time
        
        assert len(sessions) == 100
        assert save_time < 5.0  # Should complete within 5 seconds
        assert list_time < 1.0  # Listing should be fast
    
    def test_input_validation_performance(self):
        """Test performance of input validation"""
        import time
        
        # Test sanitization of large text
        large_text = "test " * 10000  # 50,000 characters
        
        start_time = time.time()
        for _ in range(100):
            InputValidator.sanitize_text_input(large_text)
        elapsed = time.time() - start_time
        
        assert elapsed < 1.0  # 100 sanitizations should be fast

# ============================================
# Run Tests
# ============================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])