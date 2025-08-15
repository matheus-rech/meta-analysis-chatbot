#!/usr/bin/env python3
"""
Basic functionality tests that work without external dependencies
Tests core server functionality and health checks
"""

import sys
import os
import json
import subprocess
import time
from pathlib import Path

# Add the project root to Python path
sys.path.insert(0, str(Path(__file__).parent))

def test_server_health_endpoint():
    """Test that server.py responds to health checks"""
    print("🔍 Testing server health endpoint...")
    
    try:
        # Start server process
        proc = subprocess.Popen(
            [sys.executable, "server.py"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            cwd=str(Path(__file__).parent)
        )
        
        # Test health endpoint
        health_request = {
            "jsonrpc": "2.0",
            "method": "health",
            "id": "test_health"
        }
        
        proc.stdin.write(json.dumps(health_request) + "\n")
        proc.stdin.flush()
        
        # Read response with timeout
        response_line = proc.stdout.readline()
        
        if response_line:
            response = json.loads(response_line)
            if response.get("result", {}).get("status") == "healthy":
                print("✅ Health endpoint working")
                result = True
            else:
                print(f"❌ Health endpoint returned: {response}")
                result = False
        else:
            print("❌ No response from health endpoint")
            result = False
            
        # Clean up
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()
            
        return result
        
    except Exception as e:
        print(f"❌ Health endpoint test failed: {e}")
        return False

def test_r_health_check():
    """Test R health check functionality"""
    print("🔍 Testing R health check...")
    
    try:
        # Start server process
        proc = subprocess.Popen(
            [sys.executable, "server.py"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            cwd=str(Path(__file__).parent)
        )
        
        # Test R health check tool
        health_request = {
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {
                "name": "health_check",
                "arguments": {}
            },
            "id": "test_r_health"
        }
        
        proc.stdin.write(json.dumps(health_request) + "\n")
        proc.stdin.flush()
        
        # Read response
        response_line = proc.stdout.readline()
        
        if response_line:
            response = json.loads(response_line)
            result_content = response.get("result", {}).get("content", [])
            if result_content:
                r_result = json.loads(result_content[0]["text"])
                if r_result.get("status") in ["success", "warning"]:
                    print(f"✅ R health check working: {r_result.get('message', 'OK')}")
                    result = True
                else:
                    print(f"❌ R health check failed: {r_result}")
                    result = False
            else:
                print(f"❌ No content in R health response: {response}")
                result = False
        else:
            print("❌ No response from R health check")
            result = False
            
        # Clean up
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()
            
        return result
        
    except Exception as e:
        print(f"❌ R health check test failed: {e}")
        return False

def test_tools_list():
    """Test that server can list available tools"""
    print("🔍 Testing tools list endpoint...")
    
    try:
        # Start server process
        proc = subprocess.Popen(
            [sys.executable, "server.py"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            cwd=str(Path(__file__).parent)
        )
        
        # Test tools list
        tools_request = {
            "jsonrpc": "2.0",
            "method": "tools/list",
            "id": "test_tools"
        }
        
        proc.stdin.write(json.dumps(tools_request) + "\n")
        proc.stdin.flush()
        
        # Read response
        response_line = proc.stdout.readline()
        
        if response_line:
            response = json.loads(response_line)
            tools = response.get("result", {}).get("tools", [])
            expected_tools = ["health_check", "initialize_meta_analysis", "upload_study_data", 
                            "perform_meta_analysis", "generate_forest_plot", "assess_publication_bias",
                            "generate_report", "get_session_status", "execute_r_code"]
            
            found_tools = [tool["name"] for tool in tools]
            missing_tools = [tool for tool in expected_tools if tool not in found_tools]
            
            if not missing_tools:
                print(f"✅ All expected tools found: {len(found_tools)} tools")
                result = True
            else:
                print(f"❌ Missing tools: {missing_tools}")
                print(f"Found tools: {found_tools}")
                result = False
        else:
            print("❌ No response from tools list")
            result = False
            
        # Clean up
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()
            
        return result
        
    except Exception as e:
        print(f"❌ Tools list test failed: {e}")
        return False

def test_invalid_request():
    """Test that server handles invalid requests properly"""
    print("🔍 Testing invalid request handling...")
    
    try:
        # Start server process
        proc = subprocess.Popen(
            [sys.executable, "server.py"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            cwd=str(Path(__file__).parent)
        )
        
        # Test invalid method
        invalid_request = {
            "jsonrpc": "2.0",
            "method": "invalid_method",
            "id": "test_invalid"
        }
        
        proc.stdin.write(json.dumps(invalid_request) + "\n")
        proc.stdin.flush()
        
        # Read response
        response_line = proc.stdout.readline()
        
        if response_line:
            response = json.loads(response_line)
            error = response.get("error", {})
            if error.get("code") == -32601 and "not found" in error.get("message", "").lower():
                print("✅ Invalid requests handled properly")
                result = True
            else:
                print(f"❌ Unexpected error response: {response}")
                result = False
        else:
            print("❌ No response to invalid request")
            result = False
            
        # Clean up
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()
            
        return result
        
    except Exception as e:
        print(f"❌ Invalid request test failed: {e}")
        return False

def test_session_initialization():
    """Test that session initialization works"""
    print("🔍 Testing session initialization...")
    
    try:
        # Start server process
        proc = subprocess.Popen(
            [sys.executable, "server.py"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            cwd=str(Path(__file__).parent)
        )
        
        # Test session initialization
        init_request = {
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {
                "name": "initialize_meta_analysis",
                "arguments": {
                    "name": "Test Analysis",
                    "study_type": "clinical_trial",
                    "effect_measure": "OR",
                    "analysis_model": "random"
                }
            },
            "id": "test_session_init"
        }
        
        proc.stdin.write(json.dumps(init_request) + "\n")
        proc.stdin.flush()
        
        # Read response
        response_line = proc.stdout.readline()
        
        if response_line:
            response = json.loads(response_line)
            result_content = response.get("result", {}).get("content", [])
            if result_content:
                result = json.loads(result_content[0]["text"])
                if result.get("status") == "success" and result.get("session_id"):
                    print(f"✅ Session initialization working: {result.get('session_id')[:8]}...")
                    result_success = True
                else:
                    print(f"❌ Session init failed: {result}")
                    result_success = False
            else:
                print(f"❌ No content in session init response: {response}")
                result_success = False
        else:
            print("❌ No response from session initialization")
            result_success = False
            
        # Clean up
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()
            
        return result_success
        
    except Exception as e:
        print(f"❌ Session initialization test failed: {e}")
        return False

def main():
    """Run all basic functionality tests"""
    print("=" * 60)
    print("BASIC FUNCTIONALITY TESTS")
    print("=" * 60)
    
    tests = [
        test_server_health_endpoint,
        test_r_health_check,
        test_tools_list,
        test_session_initialization,
        test_invalid_request
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        try:
            if test():
                passed += 1
            print()  # Add spacing between tests
        except Exception as e:
            print(f"❌ Test {test.__name__} crashed: {e}\n")
    
    print("=" * 60)
    print(f"RESULTS: {passed}/{total} tests passed")
    print("=" * 60)
    
    return passed == total

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)