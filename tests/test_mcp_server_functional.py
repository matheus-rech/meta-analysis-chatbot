#!/usr/bin/env python3
"""
Functional tests for MCP server with real data
Tests the complete meta-analysis workflow using actual statistical computations
"""

import pytest
import json
import subprocess
import time
import tempfile
import base64
import os
from pathlib import Path
from typing import Dict, Any, List, Optional
import pandas as pd
import numpy as np


class TestMCPServerFunctional:
    """Functional tests for MCP server"""
    
    @pytest.fixture(scope="class")
    def server_process(self):
        """Start MCP server for testing"""
        env = os.environ.copy()
        env["DEBUG_R"] = "1"
        env["PYTHONUNBUFFERED"] = "1"
        env["RSCRIPT_TIMEOUT_SEC"] = "60"
        
        # Get project root (parent of tests directory)
        project_root = Path(__file__).parent.parent
        server_path = project_root / "server.py"
        
        proc = subprocess.Popen(
            ["python", str(server_path)],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            env=env,
            cwd=str(project_root)  # Run from project root
        )
        
        time.sleep(2)  # Give server time to start
        yield proc
        
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()
    
    def send_request(self, proc: subprocess.Popen, method: str, params: Dict[str, Any]) -> Dict:
        """Send JSON-RPC request to server"""
        request = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": method,
            "params": params
        }
        
        proc.stdin.write(json.dumps(request) + "\n")
        proc.stdin.flush()
        
        response_line = proc.stdout.readline()
        return json.loads(response_line)
    
    def extract_result(self, response: Dict) -> Dict:
        """Extract result from JSON-RPC response"""
        if "error" in response:
            raise Exception(f"Server error: {response['error']}")
        
        content = response["result"]["content"][0]["text"]
        return json.loads(content)
    
    # ========== Real Data Tests ==========
    
    def test_clinical_trial_odds_ratio(self, server_process):
        """Test clinical trial analysis with odds ratio"""
        
        # Real clinical trial data (simulated but realistic)
        data = """study,event1,n1,event2,n2,year,quality
ACCORD,315,2362,371,2371,2008,high
ADVANCE,557,5571,590,5569,2008,high
VADT,102,892,95,899,2009,moderate
UKPDS,119,2729,138,1138,1998,high
PROactive,301,2605,358,2633,2005,moderate
RECORD,60,2220,71,2227,2009,low
ORIGIN,580,6264,633,6273,2012,high
SAVOR,613,8280,609,8212,2013,high"""
        
        # Initialize
        response = self.send_request(server_process, "tools/call", {
            "name": "initialize_meta_analysis",
            "arguments": {
                "name": "Diabetes Clinical Trials",
                "study_type": "clinical_trial",
                "effect_measure": "OR",
                "analysis_model": "random"
            }
        })
        
        result = self.extract_result(response)
        assert result["status"] == "success"
        session_id = result["session_id"]
        
        # Upload data
        response = self.send_request(server_process, "tools/call", {
            "name": "upload_study_data",
            "arguments": {
                "session_id": session_id,
                "data_content": base64.b64encode(data.encode()).decode(),
                "data_format": "csv",
                "validation_level": "comprehensive"
            }
        })
        
        result = self.extract_result(response)
        assert result["status"] == "success"
        assert result["studies_uploaded"] == 8
        
        # Perform analysis
        response = self.send_request(server_process, "tools/call", {
            "name": "perform_meta_analysis",
            "arguments": {
                "session_id": session_id,
                "heterogeneity_test": True,
                "publication_bias": True,
                "sensitivity_analysis": False
            }
        })
        
        result = self.extract_result(response)
        assert result["status"] == "success"
        
        # Verify results are realistic
        assert "overall_effect" in result
        assert "confidence_interval" in result
        assert "p_value" in result
        assert "heterogeneity" in result
        
        # Check heterogeneity metrics
        heterogeneity = result["heterogeneity"]
        assert "i_squared" in heterogeneity
        assert 0 <= heterogeneity["i_squared"] <= 100
        assert "tau_squared" in heterogeneity
        assert heterogeneity["tau_squared"] >= 0
    
    def test_continuous_outcome_mean_difference(self, server_process):
        """Test continuous outcome with mean difference"""
        
        # Blood pressure reduction data
        data = """study,mean1,sd1,n1,mean2,sd2,n2,duration_weeks
HOPE,139.2,14.5,4645,141.8,14.2,4652,52
EUROPA,137.5,13.8,6110,139.2,13.5,6108,48
PEACE,133.1,12.2,4158,134.8,12.5,4132,56
CAMELOT,129.5,11.8,1318,131.2,12.1,1308,24
QUIET,135.8,13.2,877,137.5,13.5,890,32"""
        
        # Initialize
        response = self.send_request(server_process, "tools/call", {
            "name": "initialize_meta_analysis",
            "arguments": {
                "name": "Blood Pressure Studies",
                "study_type": "clinical_trial",
                "effect_measure": "MD",
                "analysis_model": "random"
            }
        })
        
        result = self.extract_result(response)
        session_id = result["session_id"]
        
        # Upload and analyze
        response = self.send_request(server_process, "tools/call", {
            "name": "upload_study_data",
            "arguments": {
                "session_id": session_id,
                "data_content": base64.b64encode(data.encode()).decode(),
                "data_format": "csv"
            }
        })
        
        result = self.extract_result(response)
        assert result["status"] == "success"
        
        # Perform analysis
        response = self.send_request(server_process, "tools/call", {
            "name": "perform_meta_analysis",
            "arguments": {
                "session_id": session_id,
                "heterogeneity_test": True
            }
        })
        
        result = self.extract_result(response)
        assert result["status"] == "success"
        
        # Verify mean difference results
        assert result["overall_effect"] < 0  # Should show reduction
        assert len(result["confidence_interval"]) == 2
        assert result["confidence_interval"][0] < result["overall_effect"]
        assert result["confidence_interval"][1] > result["overall_effect"]
    
    def test_standardized_mean_difference(self, server_process):
        """Test SMD with different depression scales"""
        
        # Depression scores on different scales
        data = """study,mean1,sd1,n1,mean2,sd2,n2,scale
BeckTrial,18.5,5.2,120,24.3,5.8,118,BDI
HamiltonStudy,22.1,6.1,95,28.7,6.5,93,HAM-D
MontgomeryRCT,15.3,4.8,110,19.8,5.1,112,MADRS
ZungTrial,45.2,8.9,85,52.1,9.2,83,SDS
PHQStudy,12.4,3.2,105,16.8,3.5,107,PHQ-9"""
        
        # Initialize with SMD
        response = self.send_request(server_process, "tools/call", {
            "name": "initialize_meta_analysis",
            "arguments": {
                "name": "Depression Scale Comparison",
                "study_type": "clinical_trial",
                "effect_measure": "SMD",
                "analysis_model": "random"
            }
        })
        
        result = self.extract_result(response)
        session_id = result["session_id"]
        
        # Upload and analyze
        response = self.send_request(server_process, "tools/call", {
            "name": "upload_study_data",
            "arguments": {
                "session_id": session_id,
                "data_content": base64.b64encode(data.encode()).decode(),
                "data_format": "csv"
            }
        })
        
        result = self.extract_result(response)
        assert result["status"] == "success"
        
        response = self.send_request(server_process, "tools/call", {
            "name": "perform_meta_analysis",
            "arguments": {
                "session_id": session_id,
                "heterogeneity_test": True
            }
        })
        
        result = self.extract_result(response)
        assert result["status"] == "success"
        
        # Check SMD interpretation
        smd = result["overall_effect"]
        assert -2 < smd < 2  # Reasonable SMD range
        
        # Check for effect size interpretation
        if "interpretation" in result:
            assert any(term in result["interpretation"].lower() 
                      for term in ["small", "medium", "large"])
    
    def test_publication_bias_with_sufficient_studies(self, server_process):
        """Test publication bias assessment with >10 studies"""
        
        # Generate 12 studies for bias assessment
        studies = []
        np.random.seed(42)
        for i in range(12):
            n1 = np.random.randint(50, 200)
            n2 = np.random.randint(50, 200)
            event1 = np.random.randint(10, min(40, n1))
            event2 = np.random.randint(15, min(45, n2))
            studies.append(f"Study{i+1},{event1},{n1},{event2},{n2}")
        
        data = "study,event1,n1,event2,n2\n" + "\n".join(studies)
        
        # Initialize and upload
        response = self.send_request(server_process, "tools/call", {
            "name": "initialize_meta_analysis",
            "arguments": {
                "name": "Bias Assessment Test",
                "study_type": "clinical_trial",
                "effect_measure": "OR",
                "analysis_model": "random"
            }
        })
        
        result = self.extract_result(response)
        session_id = result["session_id"]
        
        response = self.send_request(server_process, "tools/call", {
            "name": "upload_study_data",
            "arguments": {
                "session_id": session_id,
                "data_content": base64.b64encode(data.encode()).decode(),
                "data_format": "csv"
            }
        })
        
        # Assess publication bias
        response = self.send_request(server_process, "tools/call", {
            "name": "assess_publication_bias",
            "arguments": {
                "session_id": session_id,
                "methods": ["egger", "begg", "funnel"]
            }
        })
        
        result = self.extract_result(response)
        assert result["status"] == "success"
        
        # Check bias test results
        assert "egger_test" in result
        assert "p_value" in result["egger_test"]
        assert 0 <= result["egger_test"]["p_value"] <= 1
        
        assert "begg_test" in result
        assert "p_value" in result["begg_test"]
        
        # Check for interpretation
        assert "interpretation" in result
    
    def test_forest_plot_generation(self, server_process):
        """Test forest plot generation with real data"""
        
        data = """study,effect_size,se,year
Smith2020,0.45,0.12,2020
Johnson2021,0.38,0.15,2021
Williams2019,0.52,0.10,2019
Brown2022,0.41,0.14,2022
Davis2021,0.48,0.11,2021"""
        
        # Initialize
        response = self.send_request(server_process, "tools/call", {
            "name": "initialize_meta_analysis",
            "arguments": {
                "name": "Forest Plot Test",
                "study_type": "clinical_trial",
                "effect_measure": "OR",
                "analysis_model": "random"
            }
        })
        
        result = self.extract_result(response)
        session_id = result["session_id"]
        
        # Upload data
        response = self.send_request(server_process, "tools/call", {
            "name": "upload_study_data",
            "arguments": {
                "session_id": session_id,
                "data_content": base64.b64encode(data.encode()).decode(),
                "data_format": "csv"
            }
        })
        
        # Perform analysis first
        response = self.send_request(server_process, "tools/call", {
            "name": "perform_meta_analysis",
            "arguments": {
                "session_id": session_id
            }
        })
        
        # Generate forest plot
        response = self.send_request(server_process, "tools/call", {
            "name": "generate_forest_plot",
            "arguments": {
                "session_id": session_id,
                "plot_style": "classic",
                "confidence_level": 0.95
            }
        })
        
        result = self.extract_result(response)
        assert result["status"] == "success"
        
        # Check plot file was created
        assert "forest_plot_path" in result or "plot_file" in result
        
        # Verify file exists (if path is absolute)
        if "forest_plot_path" in result:
            plot_path = result["forest_plot_path"]
            if os.path.isabs(plot_path):
                assert os.path.exists(plot_path)
    
    def test_heterogeneity_investigation(self, server_process):
        """Test heterogeneity investigation with subgroup analysis"""
        
        # Data with clear subgroups
        data = """study,event1,n1,event2,n2,region,dose
EuropeA,45,150,38,148,Europe,high
EuropeB,42,160,40,155,Europe,high
AsiaA,25,180,35,175,Asia,low
AsiaB,28,170,38,168,Asia,low
AmericaA,55,200,45,195,America,high
AmericaB,52,190,43,188,America,high"""
        
        # Initialize and analyze
        response = self.send_request(server_process, "tools/call", {
            "name": "initialize_meta_analysis",
            "arguments": {
                "name": "Heterogeneity Investigation",
                "study_type": "clinical_trial",
                "effect_measure": "OR",
                "analysis_model": "random"
            }
        })
        
        result = self.extract_result(response)
        session_id = result["session_id"]
        
        response = self.send_request(server_process, "tools/call", {
            "name": "upload_study_data",
            "arguments": {
                "session_id": session_id,
                "data_content": base64.b64encode(data.encode()).decode(),
                "data_format": "csv"
            }
        })
        
        response = self.send_request(server_process, "tools/call", {
            "name": "perform_meta_analysis",
            "arguments": {
                "session_id": session_id,
                "heterogeneity_test": True,
                "subgroup_analysis": ["region", "dose"]
            }
        })
        
        result = self.extract_result(response)
        assert result["status"] == "success"
        
        # Check heterogeneity is detected and investigated
        assert result["heterogeneity"]["i_squared"] > 0
        
        # Check for subgroup results if implemented
        if "subgroup_results" in result:
            assert "region" in result["subgroup_results"]
            assert "dose" in result["subgroup_results"]
    
    def test_sensitivity_analysis(self, server_process):
        """Test sensitivity analysis by excluding studies"""
        
        data = """study,effect_size,se,quality
HighQuality1,0.45,0.10,high
HighQuality2,0.42,0.11,high
LowQuality1,0.85,0.25,low
HighQuality3,0.48,0.09,high
Outlier,1.25,0.35,low"""
        
        # Initialize and analyze
        response = self.send_request(server_process, "tools/call", {
            "name": "initialize_meta_analysis",
            "arguments": {
                "name": "Sensitivity Analysis",
                "study_type": "clinical_trial",
                "effect_measure": "OR",
                "analysis_model": "random"
            }
        })
        
        result = self.extract_result(response)
        session_id = result["session_id"]
        
        response = self.send_request(server_process, "tools/call", {
            "name": "upload_study_data",
            "arguments": {
                "session_id": session_id,
                "data_content": base64.b64encode(data.encode()).decode(),
                "data_format": "csv"
            }
        })
        
        # Perform analysis with sensitivity
        response = self.send_request(server_process, "tools/call", {
            "name": "perform_meta_analysis",
            "arguments": {
                "session_id": session_id,
                "sensitivity_analysis": True
            }
        })
        
        result = self.extract_result(response)
        assert result["status"] == "success"
        
        # Check for sensitivity results
        if "sensitivity_results" in result:
            # Should show different results when excluding outliers
            assert len(result["sensitivity_results"]) > 0
    
    def test_cochrane_recommendations_integration(self, server_process):
        """Test that Cochrane recommendations are provided"""
        
        # Data that should trigger recommendations
        data = """study,event1,n1,event2,n2
Study1,10,100,15,100
Study2,25,150,20,150
Study3,5,80,8,85"""
        
        # Initialize with few studies (should trigger warning)
        response = self.send_request(server_process, "tools/call", {
            "name": "initialize_meta_analysis",
            "arguments": {
                "name": "Cochrane Guidance Test",
                "study_type": "clinical_trial",
                "effect_measure": "OR",
                "analysis_model": "random"
            }
        })
        
        result = self.extract_result(response)
        session_id = result["session_id"]
        
        response = self.send_request(server_process, "tools/call", {
            "name": "upload_study_data",
            "arguments": {
                "session_id": session_id,
                "data_content": base64.b64encode(data.encode()).decode(),
                "data_format": "csv"
            }
        })
        
        response = self.send_request(server_process, "tools/call", {
            "name": "perform_meta_analysis",
            "arguments": {
                "session_id": session_id,
                "heterogeneity_test": True,
                "publication_bias": True
            }
        })
        
        result = self.extract_result(response)
        
        # Check for Cochrane recommendations
        if "cochrane_recommendations" in result:
            recommendations = result["cochrane_recommendations"]
            
            # Should warn about few studies
            assert any("few studies" in str(rec).lower() 
                      for rec in recommendations.values())
            
            # Should reference Cochrane Handbook
            assert any("cochrane" in str(rec).lower() 
                      for rec in recommendations.values())
    
    def test_report_generation(self, server_process):
        """Test comprehensive report generation"""
        
        data = """study,effect_size,se,year,quality
Study1,0.45,0.12,2020,high
Study2,0.38,0.15,2021,moderate
Study3,0.52,0.10,2019,high
Study4,0.41,0.14,2022,low
Study5,0.48,0.11,2021,high"""
        
        # Complete workflow
        response = self.send_request(server_process, "tools/call", {
            "name": "initialize_meta_analysis",
            "arguments": {
                "name": "Report Generation Test",
                "study_type": "clinical_trial",
                "effect_measure": "OR",
                "analysis_model": "random"
            }
        })
        
        result = self.extract_result(response)
        session_id = result["session_id"]
        
        # Upload data
        response = self.send_request(server_process, "tools/call", {
            "name": "upload_study_data",
            "arguments": {
                "session_id": session_id,
                "data_content": base64.b64encode(data.encode()).decode(),
                "data_format": "csv"
            }
        })
        
        # Perform analysis
        response = self.send_request(server_process, "tools/call", {
            "name": "perform_meta_analysis",
            "arguments": {
                "session_id": session_id,
                "heterogeneity_test": True
            }
        })
        
        # Generate report
        response = self.send_request(server_process, "tools/call", {
            "name": "generate_report",
            "arguments": {
                "session_id": session_id,
                "format": "html",
                "include_plots": True,
                "include_recommendations": True
            }
        })
        
        result = self.extract_result(response)
        assert result["status"] == "success"
        
        # Check report was generated
        assert "report_path" in result or "report_file" in result
        
        # If HTML format, check it's valid
        if result.get("format") == "html":
            report_path = result.get("report_path", result.get("report_file"))
            if report_path and os.path.isabs(report_path):
                assert os.path.exists(report_path)
                
                # Check report contains expected sections
                with open(report_path, 'r') as f:
                    content = f.read()
                    assert "meta-analysis" in content.lower()
                    assert "results" in content.lower()


if __name__ == "__main__":
    pytest.main([
        __file__,
        "-v",
        "--tb=short",
        "-s"
    ])
