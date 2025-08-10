#!/usr/bin/env python3
"""
Initialize Enhanced Environment for Meta-Analysis Chatbot
Sets up all necessary configurations for background agents and enhanced capabilities
"""

import os
import sys
import json
import yaml
import subprocess
import shutil
from pathlib import Path
from typing import Dict, List, Any
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class EnvironmentInitializer:
    """Initialize and configure the enhanced environment"""
    
    def __init__(self):
        self.project_root = Path(__file__).parent.parent
        self.config_dir = self.project_root / "config"
        self.scripts_dir = self.project_root / "scripts"
        self.tests_dir = self.project_root / "tests"
        
    def create_directories(self):
        """Create necessary directories"""
        directories = [
            "config",
            "sessions",
            "logs",
            "metrics",
            "profiles",
            "docs",
            "cache",
            ".cursor",
            ".vscode"
        ]
        
        for dir_name in directories:
            dir_path = self.project_root / dir_name
            dir_path.mkdir(exist_ok=True)
            logger.info(f"✓ Created directory: {dir_path}")
    
    def setup_environment_variables(self):
        """Set up environment variables"""
        env_vars = {
            "PYTHONPATH": str(self.project_root),
            "PYTHONUNBUFFERED": "1",
            "DEBUG_R": "1",
            "GRADIO_MCP_SERVER": "true",
            "ENABLE_BACKGROUND_AGENTS": "true",
            "COCHRANE_ENHANCED_MODE": "true",
            "SESSIONS_DIR": str(self.project_root / "sessions"),
            "LOG_DIR": str(self.project_root / "logs"),
            "METRICS_DIR": str(self.project_root / "metrics")
        }
        
        # Create .env file if it doesn't exist
        env_file = self.project_root / ".env"
        if not env_file.exists():
            with open(env_file, 'w') as f:
                for key, value in env_vars.items():
                    f.write(f"{key}={value}\n")
            logger.info(f"✓ Created .env file with environment variables")
        else:
            logger.info("✓ .env file already exists")
        
        # Export variables to current session
        for key, value in env_vars.items():
            os.environ[key] = value
    
    def install_dependencies(self):
        """Install Python and R dependencies"""
        logger.info("Installing dependencies...")
        
        # Python dependencies
        try:
            subprocess.run([
                sys.executable, "-m", "pip", "install", "-r", 
                str(self.project_root / "requirements-chatbot.txt")
            ], check=True)
            logger.info("✓ Installed Python dependencies")
        except subprocess.CalledProcessError as e:
            logger.error(f"✗ Failed to install Python dependencies: {e}")
        
        # Test dependencies
        try:
            subprocess.run([
                sys.executable, "-m", "pip", "install", "-r",
                str(self.tests_dir / "requirements-test.txt")
            ], check=True)
            logger.info("✓ Installed test dependencies")
        except subprocess.CalledProcessError as e:
            logger.warning(f"⚠ Failed to install test dependencies: {e}")
        
        # R dependencies
        r_script = """
        packages <- c("meta", "metafor", "jsonlite", "ggplot2", "rmarkdown", "knitr", "base64enc")
        for (pkg in packages) {
            if (!pkg %in% installed.packages()[,"Package"]) {
                install.packages(pkg, repos="https://cloud.r-project.org", quiet=TRUE)
                cat(paste("Installed:", pkg, "\n"))
            } else {
                cat(paste("Already installed:", pkg, "\n"))
            }
        }
        """
        
        try:
            result = subprocess.run(
                ["Rscript", "-e", r_script],
                capture_output=True,
                text=True
            )
            if result.returncode == 0:
                logger.info("✓ R packages verified/installed")
            else:
                logger.warning(f"⚠ R package installation had issues: {result.stderr}")
        except FileNotFoundError:
            logger.error("✗ R is not installed. Please install R first.")
    
    def setup_agent_configuration(self):
        """Set up agent configuration files"""
        # Agent configuration is already created
        config_file = self.config_dir / "agent-environment.yaml"
        if config_file.exists():
            logger.info(f"✓ Agent configuration found: {config_file}")
        else:
            logger.warning("⚠ Agent configuration not found")
    
    def setup_vscode_configuration(self):
        """Set up VS Code configuration"""
        vscode_dir = self.project_root / ".vscode"
        settings_file = vscode_dir / "settings.json"
        
        if settings_file.exists():
            logger.info(f"✓ VS Code settings configured: {settings_file}")
        else:
            logger.warning("⚠ VS Code settings not found")
        
        # Create launch configuration for debugging
        launch_config = {
            "version": "0.2.0",
            "configurations": [
                {
                    "name": "Python: Gradio App",
                    "type": "python",
                    "request": "launch",
                    "program": "${workspaceFolder}/gradio_native_mcp.py",
                    "console": "integratedTerminal",
                    "env": {
                        "DEBUG_R": "1",
                        "GRADIO_MCP_SERVER": "true"
                    }
                },
                {
                    "name": "Python: MCP Server",
                    "type": "python",
                    "request": "launch",
                    "program": "${workspaceFolder}/server.py",
                    "console": "integratedTerminal",
                    "env": {
                        "DEBUG_R": "1"
                    }
                },
                {
                    "name": "Python: Run Tests",
                    "type": "python",
                    "request": "launch",
                    "module": "pytest",
                    "args": ["tests", "-v"],
                    "console": "integratedTerminal"
                },
                {
                    "name": "Python: Agent Manager",
                    "type": "python",
                    "request": "launch",
                    "program": "${workspaceFolder}/scripts/agent_manager.py",
                    "console": "integratedTerminal"
                }
            ]
        }
        
        launch_file = vscode_dir / "launch.json"
        with open(launch_file, 'w') as f:
            json.dump(launch_config, f, indent=2)
        logger.info(f"✓ Created VS Code launch configuration")
    
    def setup_cursor_configuration(self):
        """Set up Cursor-specific configuration"""
        cursor_dir = self.project_root / ".cursor"
        cursor_dir.mkdir(exist_ok=True)
        
        # Environment configuration is already set
        env_file = cursor_dir / "environment.json"
        if env_file.exists():
            logger.info(f"✓ Cursor environment configured: {env_file}")
        
        # Rules directory should exist
        rules_dir = cursor_dir / "rules"
        if rules_dir.exists() and list(rules_dir.glob("*.mdc")):
            logger.info(f"✓ Cursor rules configured: {len(list(rules_dir.glob('*.mdc')))} rules found")
    
    def verify_r_environment(self):
        """Verify R environment is properly configured"""
        try:
            # Check R version
            result = subprocess.run(
                ["Rscript", "--version"],
                capture_output=True,
                text=True
            )
            if result.returncode == 0:
                logger.info("✓ R is installed and accessible")
            
            # Test R script execution
            test_script = """
            library(jsonlite)
            cat(toJSON(list(status="success", message="R environment verified")))
            """
            
            result = subprocess.run(
                ["Rscript", "-e", test_script],
                capture_output=True,
                text=True
            )
            
            if result.returncode == 0 and "success" in result.stdout:
                logger.info("✓ R environment is properly configured")
            else:
                logger.warning("⚠ R environment may have issues")
                
        except FileNotFoundError:
            logger.error("✗ R is not installed or not in PATH")
    
    def start_background_agents(self):
        """Start the agent manager"""
        logger.info("Starting background agents...")
        
        agent_manager_path = self.scripts_dir / "agent_manager.py"
        if agent_manager_path.exists():
            try:
                # Start in background
                process = subprocess.Popen(
                    [sys.executable, str(agent_manager_path)],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    start_new_session=True
                )
                logger.info(f"✓ Agent manager started (PID: {process.pid})")
                
                # Save PID for later management
                pid_file = self.project_root / ".agent_manager.pid"
                with open(pid_file, 'w') as f:
                    f.write(str(process.pid))
                    
            except Exception as e:
                logger.error(f"✗ Failed to start agent manager: {e}")
        else:
            logger.warning("⚠ Agent manager script not found")
    
    def generate_status_report(self):
        """Generate a status report of the environment"""
        report = {
            "timestamp": os.popen("date").read().strip(),
            "python_version": sys.version,
            "project_root": str(self.project_root),
            "environment_variables": {
                "PYTHONPATH": os.getenv("PYTHONPATH"),
                "DEBUG_R": os.getenv("DEBUG_R"),
                "GRADIO_MCP_SERVER": os.getenv("GRADIO_MCP_SERVER"),
                "ENABLE_BACKGROUND_AGENTS": os.getenv("ENABLE_BACKGROUND_AGENTS")
            },
            "directories": {
                "config": self.config_dir.exists(),
                "sessions": (self.project_root / "sessions").exists(),
                "logs": (self.project_root / "logs").exists(),
                "metrics": (self.project_root / "metrics").exists()
            },
            "configurations": {
                "cursor_env": (self.project_root / ".cursor/environment.json").exists(),
                "agent_config": (self.config_dir / "agent-environment.yaml").exists(),
                "vscode_settings": (self.project_root / ".vscode/settings.json").exists()
            }
        }
        
        # Save report
        report_file = self.project_root / "environment_status.json"
        with open(report_file, 'w') as f:
            json.dump(report, f, indent=2)
        
        logger.info(f"✓ Environment status report saved to: {report_file}")
        
        # Print summary
        print("\n" + "="*60)
        print("ENVIRONMENT INITIALIZATION COMPLETE")
        print("="*60)
        print(f"Project Root: {self.project_root}")
        print(f"Python Version: {sys.version.split()[0]}")
        print("\nConfigurations:")
        for name, exists in report["configurations"].items():
            status = "✓" if exists else "✗"
            print(f"  {status} {name}")
        print("\nNext Steps:")
        print("  1. Start Gradio app: python gradio_native_mcp.py")
        print("  2. Run tests: python tests/run_all_tests.py")
        print("  3. Start MCP Inspector: python tests/test_mcp_inspector_setup.py")
        print("="*60)
    
    def initialize(self):
        """Run full initialization"""
        logger.info("Initializing enhanced environment for Meta-Analysis Chatbot...")
        
        self.create_directories()
        self.setup_environment_variables()
        self.install_dependencies()
        self.setup_agent_configuration()
        self.setup_vscode_configuration()
        self.setup_cursor_configuration()
        self.verify_r_environment()
        # Optionally start agents (commented out by default)
        # self.start_background_agents()
        self.generate_status_report()
        
        logger.info("✓ Environment initialization complete!")


def main():
    """Main entry point"""
    initializer = EnvironmentInitializer()
    
    try:
        initializer.initialize()
        return 0
    except Exception as e:
        logger.error(f"Initialization failed: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
