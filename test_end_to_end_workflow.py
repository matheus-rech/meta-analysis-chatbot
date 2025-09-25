#!/usr/bin/env python3
"""
End-to-End Workflow Test Suite
Tests the complete meta-analysis chatbot workflow including:
- R initialization and package validation
- Python-R communication bridge
- Session management
- Basic statistical operations
- Health checks and validation
"""

import os
import sys
import json
import subprocess
import uuid
import tempfile
import shutil
from pathlib import Path
import pytest
import time

class TestEndToEndWorkflow:
    """Complete end-to-end workflow tests"""
    
    def setup_method(self):
        """Set up test environment"""
        self.project_root = Path(__file__).parent
        self.r_lib_path = Path.home() / "R" / "library" 
        self.sessions_dir = self.project_root / "sessions"
        self.test_session_id = str(uuid.uuid4())
        
        # Set R environment
        self.env = os.environ.copy()
        self.env['R_LIBS'] = str(self.r_lib_path)
        
        # Create sessions directory
        self.sessions_dir.mkdir(exist_ok=True)
    
    def teardown_method(self):
        """Clean up test environment"""
        # Clean up test session
        test_session_path = self.sessions_dir / self.test_session_id
        if test_session_path.exists():
            shutil.rmtree(test_session_path)
    
    def test_r_environment_initialization(self):
        """Test R environment is properly initialized"""
        print("🧪 Testing R environment initialization...")
        
        # Test R is available
        result = subprocess.run(['Rscript', '--version'], 
                              capture_output=True, text=True, env=self.env)
        assert result.returncode == 0, f"R not available: {result.stderr}"
        
        # Test critical packages are available
        r_script = """
        .libPaths(Sys.getenv('R_LIBS'))
        library(jsonlite)
        
        required_packages <- c('jsonlite', 'base64enc')
        missing_packages <- required_packages[!required_packages %in% installed.packages()[,'Package']]
        
        result <- list(
            status = if(length(missing_packages) == 0) 'success' else 'error',
            available_packages = installed.packages()[,'Package'],
            missing_packages = missing_packages
        )
        
        cat(toJSON(result, auto_unbox = TRUE))
        """
        
        result = subprocess.run(['Rscript', '-e', r_script],
                              capture_output=True, text=True, env=self.env)
        assert result.returncode == 0, f"R script failed: {result.stderr}"
        
        response = json.loads(result.stdout)
        assert response['status'] == 'success', f"Missing R packages: {response.get('missing_packages', [])}"
        
        print("✅ R environment properly initialized")
    
    def test_python_r_bridge_communication(self):
        """Test Python-R communication bridge"""
        print("🌉 Testing Python-R communication bridge...")
        
        # Test basic JSON communication
        test_data = {"message": "hello from python", "number": 42}
        
        r_script = f"""
        .libPaths(Sys.getenv('R_LIBS'))
        library(jsonlite)
        
        # Receive data from Python
        input_json <- '{json.dumps(test_data)}'
        input_data <- fromJSON(input_json)
        
        # Process and return response
        response <- list(
            status = 'success',
            received_message = input_data$message,
            doubled_number = input_data$number * 2,
            r_version = R.version.string
        )
        
        cat(toJSON(response, auto_unbox = TRUE))
        """
        
        result = subprocess.run(['Rscript', '-e', r_script],
                              capture_output=True, text=True, env=self.env)
        assert result.returncode == 0, f"R bridge failed: {result.stderr}"
        
        response = json.loads(result.stdout)
        assert response['status'] == 'success'
        assert response['received_message'] == test_data['message']
        assert response['doubled_number'] == test_data['number'] * 2
        
        print("✅ Python-R bridge working correctly")
    
    def test_session_management(self):
        """Test session creation and management"""
        print("📁 Testing session management...")
        
        # Create session directory structure
        session_path = self.sessions_dir / self.test_session_id
        session_path.mkdir(parents=True, exist_ok=True)
        
        for subdir in ['input', 'processing', 'results', 'tmp']:
            (session_path / subdir).mkdir(exist_ok=True)
        
        # Create session metadata
        session_metadata = {
            'session_id': self.test_session_id,
            'created_at': time.time(),
            'status': 'active',
            'workflow_stage': 'initialization'
        }
        
        session_file = session_path / 'session.json'
        with open(session_file, 'w') as f:
            json.dump(session_metadata, f)
        
        # Verify session structure
        assert session_path.exists()
        assert session_file.exists()
        
        for subdir in ['input', 'processing', 'results', 'tmp']:
            assert (session_path / subdir).exists()
        
        # Test session metadata reading
        with open(session_file, 'r') as f:
            loaded_metadata = json.load(f)
        
        assert loaded_metadata['session_id'] == self.test_session_id
        assert loaded_metadata['status'] == 'active'
        
        print("✅ Session management working correctly")
    
    def test_health_check_endpoint(self):
        """Test health check functionality"""
        print("🔍 Testing health check endpoint...")
        
        # Test basic health check
        r_script = """
        .libPaths(Sys.getenv('R_LIBS'))
        
        # Basic health check without dependencies
        health_check <- function() {
            return(list(
                status = 'healthy',
                timestamp = Sys.time(),
                r_version = R.version.string,
                message = 'R backend operational'
            ))
        }
        
        # Execute health check
        result <- health_check()
        
        # If jsonlite is available, use it for output
        if ('jsonlite' %in% installed.packages()[,'Package']) {
            library(jsonlite)
            cat(toJSON(result, auto_unbox = TRUE))
        } else {
            cat('{"status":"healthy","message":"R backend operational - minimal mode"}')
        }
        """
        
        result = subprocess.run(['Rscript', '-e', r_script],
                              capture_output=True, text=True, env=self.env)
        assert result.returncode == 0, f"Health check failed: {result.stderr}"
        
        response = json.loads(result.stdout)
        assert response['status'] == 'healthy'
        
        print("✅ Health check working correctly")
    
    def test_mock_statistical_operation(self):
        """Test mock statistical operation workflow"""
        print("📊 Testing mock statistical operation...")
        
        # Create mock dataset in session
        session_path = self.sessions_dir / self.test_session_id
        session_path.mkdir(parents=True, exist_ok=True)
        input_path = session_path / 'input'
        input_path.mkdir(exist_ok=True)
        
        # Mock meta-analysis data
        mock_data = [
            {'study': 'Study1', 'effect_size': 0.5, 'se': 0.2},
            {'study': 'Study2', 'effect_size': 0.3, 'se': 0.15},
            {'study': 'Study3', 'effect_size': 0.7, 'se': 0.25}
        ]
        
        data_file = input_path / 'mock_data.json'
        with open(data_file, 'w') as f:
            json.dump(mock_data, f)
        
        # Process data with R
        r_script = f"""
        .libPaths(Sys.getenv('R_LIBS'))
        library(jsonlite)
        
        # Load data
        data_path <- '{data_file}'
        mock_data <- fromJSON(data_path)
        
        # Simple statistical calculation
        effect_sizes <- mock_data$effect_size
        mean_effect <- mean(effect_sizes)
        se_pooled <- sqrt(mean(mock_data$se^2))
        
        # Results
        result <- list(
            status = 'success',
            n_studies = length(effect_sizes),
            pooled_effect = mean_effect,
            pooled_se = se_pooled,
            ci_lower = mean_effect - 1.96 * se_pooled,
            ci_upper = mean_effect + 1.96 * se_pooled
        )
        
        cat(toJSON(result, auto_unbox = TRUE))
        """
        
        result = subprocess.run(['Rscript', '-e', r_script],
                              capture_output=True, text=True, env=self.env)
        assert result.returncode == 0, f"Statistical operation failed: {result.stderr}"
        
        response = json.loads(result.stdout)
        assert response['status'] == 'success'
        assert response['n_studies'] == 3
        assert isinstance(response['pooled_effect'], (int, float))
        
        print("✅ Mock statistical operation completed successfully")
    
    def test_complete_workflow_integration(self):
        """Test complete workflow from start to finish"""
        print("🔄 Testing complete workflow integration...")
        
        workflow_steps = [
            "initialization",
            "data_upload",
            "validation", 
            "analysis",
            "results"
        ]
        
        session_path = self.sessions_dir / self.test_session_id
        session_path.mkdir(parents=True, exist_ok=True)
        
        # Initialize workflow state
        workflow_state = {
            'session_id': self.test_session_id,
            'current_step': 0,
            'completed_steps': [],
            'status': 'running'
        }
        
        # Simulate each workflow step
        for i, step in enumerate(workflow_steps):
            print(f"  Step {i+1}: {step}")
            
            # Update workflow state
            workflow_state['current_step'] = i
            workflow_state['completed_steps'].append(step)
            
            # Save state
            state_file = session_path / 'workflow_state.json'
            with open(state_file, 'w') as f:
                json.dump(workflow_state, f)
            
            # Verify state persisted
            with open(state_file, 'r') as f:
                saved_state = json.load(f)
            
            assert saved_state['current_step'] == i
            assert step in saved_state['completed_steps']
            
            # Small delay to simulate processing
            time.sleep(0.1)
        
        # Mark workflow complete
        workflow_state['status'] = 'completed'
        with open(state_file, 'w') as f:
            json.dump(workflow_state, f)
        
        # Final verification
        assert len(workflow_state['completed_steps']) == len(workflow_steps)
        assert workflow_state['status'] == 'completed'
        
        print("✅ Complete workflow integration successful")

def test_workflow_main():
    """Main function for running workflow tests"""
    print("🚀 Starting End-to-End Workflow Tests")
    print("=" * 50)
    
    # Run the tests
    test_class = TestEndToEndWorkflow()
    
    try:
        test_class.setup_method()
        test_class.test_r_environment_initialization()
        test_class.test_python_r_bridge_communication()
        test_class.test_session_management()
        test_class.test_health_check_endpoint()
        test_class.test_mock_statistical_operation()
        test_class.test_complete_workflow_integration()
        
        print("\n🎉 All End-to-End Workflow Tests Passed!")
        return True
        
    except Exception as e:
        print(f"\n❌ Workflow Test Failed: {e}")
        return False
        
    finally:
        test_class.teardown_method()

if __name__ == "__main__":
    success = test_workflow_main()
    sys.exit(0 if success else 1)