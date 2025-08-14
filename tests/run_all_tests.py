#!/usr/bin/env python3
"""
Master test runner for Meta-Analysis Chatbot
Runs all test suites and generates comprehensive report
"""

import os
import sys
import subprocess
import time
import json
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any


class TestRunner:
    """Orchestrates all test suites"""
    
    def __init__(self):
        self.results = {}
        self.start_time = None
        self.end_time = None
        self.test_dir = Path(__file__).parent
        self.project_root = self.test_dir.parent
    
    def check_environment(self) -> bool:
        """Check test environment is properly set up"""
        
        print("Checking test environment...")
        
        checks = {
            "Python": self._check_python(),
            "R": self._check_r(),
            "Node.js": self._check_node(),
            "Playwright": self._check_playwright(),
            "R packages": self._check_r_packages(),
            "Python packages": self._check_python_packages()
        }
        
        all_passed = all(checks.values())
        
        print("\nEnvironment Check Results:")
        for name, passed in checks.items():
            status = "✓" if passed else "✗"
            print(f"  {status} {name}")
        
        return all_passed
    
    def _check_python(self) -> bool:
        """Check Python version"""
        try:
            import sys
            version = sys.version_info
            return version.major == 3 and version.minor >= 8
        except:
            return False
    
    def _check_r(self) -> bool:
        """Check R is installed"""
        try:
            result = subprocess.run(
                ["Rscript", "--version"],
                capture_output=True,
                text=True
            )
            return result.returncode == 0
        except:
            return False
    
    def _check_node(self) -> bool:
        """Check Node.js is installed"""
        try:
            result = subprocess.run(
                ["node", "--version"],
                capture_output=True,
                text=True
            )
            return result.returncode == 0
        except:
            return False
    
    def _check_playwright(self) -> bool:
        """Check Playwright is installed"""
        try:
            import playwright
            return True
        except ImportError:
            return False
    
    def _check_r_packages(self) -> bool:
        """Check required R packages"""
        try:
            script = """
            packages <- c("meta", "metafor", "jsonlite")
            all(packages %in% installed.packages()[,"Package"])
            """
            result = subprocess.run(
                ["Rscript", "-e", script],
                capture_output=True,
                text=True
            )
            return "TRUE" in result.stdout
        except:
            return False
    
    def _check_python_packages(self) -> bool:
        """Check required Python packages"""
        required = ["gradio", "pandas", "numpy", "pytest", "playwright"]
        try:
            for pkg in required:
                __import__(pkg)
            return True
        except ImportError:
            return False
    
    def install_dependencies(self):
        """Install missing dependencies"""
        
        print("\nInstalling dependencies...")
        
        # Install Python packages
        print("Installing Python packages...")
        subprocess.run([
            sys.executable, "-m", "pip", "install", "-r", 
            str(self.project_root / "requirements-chatbot.txt")
        ])
        
        subprocess.run([
            sys.executable, "-m", "pip", "install",
            "pytest", "pytest-asyncio", "pytest-html", "playwright", "pytest-playwright"
        ])
        
        # Install Playwright browsers
        print("Installing Playwright browsers...")
        subprocess.run(["playwright", "install", "chromium"])
        
        # Install R packages
        print("Installing R packages...")
        r_script = """
        packages <- c("meta", "metafor", "jsonlite", "ggplot2", "rmarkdown", "knitr")
        for (pkg in packages) {
            if (!pkg %in% installed.packages()[,"Package"]) {
                install.packages(pkg, repos="https://cloud.r-project.org")
            }
        }
        """
        subprocess.run(["Rscript", "-e", r_script])
    
    def start_gradio_server(self) -> subprocess.Popen:
        """Start Gradio server for testing"""
        
        print("\nStarting Gradio server...")
        
        env = os.environ.copy()
        env["PYTHONUNBUFFERED"] = "1"
        env["DEBUG_R"] = "1"
        env["TEST_MODE"] = "1"
        
        # Use a test API key if not set
        if "OPENAI_API_KEY" not in env and "ANTHROPIC_API_KEY" not in env:
            env["OPENAI_API_KEY"] = "test-key-for-ui-testing"
        
        proc = subprocess.Popen(
            [sys.executable, str(self.project_root / "chatbot_enhanced.py")],
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        # Wait for server to start
        print("Waiting for Gradio to start...")
        time.sleep(10)
        
        return proc
    
    def run_test_suite(self, name: str, command: List[str]) -> Dict[str, Any]:
        """Run a test suite and capture results"""
        
        print(f"\n{'='*60}")
        print(f"Running {name}")
        print('='*60)
        
        start = time.time()
        
        try:
            result = subprocess.run(
                command,
                cwd=str(self.project_root),
                capture_output=True,
                text=True,
                timeout=300  # 5 minute timeout
            )
            
            duration = time.time() - start
            
            # Parse pytest output for test counts
            output = result.stdout + result.stderr
            passed = output.count(" passed")
            failed = output.count(" failed")
            errors = output.count(" error")
            skipped = output.count(" skipped")
            
            return {
                "name": name,
                "passed": passed,
                "failed": failed,
                "errors": errors,
                "skipped": skipped,
                "duration": duration,
                "success": result.returncode == 0,
                "output": output[-5000:] if len(output) > 5000 else output  # Last 5000 chars
            }
            
        except subprocess.TimeoutExpired:
            return {
                "name": name,
                "passed": 0,
                "failed": 0,
                "errors": 1,
                "skipped": 0,
                "duration": 300,
                "success": False,
                "output": "Test suite timed out after 5 minutes"
            }
        except Exception as e:
            return {
                "name": name,
                "passed": 0,
                "failed": 0,
                "errors": 1,
                "skipped": 0,
                "duration": time.time() - start,
                "success": False,
                "output": str(e)
            }
    
    def run_all_tests(self):
        """Run all test suites"""
        
        self.start_time = datetime.now()
        
        # Check environment
        if not self.check_environment():
            print("\n⚠️  Some dependencies are missing. Assuming they are globally installed and proceeding.")
            # response = input("Install dependencies? (y/n): ")
            # if response.lower() == 'y':
            #     self.install_dependencies()
            # else:
            #     print("Please install dependencies manually and try again.")
            #     return False
        
        # Let test suites manage their own servers
        try:
            # Define test suites
            test_suites = [
                {
                    "name": "MCP Server Functional Tests",
                    "command": [
                        sys.executable, "-m", "pytest",
                        "tests/test_mcp_server_functional.py",
                        "-v", "--tb=short"
                    ]
                },
                {
                    "name": "Gradio UI Playwright Tests",
                    "command": [
                        sys.executable, "-m", "pytest",
                        "tests/test_gradio_ui_playwright.py",
                        "-v", "--tb=short",
                        "--html=tests/playwright_report.html",
                        "--self-contained-html"
                    ]
                },
                # Disable client integration for now (file may be optional in this repo)
                # {
                #     "name": "MCP Client Integration Tests",
                #     "command": [
                #         sys.executable, "test_mcp_clients.py"
                #     ]
                # }
            ]
            
            # Run each test suite
            for suite in test_suites:
                result = self.run_test_suite(suite["name"], suite["command"])
                self.results[suite["name"]] = result
            
        finally:
            # Server cleanup is now handled by individual test suites
            pass
        
        self.end_time = datetime.now()
        
        # Generate report
        self.generate_report()
        
        # Return overall success
        return all(r["success"] for r in self.results.values())
    
    def generate_report(self):
        """Generate comprehensive test report"""
        
        print("\n" + "="*60)
        print("TEST REPORT")
        print("="*60)
        
        duration = (self.end_time - self.start_time).total_seconds()
        
        print(f"\nTest Run Summary")
        print(f"  Started: {self.start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"  Ended: {self.end_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"  Duration: {duration:.2f} seconds")
        
        print(f"\nTest Results:")
        
        total_passed = 0
        total_failed = 0
        total_errors = 0
        total_skipped = 0
        
        for name, result in self.results.items():
            status = "✓" if result["success"] else "✗"
            print(f"\n{status} {name}")
            print(f"    Passed: {result['passed']}")
            print(f"    Failed: {result['failed']}")
            print(f"    Errors: {result['errors']}")
            print(f"    Skipped: {result['skipped']}")
            print(f"    Duration: {result['duration']:.2f}s")
            
            total_passed += result["passed"]
            total_failed += result["failed"]
            total_errors += result["errors"]
            total_skipped += result["skipped"]
        
        print(f"\nOverall Statistics:")
        print(f"  Total Passed: {total_passed}")
        print(f"  Total Failed: {total_failed}")
        print(f"  Total Errors: {total_errors}")
        print(f"  Total Skipped: {total_skipped}")
        
        success_rate = (total_passed / (total_passed + total_failed + total_errors) * 100) if (total_passed + total_failed + total_errors) > 0 else 0
        print(f"  Success Rate: {success_rate:.1f}%")
        
        # Save detailed report to file
        report_path = self.test_dir / f"test_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(report_path, 'w') as f:
            json.dump({
                "start_time": self.start_time.isoformat(),
                "end_time": self.end_time.isoformat(),
                "duration": duration,
                "results": self.results,
                "summary": {
                    "total_passed": total_passed,
                    "total_failed": total_failed,
                    "total_errors": total_errors,
                    "total_skipped": total_skipped,
                    "success_rate": success_rate
                }
            }, f, indent=2)
        
        print(f"\nDetailed report saved to: {report_path}")
        
        # Check for HTML reports
        html_reports = list(self.test_dir.glob("*.html"))
        if html_reports:
            print(f"\nHTML reports generated:")
            for report in html_reports:
                print(f"  - {report}")
    
    def run_specific_test(self, test_name: str):
        """Run a specific test suite"""
        
        test_files = {
            "functional": "test_mcp_server_functional.py",
            "ui": "test_gradio_ui_playwright.py",
            "integration": "test_mcp_clients.py",
            "inspector": "test_mcp_inspector_setup.py"
        }
        
        if test_name not in test_files:
            print(f"Unknown test: {test_name}")
            print(f"Available tests: {', '.join(test_files.keys())}")
            return False
        
        if test_name == "inspector":
            # Special handling for inspector
            subprocess.run([sys.executable, test_files[test_name]])
        else:
            # Run with pytest
            subprocess.run([
                sys.executable, "-m", "pytest",
                test_files[test_name],
                "-v", "--tb=short"
            ])


def main():
    """Main entry point"""
    
    runner = TestRunner()
    
    if len(sys.argv) > 1:
        # Run specific test
        test_name = sys.argv[1]
        runner.run_specific_test(test_name)
    else:
        # Run all tests
        success = runner.run_all_tests()
        
        if success:
            print("\n🎉 All tests passed!")
            return 0
        else:
            print("\n⚠️  Some tests failed. Please review the output above.")
            return 1


if __name__ == "__main__":
    sys.exit(main())
