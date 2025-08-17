#!/usr/bin/env python3
"""
Test security fixes implementation
"""
import sys
import os

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

if __name__ == "__main__":
    print("Running security fixes validation tests...\n")
    
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
    
    print(f"Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All security fixes validation tests passed!")
        sys.exit(0)
    else:
        print("⚠️ Some tests failed. Check the output above for details.")
        sys.exit(1)