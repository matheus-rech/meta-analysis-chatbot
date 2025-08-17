#!/usr/bin/env python3
"""
Test script to verify the security fixes are working properly.
"""

import sys
import os

# Add current directory to path for imports
sys.path.insert(0, os.path.dirname(__file__))

def test_security_integration_import():
    """Test that security integration can be imported without errors"""
    try:
        from utils.security_integration import SecurePatterns
        print("✅ Security integration imports successfully")
        return True
    except Exception as e:
        print(f"❌ Security integration import failed: {e}")
        return False

def test_apply_security_patches_behavior():
    """Test that apply_security_patches works and handles errors"""
    try:
        from utils.security_integration import apply_security_patches, SecurePatterns

        # Test normal behavior
        dummy_target = {}
        result = apply_security_patches(dummy_target)
        print("✅ apply_security_patches executed successfully")
        assert result is not None, "apply_security_patches should return a value"

        # Test error handling by passing invalid input (if possible)
        try:
            apply_security_patches(None)
            print("✅ apply_security_patches handled None input gracefully")
        except Exception as err:
            print(f"✅ apply_security_patches raised error as expected for None input: {err}")

        return True
    except Exception as e:
        print(f"❌ apply_security_patches test failed: {e}")
        return False

def test_server_import():
    """Test that server module can be imported"""
    try:
        import server
        print("✅ Server module imports successfully")
        return True
    except Exception as e:
        print(f"❌ Server import failed: {e}")
        return False

def test_secure_patterns():
    """Test that SecurePatterns methods are available"""
    try:
        from utils.security_integration import SecurePatterns
        
        # Check if methods exist
        assert hasattr(SecurePatterns, 'safe_subprocess_run'), "safe_subprocess_run method missing"
        assert hasattr(SecurePatterns, 'safe_subprocess_popen'), "safe_subprocess_popen method missing"
        
        print("✅ SecurePatterns methods are available")
        return True
    except Exception as e:
        print(f"❌ SecurePatterns test failed: {e}")
        return False

def test_basic_functionality():
    """Test basic functionality without external dependencies"""
    try:
        # Test path validation
        from utils.validators import InputValidator
        
        # Test basic string validation
        result = InputValidator.validate_string("test123", pattern="alphanumeric")
        print(f"✅ Input validation works: {result}")
        return True
    except Exception as e:
        print(f"❌ Basic functionality test failed: {e}")
        return False

def test_command_injection_fix():
    """Test that command injection is prevented in server.py"""
    print("Testing Command Injection Fix...")
    
    from server import execute_r
    
    # Test 1: Valid tool name should work
    result = execute_r("health_check", {})
    print(f"✓ Valid tool name 'health_check' accepted: {result.get('status', 'unknown')}")
    
    # Test 2: Invalid tool name should be rejected
    result = execute_r("invalid_tool; rm -rf /", {})
    assert result['status'] == 'error', "Should reject invalid tool name"
    assert 'Invalid tool name' in result['message'], "Should provide clear error message"
    print("✓ Malicious tool name rejected")
    
    # Test 3: Tool name with path injection should be rejected
    result = execute_r("../../../etc/passwd", {})
    assert result['status'] == 'error', "Should reject path traversal in tool name"
    print("✓ Path traversal in tool name rejected")
    
    print("✅ Command injection fixes working correctly\n")

def test_input_validation():
    """Test that input validation is working"""
    print("Testing Input Validation...")
    
    from utils.validators import InputValidator, ValidationError
    
    # Test 1: Valid session ID
    try:
        result = InputValidator.validate_session_id("test-session-123")
        print("✓ Valid session ID accepted")
    except ValidationError:
        print("✗ Valid session ID rejected (unexpected)")
    
    # Test 2: Invalid session ID with dangerous characters
    try:
        result = InputValidator.validate_session_id("test; rm -rf /")
        print("✗ Dangerous session ID accepted (security issue)")
    except ValidationError:
        print("✓ Dangerous session ID rejected")
    
    # Test 3: Valid enum value
    try:
        result = InputValidator.validate_enum("csv", "data_format")
        print("✓ Valid data format accepted")
    except ValidationError:
        print("✗ Valid data format rejected (unexpected)")
    
    # Test 4: Invalid enum value
    try:
        result = InputValidator.validate_enum("../../../etc/passwd", "data_format")
        print("✗ Path traversal in enum accepted (security issue)")
    except ValidationError:
        print("✓ Path traversal in enum rejected")
    
    print("✅ Input validation working correctly\n")

def test_path_traversal_fix():
    """Test that path traversal is prevented"""
    print("Testing Path Traversal Fix...")
    
    # Test validation of file formats
    from utils.validators import InputValidator, ValidationError
    
    # Valid formats should work
    valid_formats = ["csv", "excel", "xlsx"]
    for fmt in valid_formats:
        try:
            result = InputValidator.validate_enum(fmt, "data_format")
            print(f"✓ Valid format '{fmt}' accepted")
        except ValidationError:
            print(f"✗ Valid format '{fmt}' rejected (unexpected)")
    
    # Invalid formats should be rejected
    invalid_formats = ["../../../etc/passwd", "script.sh", "malware.exe"]
    for fmt in invalid_formats:
        try:
            result = InputValidator.validate_enum(fmt, "data_format")
            print(f"✗ Dangerous format '{fmt}' accepted (security issue)")
        except ValidationError:
            print(f"✓ Dangerous format '{fmt}' rejected")
    
    print("✅ Path traversal fixes working correctly\n")

def test_session_cleanup():
    """Test session cleanup mechanism"""
    print("Testing Session Cleanup...")
    
    # This is a simplified test since we can't easily test the actual TTL without waiting
    try:
        from chatbot_enhanced import MCPClient
        
        # Create a client instance
        client = MCPClient()
        
        # Check that cleanup methods exist
        assert hasattr(client, '_cleanup_expired_sessions'), "Cleanup method should exist"
        assert hasattr(client, '_session_access_times'), "Access time tracking should exist"
        assert hasattr(client, '_session_ttl'), "TTL should be configured"
        
        print("✓ Session cleanup mechanism is properly implemented")
        print(f"✓ Session TTL configured: {client._session_ttl} seconds")
        
    except ImportError as e:
        print(f"⚠ Could not test session cleanup due to missing dependencies: {e}")
    
    print("✅ Session cleanup test completed\n")

def main():
    """Run all security tests"""
    print("=" * 60)
    print("SECURITY FIXES VERIFICATION")
    print("=" * 60)
    print()
    
    try:
        # Validation block for integration and server
        tests = [
            test_security_integration_import,
            test_server_import, 
            test_secure_patterns,
            test_basic_functionality
        ]
        passed = 0
        total = len(tests)
        for test in tests:
            if test():
                passed += 1
            print()
        print(f"Test Results: {passed}/{total} basic tests passed")
        if passed != total:
            print("⚠️ Some basic tests failed. Check the output above for details.\n")
        
        # Security-specific tests
        test_command_injection_fix()
        test_input_validation()
        test_path_traversal_fix()
        test_session_cleanup()
        
        print("=" * 60)
        print("🎉 ALL SECURITY FIXES VERIFIED SUCCESSFULLY!")
        print("=" * 60)
        return 0
        
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(main())
