#!/usr/bin/env python3
"""
MCP Inspector setup and testing script
Uses MCP Inspector to test and debug the Meta-Analysis MCP server
"""

import os
import sys
import json
import subprocess
import time
import requests
from pathlib import Path
from typing import Dict, Any, List, Optional


class MCPInspectorTester:
    """
    MCP Inspector testing utilities
    
    MCP Inspector is a debugging tool for MCP servers that provides:
    - Interactive testing of MCP tools
    - Request/response inspection
    - Performance profiling
    - Error debugging
    """
    
    def __init__(self):
        self.inspector_installed = False
        self.server_process = None
        self.inspector_process = None
    
    def check_dependencies(self) -> bool:
        """Check if required dependencies are installed"""
        
        print("Checking dependencies...")
        
        # Check for Node.js (required for MCP Inspector)
        try:
            result = subprocess.run(
                ["node", "--version"],
                capture_output=True,
                text=True
            )
            if result.returncode == 0:
                print(f"✓ Node.js installed: {result.stdout.strip()}")
            else:
                print("✗ Node.js not found. Please install Node.js first.")
                return False
        except FileNotFoundError:
            print("✗ Node.js not found. Please install Node.js first.")
            return False
        
        # Check for npm
        try:
            result = subprocess.run(
                ["npm", "--version"],
                capture_output=True,
                text=True
            )
            if result.returncode == 0:
                print(f"✓ npm installed: {result.stdout.strip()}")
            else:
                print("✗ npm not found.")
                return False
        except FileNotFoundError:
            print("✗ npm not found.")
            return False
        
        return True
    
    def install_mcp_inspector(self) -> bool:
        """Install MCP Inspector via npm"""
        
        print("\nInstalling MCP Inspector...")
        
        # Check if already installed
        try:
            result = subprocess.run(
                ["npx", "mcp-inspector", "--version"],
                capture_output=True,
                text=True,
                timeout=10
            )
            if result.returncode == 0:
                print("✓ MCP Inspector already installed")
                self.inspector_installed = True
                return True
        except (FileNotFoundError, subprocess.TimeoutExpired):
            pass
        
        # Install MCP Inspector
        try:
            print("Installing @modelcontextprotocol/inspector...")
            result = subprocess.run(
                ["npm", "install", "-g", "@modelcontextprotocol/inspector"],
                capture_output=True,
                text=True,
                timeout=60
            )
            
            if result.returncode == 0:
                print("✓ MCP Inspector installed successfully")
                self.inspector_installed = True
                return True
            else:
                print(f"✗ Installation failed: {result.stderr}")
                return False
                
        except Exception as e:
            print(f"✗ Error installing MCP Inspector: {e}")
            return False
    
    def start_mcp_server(self) -> bool:
        """Start the Meta-Analysis MCP server"""
        
        print("\nStarting Meta-Analysis MCP server...")
        
        env = os.environ.copy()
        env["DEBUG_R"] = "1"
        env["PYTHONUNBUFFERED"] = "1"
        env["RSCRIPT_TIMEOUT_SEC"] = "60"
        
        try:
            self.server_process = subprocess.Popen(
                ["python", "server.py"],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                env=env
            )
            
            time.sleep(3)  # Give server time to start
            
            # Test if server is responding
            test_request = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "tools/list",
                "params": {}
            }
            
            self.server_process.stdin.write(json.dumps(test_request) + "\n")
            self.server_process.stdin.flush()
            
            # Try to read response
            import select
            if select.select([self.server_process.stdout], [], [], 5)[0]:
                response = self.server_process.stdout.readline()
                if response:
                    print("✓ MCP server started and responding")
                    return True
            
            print("✗ MCP server not responding")
            return False
            
        except Exception as e:
            print(f"✗ Error starting MCP server: {e}")
            return False
    
    def create_inspector_config(self) -> str:
        """Create configuration file for MCP Inspector"""
        
        config = {
            "servers": {
                "meta-analysis": {
                    "command": "python",
                    "args": ["server.py"],
                    "env": {
                        "DEBUG_R": "1",
                        "PYTHONUNBUFFERED": "1",
                        "RSCRIPT_TIMEOUT_SEC": "60",
                        "SESSIONS_DIR": str(Path.cwd() / "sessions")
                    }
                }
            }
        }
        
        config_path = Path("mcp-inspector-config.json")
        with open(config_path, "w") as f:
            json.dump(config, f, indent=2)
        
        print(f"✓ Created inspector config: {config_path}")
        return str(config_path)
    
    def start_mcp_inspector(self, config_path: str) -> bool:
        """Start MCP Inspector with our server configuration"""
        
        print("\nStarting MCP Inspector...")
        
        try:
            # Start inspector with our config
            self.inspector_process = subprocess.Popen(
                ["npx", "mcp-inspector", config_path],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            time.sleep(5)  # Give inspector time to start
            
            print("✓ MCP Inspector started")
            print("  Open http://localhost:5173 in your browser")
            print("  The inspector provides:")
            print("    - Interactive tool testing")
            print("    - Request/response inspection")
            print("    - Performance profiling")
            print("    - Error debugging")
            
            return True
            
        except Exception as e:
            print(f"✗ Error starting MCP Inspector: {e}")
            return False
    
    def run_inspector_tests(self):
        """Guide for using MCP Inspector to test the server"""
        
        print("\n" + "="*60)
        print("MCP INSPECTOR TEST GUIDE")
        print("="*60)
        
        print("""
1. TOOL DISCOVERY TEST:
   - Click on "meta-analysis" server in the inspector
   - Click "Tools" tab
   - Verify all 8 tools are listed:
     * initialize_meta_analysis
     * upload_study_data
     * perform_meta_analysis
     * generate_forest_plot
     * assess_publication_bias
     * generate_report
     * get_session_status
     * health_check

2. HEALTH CHECK TEST:
   - Select "health_check" tool
   - Click "Execute"
   - Verify response shows:
     * R packages installed
     * R version information

3. INITIALIZATION TEST:
   - Select "initialize_meta_analysis"
   - Fill in parameters:
     * name: "Test Analysis"
     * study_type: "clinical_trial"
     * effect_measure: "OR"
     * analysis_model: "random"
   - Click "Execute"
   - Copy the session_id from response

4. DATA UPLOAD TEST:
   - Select "upload_study_data"
   - Use the session_id from step 3
   - Prepare test data (base64 encoded CSV)
   - Set validation_level: "comprehensive"
   - Execute and verify success

5. ANALYSIS TEST:
   - Select "perform_meta_analysis"
   - Use the same session_id
   - Enable heterogeneity_test
   - Execute and inspect results:
     * Overall effect
     * Confidence intervals
     * Heterogeneity metrics
     * P-values

6. FOREST PLOT TEST:
   - Select "generate_forest_plot"
   - Use the same session_id
   - Set plot_style: "classic"
   - Execute and verify plot path

7. PERFORMANCE TESTING:
   - Use Inspector's timing information
   - Check response times for each tool
   - Identify any bottlenecks

8. ERROR TESTING:
   - Try invalid session IDs
   - Upload malformed data
   - Use incorrect parameters
   - Verify error messages are informative
        """)
        
        print("\n" + "="*60)
        print("AUTOMATED TEST RESULTS")
        print("="*60)
        
        # Run some automated tests via the inspector API if available
        self.run_automated_tests()
    
    def run_automated_tests(self):
        """Run automated tests through MCP Inspector if API is available"""
        
        print("\nRunning automated tests...")
        
        # Test data
        test_cases = [
            {
                "name": "Tool Discovery",
                "method": "tools/list",
                "params": {},
                "expected": lambda r: "tools" in r and len(r["tools"]) >= 8
            },
            {
                "name": "Health Check",
                "method": "tools/call",
                "params": {
                    "name": "health_check",
                    "arguments": {}
                },
                "expected": lambda r: "content" in r
            },
            {
                "name": "Initialize Analysis",
                "method": "tools/call",
                "params": {
                    "name": "initialize_meta_analysis",
                    "arguments": {
                        "name": "Automated Test",
                        "study_type": "clinical_trial",
                        "effect_measure": "OR",
                        "analysis_model": "random"
                    }
                },
                "expected": lambda r: "content" in r
            }
        ]
        
        passed = 0
        failed = 0
        
        for test in test_cases:
            try:
                # Send request to server
                request = {
                    "jsonrpc": "2.0",
                    "id": 1,
                    "method": test["method"],
                    "params": test["params"]
                }
                
                self.server_process.stdin.write(json.dumps(request) + "\n")
                self.server_process.stdin.flush()
                
                # Read response
                response_line = self.server_process.stdout.readline()
                response = json.loads(response_line)
                
                # Check result
                if "result" in response and test["expected"](response["result"]):
                    print(f"✓ {test['name']}: PASSED")
                    passed += 1
                else:
                    print(f"✗ {test['name']}: FAILED")
                    print(f"  Response: {response}")
                    failed += 1
                    
            except Exception as e:
                print(f"✗ {test['name']}: ERROR - {e}")
                failed += 1
        
        print(f"\nResults: {passed} passed, {failed} failed")
    
    def cleanup(self):
        """Clean up processes"""
        
        print("\nCleaning up...")
        
        if self.server_process:
            self.server_process.terminate()
            try:
                self.server_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.server_process.kill()
        
        if self.inspector_process:
            self.inspector_process.terminate()
            try:
                self.inspector_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.inspector_process.kill()
        
        print("✓ Cleanup complete")


def main():
    """Main test runner"""
    
    print("MCP Inspector Testing Setup")
    print("="*60)
    
    tester = MCPInspectorTester()
    
    try:
        # Check dependencies
        if not tester.check_dependencies():
            print("\nPlease install Node.js from https://nodejs.org/")
            return 1
        
        # Install MCP Inspector
        if not tester.install_mcp_inspector():
            print("\nFailed to install MCP Inspector")
            print("Try manual installation:")
            print("  npm install -g @modelcontextprotocol/inspector")
            return 1
        
        # Create configuration
        config_path = tester.create_inspector_config()
        
        # Start MCP server
        if not tester.start_mcp_server():
            print("\nFailed to start MCP server")
            return 1
        
        # Start MCP Inspector
        if not tester.start_mcp_inspector(config_path):
            print("\nFailed to start MCP Inspector")
            print("Try running manually:")
            print(f"  npx mcp-inspector {config_path}")
            return 1
        
        # Run tests
        tester.run_inspector_tests()
        
        # Keep running for interactive testing
        print("\n" + "="*60)
        print("Inspector is running at http://localhost:5173")
        print("Press Ctrl+C to stop")
        print("="*60)
        
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\nStopping...")
        
    finally:
        tester.cleanup()
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
