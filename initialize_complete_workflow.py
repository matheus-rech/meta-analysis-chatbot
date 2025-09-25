#!/usr/bin/env python3
"""
Complete Workflow Initialization and Testing Script
Creates and validates end-to-end workflows for the meta-analysis chatbot:
- R environment setup and package installation
- Python environment validation
- Session management system
- Health check endpoints
- Deployment readiness checks
"""

import os
import sys
import json
import subprocess
import uuid
import time
from pathlib import Path


class WorkflowInitializer:
    """Complete workflow initialization and validation"""
    
    def __init__(self):
        self.project_root = Path(__file__).parent
        self.r_lib_path = Path.home() / "R" / "library"
        self.results = {}
        
    def log(self, message: str, level: str = "INFO"):
        """Log message with timestamp"""
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{timestamp}] {level}: {message}")
        
    def run_r_command(self, r_code: str) -> dict:
        """Execute R code and return results"""
        env = os.environ.copy()
        env['R_LIBS'] = str(self.r_lib_path)
        
        try:
            result = subprocess.run(
                ['Rscript', '-e', r_code],
                capture_output=True,
                text=True,
                env=env,
                timeout=120
            )
            
            return {
                "success": result.returncode == 0,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "returncode": result.returncode
            }
            
        except Exception as e:
            return {
                "success": False,
                "stdout": "",
                "stderr": str(e),
                "returncode": -1
            }
    
    def stage_1_environment_check(self) -> bool:
        """Check system environment"""
        self.log("🔍 Stage 1: Environment Check")
        
        # Check Python version
        py_version = sys.version_info
        if py_version.major == 3 and py_version.minor >= 8:
            self.log(f"✅ Python {py_version.major}.{py_version.minor}.{py_version.micro}")
        else:
            self.log(f"❌ Python {py_version.major}.{py_version.minor} (need 3.8+)")
            return False
        
        # Check R availability
        r_result = self.run_r_command("cat('R is available')")
        if r_result["success"]:
            self.log("✅ R is available")
        else:
            self.log(f"❌ R not available: {r_result['stderr']}")
            return False
            
        return True
    
    def stage_2_r_packages(self) -> bool:
        """Ensure R packages are installed"""
        self.log("📦 Stage 2: R Package Setup")
        
        # Check and install jsonlite
        check_install_code = f"""
        .libPaths('{self.r_lib_path}')
        
        if (!'jsonlite' %in% installed.packages()[,'Package']) {{
            install.packages('jsonlite', repos='https://cran.r-project.org', lib='{self.r_lib_path}')
        }}
        
        if (!'base64enc' %in% installed.packages()[,'Package']) {{
            install.packages('base64enc', repos='https://cran.r-project.org', lib='{self.r_lib_path}')
        }}
        
        library(jsonlite)
        
        result <- list(
            status = 'success',
            packages = installed.packages()[,'Package']
        )
        
        cat(toJSON(result, auto_unbox = TRUE))
        """
        
        result = self.run_r_command(check_install_code)
        if result["success"]:
            try:
                response = json.loads(result["stdout"])
                self.log("✅ R packages available")
                return True
            except json.JSONDecodeError:
                self.log(f"❌ Failed to parse R output: {result['stdout']}")
                return False
        else:
            self.log(f"❌ R package setup failed: {result['stderr']}")
            return False
    
    def stage_3_python_environment(self) -> bool:
        """Verify Python environment"""
        self.log("🐍 Stage 3: Python Environment Check")
        
        critical_packages = ['gradio', 'pandas', 'numpy', 'pytest']
        missing = []
        
        for package in critical_packages:
            try:
                __import__(package)
                self.log(f"✅ {package}")
            except ImportError:
                self.log(f"❌ {package} missing")
                missing.append(package)
        
        if missing:
            self.log(f"Missing packages: {missing}")
            return False
        
        return True
    
    def stage_4_session_management(self) -> bool:
        """Test session management system"""
        self.log("📁 Stage 4: Session Management Test")
        
        # Create session directory structure
        sessions_dir = self.project_root / "sessions"
        sessions_dir.mkdir(exist_ok=True)
        
        test_session_id = str(uuid.uuid4())
        session_path = sessions_dir / test_session_id
        
        try:
            session_path.mkdir()
            
            # Create subdirectories
            for subdir in ['input', 'processing', 'results', 'tmp']:
                (session_path / subdir).mkdir()
            
            # Create session metadata
            session_metadata = {
                'session_id': test_session_id,
                'created_at': time.time(),
                'status': 'test'
            }
            
            with open(session_path / 'session.json', 'w') as f:
                json.dump(session_metadata, f)
            
            # Verify session creation
            if (session_path / 'session.json').exists():
                self.log("✅ Session management working")
                
                # Cleanup
                import shutil
                shutil.rmtree(session_path)
                return True
            else:
                self.log("❌ Session creation failed")
                return False
                
        except Exception as e:
            self.log(f"❌ Session management error: {e}")
            return False
    
    def stage_5_r_integration(self) -> bool:
        """Test Python-R integration"""
        self.log("🌉 Stage 5: Python-R Integration Test")
        
        test_data = {"numbers": [1, 2, 3, 4, 5], "message": "test"}
        
        integration_code = f"""
        .libPaths('{self.r_lib_path}')
        library(jsonlite)
        
        # Simulate receiving data from Python
        test_data <- fromJSON('{json.dumps(test_data)}')
        
        # Process data
        sum_numbers <- sum(test_data$numbers)
        mean_numbers <- mean(test_data$numbers)
        
        # Return results
        result <- list(
            status = 'success',
            sum = sum_numbers,
            mean = mean_numbers,
            message_received = test_data$message,
            r_timestamp = Sys.time()
        )
        
        cat(toJSON(result, auto_unbox = TRUE))
        """
        
        result = self.run_r_command(integration_code)
        if result["success"]:
            try:
                response = json.loads(result["stdout"])
                if response.get("status") == "success":
                    self.log("✅ Python-R integration working")
                    return True
                else:
                    self.log(f"❌ Integration test failed: {response}")
                    return False
            except json.JSONDecodeError:
                self.log(f"❌ Failed to parse integration output: {result['stdout']}")
                return False
        else:
            self.log(f"❌ Integration test failed: {result['stderr']}")
            return False
    
    def stage_6_health_checks(self) -> bool:
        """Test health check functionality"""
        self.log("🔍 Stage 6: Health Check Tests")
        
        health_check_code = f"""
        .libPaths('{self.r_lib_path}')
        
        # Basic health check
        health_status <- list(
            status = 'healthy',
            timestamp = Sys.time(),
            r_version = R.version.string,
            available_packages = length(installed.packages()[,'Package'])
        )
        
        # Try to use jsonlite if available
        if ('jsonlite' %in% installed.packages()[,'Package']) {{
            library(jsonlite)
            cat(toJSON(health_status, auto_unbox = TRUE))
        }} else {{
            cat('{"status":"healthy","r_working":true}')
        }}
        """
        
        result = self.run_r_command(health_check_code)
        if result["success"]:
            try:
                response = json.loads(result["stdout"])
                if response.get("status") == "healthy":
                    self.log("✅ Health checks working")
                    return True
                else:
                    self.log(f"❌ Health check failed: {response}")
                    return False
            except json.JSONDecodeError:
                self.log(f"❌ Failed to parse health check output: {result['stdout']}")
                return False
        else:
            self.log(f"❌ Health check failed: {result['stderr']}")
            return False
    
    def stage_7_deployment_check(self) -> bool:
        """Check deployment readiness"""
        self.log("🚀 Stage 7: Deployment Readiness Check")
        
        checks = {
            "dockerfiles": False,
            "requirements": False,
            "entry_points": False
        }
        
        # Check for Dockerfiles
        dockerfiles = ['Dockerfile.chatbot', 'Dockerfile.production']
        for dockerfile in dockerfiles:
            if (self.project_root / dockerfile).exists():
                self.log(f"✅ {dockerfile} found")
                checks["dockerfiles"] = True
                break
        
        # Check requirements files
        req_files = ['requirements-chatbot.txt', 'requirements.txt']
        for req_file in req_files:
            if (self.project_root / req_file).exists():
                self.log(f"✅ {req_file} found")
                checks["requirements"] = True
                break
        
        # Check entry points
        entry_points = ['chatbot_langchain.py', 'app.py']
        for entry_point in entry_points:
            if (self.project_root / entry_point).exists():
                self.log(f"✅ {entry_point} found")
                checks["entry_points"] = True
                break
        
        success = all(checks.values())
        if success:
            self.log("✅ Deployment ready")
        else:
            self.log(f"❌ Deployment checks failed: {checks}")
        
        return success
    
    def run_complete_workflow(self) -> bool:
        """Execute complete workflow"""
        self.log("🚀 Starting Complete Workflow Initialization")
        self.log("=" * 60)
        
        stages = [
            ("Environment Check", self.stage_1_environment_check),
            ("R Package Setup", self.stage_2_r_packages),
            ("Python Environment", self.stage_3_python_environment),
            ("Session Management", self.stage_4_session_management),
            ("Python-R Integration", self.stage_5_r_integration),
            ("Health Checks", self.stage_6_health_checks),
            ("Deployment Readiness", self.stage_7_deployment_check)
        ]
        
        results = {}
        overall_success = True
        
        for stage_name, stage_func in stages:
            self.log(f"\n▶️ Starting: {stage_name}")
            try:
                success = stage_func()
                results[stage_name] = success
                if success:
                    self.log(f"✅ {stage_name} completed")
                else:
                    self.log(f"❌ {stage_name} failed")
                    overall_success = False
            except Exception as e:
                self.log(f"❌ {stage_name} exception: {e}")
                results[stage_name] = False
                overall_success = False
        
        # Save results
        self.results = {
            "timestamp": time.time(),
            "overall_success": overall_success,
            "stage_results": results
        }
        
        # Save report
        with open(self.project_root / "workflow_initialization_report.json", 'w') as f:
            json.dump(self.results, f, indent=2, default=str)
        
        self.log("\n" + "=" * 60)
        if overall_success:
            self.log("🎉 Complete Workflow Initialization SUCCESSFUL!")
        else:
            self.log("❌ Workflow Initialization FAILED")
        self.log("=" * 60)
        
        return overall_success


def main():
    """Main entry point"""
    initializer = WorkflowInitializer()
    success = initializer.run_complete_workflow()
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())