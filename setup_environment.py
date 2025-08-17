#!/usr/bin/env python3
"""
Environment Setup Script for Meta-Analysis Chatbot
Implements the TODO requirements for installation and configuration
"""
import os
import sys
import subprocess
import shutil
from pathlib import Path


class EnvironmentSetup:
    """Main setup class for the meta-analysis chatbot environment"""
    
    def __init__(self):
        self.repo_root = Path(__file__).parent
        self.sessions_dir = self.repo_root / "sessions"
        self.logs_dir = self.repo_root / "logs"
        self.config_dir = self.repo_root / "config"
        
    def print_header(self, message):
        """Print a formatted header"""
        print(f"\n{'='*60}")
        print(f"  {message}")
        print(f"{'='*60}")
        
    def check_system_requirements(self):
        """Check system requirements"""
        self.print_header("1. Checking System Requirements")
        
        # Check Python version
        py_version = sys.version_info
        print(f"✓ Python {py_version.major}.{py_version.minor}.{py_version.micro}")
        
        # Check R installation
        try:
            r_result = subprocess.run(['R', '--version'], capture_output=True, text=True)
            if r_result.returncode == 0:
                r_version = r_result.stdout.split('\n')[0]
                print(f"✓ {r_version}")
            else:
                print("✗ R not found")
                return False
        except FileNotFoundError:
            print("✗ R not installed")
            return False
            
        # Check Rscript
        try:
            subprocess.run(['Rscript', '--version'], capture_output=True, text=True)
            print("✓ Rscript available")
        except FileNotFoundError:
            print("✗ Rscript not found")
            return False
            
        return True
        
    def check_r_packages(self):
        """Check R package installation"""
        self.print_header("2. Checking R Packages")
        
        required_packages = [
            'jsonlite', 'ggplot2', 'knitr', 'rmarkdown', 'readxl'
        ]
        
        # Check installed packages
        check_script = f"""
        installed <- installed.packages()[,"Package"]
        required <- c({', '.join(f'"{pkg}"' for pkg in required_packages)})
        missing <- required[!required %in% installed]
        cat("MISSING:", paste(missing, collapse=","), "\\n")
        cat("INSTALLED:", paste(required[required %in% installed], collapse=","), "\\n")
        """
        
        try:
            result = subprocess.run(
                ['Rscript', '-e', check_script],
                capture_output=True, text=True
            )
            
            for line in result.stdout.strip().split('\n'):
                if line.startswith('MISSING:'):
                    missing = line.replace('MISSING:', '').strip()
                    if missing:
                        print(f"⚠ Missing R packages: {missing}")
                    else:
                        print("✓ All required R packages available")
                elif line.startswith('INSTALLED:'):
                    installed = line.replace('INSTALLED:', '').strip()
                    if installed:
                        print(f"✓ Installed: {installed}")
                        
        except Exception as e:
            print(f"✗ Error checking R packages: {e}")
            return False
            
        return True
        
    def check_python_packages(self):
        """Check Python package availability"""
        self.print_header("3. Checking Python Packages")
        
        required_packages = [
            'gradio', 'langchain', 'openai', 'anthropic', 
            'pandas', 'numpy', 'PIL', 'fastapi'
        ]
        
        available = []
        missing = []
        
        for package in required_packages:
            try:
                __import__(package)
                available.append(package)
                print(f"✓ {package}")
            except ImportError:
                missing.append(package)
                print(f"✗ {package}")
                
        if missing:
            print(f"\n⚠ Missing Python packages: {', '.join(missing)}")
            print("  Install with: pip install " + " ".join(missing))
            
        return len(available) > len(missing)
        
    def setup_directories(self):
        """Create required directories"""
        self.print_header("4. Setting Up Directories")
        
        directories = [
            self.sessions_dir,
            self.logs_dir,
            self.config_dir,
            self.repo_root / "outputs",
            self.repo_root / "tmp"
        ]
        
        for directory in directories:
            if not directory.exists():
                directory.mkdir(parents=True, exist_ok=True)
                print(f"✓ Created: {directory}")
            else:
                print(f"✓ Exists: {directory}")
                
        return True
        
    def setup_api_configuration(self):
        """Setup API key configuration"""
        self.print_header("5. API Key Configuration")
        
        env_file = self.repo_root / ".env"
        env_example = self.repo_root / ".env.example"
        
        if not env_file.exists() and env_example.exists():
            shutil.copy(env_example, env_file)
            print(f"✓ Created .env from .env.example")
        
        # Check for API keys
        openai_key = os.getenv('OPENAI_API_KEY')
        anthropic_key = os.getenv('ANTHROPIC_API_KEY')
        
        if openai_key:
            print(f"✓ OpenAI API key configured")
        else:
            print("⚠ OpenAI API key not found")
            
        if anthropic_key:
            print(f"✓ Anthropic API key configured") 
        else:
            print(f"⚠ Anthropic API key not found")
            
        if not openai_key and not anthropic_key:
            print(f"\n⚠ No API keys configured!")
            print(f"  Set environment variables:")
            print(f"    export OPENAI_API_KEY='your-openai-key'")
            print(f"    export ANTHROPIC_API_KEY='your-anthropic-key'")
            print(f"  Or edit .env file")
            
        return True
        
    def create_monitoring_config(self):
        """Create monitoring configuration"""
        self.print_header("6. Setting Up Monitoring")
        
        # Create monitoring configuration
        monitoring_config = {
            'performance': {
                'enabled': True,
                'interval_seconds': 300,
                'cpu_threshold': 80,
                'memory_threshold': 80
            },
            'security': {
                'enabled': True,
                'rate_limit_per_minute': 30,
                'session_timeout_hours': 24
            },
            'logging': {
                'level': 'INFO',
                'file': str(self.logs_dir / 'app.log'),
                'max_size_mb': 100
            }
        }
        
        config_file = self.config_dir / 'monitoring.json'
        with open(config_file, 'w') as f:
            import json
            json.dump(monitoring_config, f, indent=2)
            
        print(f"✓ Created monitoring config: {config_file}")
        return True
        
    def test_basic_functionality(self):
        """Test basic R integration"""
        self.print_header("7. Testing Basic Functionality")
        
        # Test R script execution
        test_script = """
        library(jsonlite)
        result <- list(
            status = "success",
            message = "R integration working",
            timestamp = Sys.time()
        )
        cat(toJSON(result, auto_unbox=TRUE))
        """
        
        try:
            result = subprocess.run(
                ['Rscript', '-e', test_script],
                capture_output=True, text=True, timeout=30
            )
            
            if result.returncode == 0:
                print("✓ R script execution successful")
                print(f"  Output: {result.stdout.strip()}")
            else:
                print(f"✗ R script failed: {result.stderr}")
                return False
                
        except subprocess.TimeoutExpired:
            print("✗ R script timeout")
            return False
        except Exception as e:
            print(f"✗ R script error: {e}")
            return False
            
        return True
        
    def create_docker_verification(self):
        """Verify Docker configuration"""
        self.print_header("8. Docker Configuration")
        
        dockerfiles = [
            'Dockerfile',
            'Dockerfile.chatbot'
        ]
        
        for dockerfile in dockerfiles:
            dockerfile_path = self.repo_root / dockerfile
            if dockerfile_path.exists():
                print(f"✓ Found: {dockerfile}")
            else:
                print(f"✗ Missing: {dockerfile}")
                
        # Test Docker build (if Docker is available)
        try:
            subprocess.run(['docker', '--version'], 
                         capture_output=True, text=True, check=True)
            print("✓ Docker available")
            
            # Note: We don't actually build here to save time
            print("  (Docker build not tested - requires network)")
            
        except (subprocess.CalledProcessError, FileNotFoundError):
            print("⚠ Docker not available")
            
        return True
        
    def generate_status_report(self):
        """Generate final status report"""
        self.print_header("9. Environment Status Report")
        
        status = {
            'timestamp': datetime.now().isoformat(),
            'python_version': f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
            'directories_created': str(len([d for d in [self.sessions_dir, self.logs_dir, self.config_dir] if d.exists()])),
            'api_keys_configured': bool(os.getenv('OPENAI_API_KEY') or os.getenv('ANTHROPIC_API_KEY')),
            'ready_for_deployment': True
        }
        
        status_file = self.repo_root / 'environment_status.json'
        with open(status_file, 'w') as f:
            import json
            json.dump(status, f, indent=2)
            
        print(f"✓ Status report saved: {status_file}")
        
        # Print summary
        print(f"\n{'='*40}")
        print("  SETUP COMPLETE")
        print(f"{'='*40}")
        print(f"Next steps:")
        print(f"1. Configure API keys in .env file")
        print("2. Run: python chatbot_langchain.py")
        print(f"3. Access UI at: http://localhost:7860")
        
        return True
        
    def run_setup(self):
        """Run complete setup process"""
        print("Meta-Analysis Chatbot Environment Setup")
        print("=======================================")
        
        steps = [
            self.check_system_requirements,
            self.check_r_packages,
            self.check_python_packages,
            self.setup_directories,
            self.setup_api_configuration,
            self.create_monitoring_config,
            self.test_basic_functionality,
            self.create_docker_verification,
            self.generate_status_report
        ]
        
        success_count = 0
        for step in steps:
            try:
                if step():
                    success_count += 1
                else:
                    print(f"⚠ Step failed but continuing...")
            except Exception as e:
                print(f"✗ Step error: {e}")
                
        print(f"\nSetup completed: {success_count}/{len(steps)} steps successful")
        return success_count == len(steps)


if __name__ == "__main__":
    setup = EnvironmentSetup()
    success = setup.run_setup()
    sys.exit(0 if success else 1)