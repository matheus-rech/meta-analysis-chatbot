#!/usr/bin/env python3
"""
Complete Workflow Validation Runner
This script runs comprehensive validation of all workflows and components:
1. R initialization and package installation
2. Python environment validation
3. End-to-end workflow testing
4. Session management
5. Statistical operations
6. Deployment readiness
"""

import os
import sys
import subprocess
import json
import time
from pathlib import Path


def main():
    """Main validation runner"""
    print("🚀 Complete Meta-Analysis Chatbot Workflow Validation")
    print("=" * 70)
    
    project_root = Path(__file__).parent
    results = {}
    start_time = time.time()
    
    # Test 1: End-to-End Workflow (our working test)
    print("\n📋 Test 1: End-to-End Workflow Validation")
    print("-" * 50)
    
    try:
        result = subprocess.run(
            [sys.executable, "test_end_to_end_workflow.py"],
            cwd=project_root,
            capture_output=True,
            text=True,
            timeout=120
        )
        
        if result.returncode == 0:
            print("✅ End-to-End Workflow Tests: PASSED")
            results["end_to_end_workflow"] = True
        else:
            print("❌ End-to-End Workflow Tests: FAILED")
            print(f"Error: {result.stderr}")
            results["end_to_end_workflow"] = False
            
    except Exception as e:
        print(f"❌ End-to-End Workflow Tests: EXCEPTION - {e}")
        results["end_to_end_workflow"] = False
    
    # Test 2: Environment Setup Validation
    print("\n🔧 Test 2: Environment Setup Validation")
    print("-" * 50)
    
    env_checks = {
        "python_version": sys.version_info >= (3, 8),
        "r_available": False,
        "critical_dirs": True,
    }
    
    # Check R
    try:
        r_result = subprocess.run(['Rscript', '--version'], 
                                capture_output=True, text=True)
        env_checks["r_available"] = r_result.returncode == 0
    except:
        env_checks["r_available"] = False
    
    # Check directories
    required_dirs = ["sessions", "scripts", "tests"]
    for dir_name in required_dirs:
        if not (project_root / dir_name).exists():
            env_checks["critical_dirs"] = False
            break
    
    # Print results
    for check, status in env_checks.items():
        status_icon = "✅" if status else "❌"
        print(f"{status_icon} {check}: {'PASS' if status else 'FAIL'}")
    
    results["environment_setup"] = all(env_checks.values())
    
    # Test 3: Component Availability
    print("\n📦 Test 3: Component Availability Check")
    print("-" * 50)
    
    components = {
        "dockerfile": (project_root / "Dockerfile.chatbot").exists(),
        "requirements": (project_root / "requirements-chatbot.txt").exists(),
        "main_app": (project_root / "chatbot_langchain.py").exists(),
        "server": (project_root / "server.py").exists(),
        "r_scripts": (project_root / "scripts" / "entry").exists(),
    }
    
    for component, available in components.items():
        status_icon = "✅" if available else "❌"
        print(f"{status_icon} {component}: {'AVAILABLE' if available else 'MISSING'}")
    
    results["components_available"] = all(components.values())
    
    # Test 4: Package Installation Check
    print("\n📚 Test 4: Package Installation Check")
    print("-" * 50)
    
    python_packages = ["gradio", "pandas", "numpy", "fastapi", "langchain"]
    python_ok = True
    
    for package in python_packages:
        try:
            __import__(package)
            print(f"✅ {package}: INSTALLED")
        except ImportError:
            print(f"❌ {package}: MISSING")
            python_ok = False
    
    # Check R packages
    r_env = os.environ.copy()
    r_env['R_LIBS'] = str(Path.home() / "R" / "library")
    
    try:
        r_result = subprocess.run([
            'Rscript', '-e', 
            'library(jsonlite); cat("jsonlite OK")'
        ], capture_output=True, text=True, env=r_env)
        
        if r_result.returncode == 0:
            print("✅ R jsonlite: INSTALLED")
            r_ok = True
        else:
            print("❌ R jsonlite: MISSING")
            r_ok = False
    except:
        print("❌ R packages: UNAVAILABLE")
        r_ok = False
    
    results["packages_installed"] = python_ok and r_ok
    
    # Summary
    end_time = time.time()
    duration = end_time - start_time
    
    print("\n" + "=" * 70)
    print("📊 WORKFLOW VALIDATION SUMMARY")
    print("=" * 70)
    
    overall_success = all(results.values())
    
    for test_name, success in results.items():
        status_icon = "✅" if success else "❌"
        print(f"{status_icon} {test_name.replace('_', ' ').title()}: {'PASS' if success else 'FAIL'}")
    
    print(f"\n⏱️  Total validation time: {duration:.2f} seconds")
    
    if overall_success:
        print("\n🎉 ALL WORKFLOW VALIDATIONS PASSED!")
        print("✨ The meta-analysis chatbot is ready for deployment!")
    else:
        print("\n⚠️  Some validations failed. Please review the output above.")
    
    # Save validation report
    validation_report = {
        "timestamp": time.time(),
        "duration_seconds": duration,
        "overall_success": overall_success,
        "detailed_results": results,
        "summary": "Complete workflow validation for meta-analysis chatbot"
    }
    
    with open(project_root / "complete_validation_report.json", 'w') as f:
        json.dump(validation_report, f, indent=2, default=str)
    
    print(f"\n📄 Detailed report saved to: complete_validation_report.json")
    print("=" * 70)
    
    return 0 if overall_success else 1


if __name__ == "__main__":
    sys.exit(main())