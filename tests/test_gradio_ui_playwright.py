#!/usr/bin/env python3
"""
Comprehensive Playwright tests for Gradio Meta-Analysis Chatbot UI
Tests functional conversations, meta-analysis performance, and UI interactions
"""

import pytest
import json
import os
import time
import sys
import subprocess
from pathlib import Path
from typing import Dict, List, Any
from playwright.sync_api import Page, expect
import pandas as pd
import numpy as np
import requests

# Test configuration
TEST_CONFIG = {
    "base_url": os.getenv("GRADIO_URL", "http://localhost:7860"),
    "timeout": 30000,  # 30 seconds
    "slow_mo": 100 if os.getenv("DEBUG") else 0,
    "headless": os.getenv("HEADLESS", "true").lower() == "true"
}

# Real test datasets
TEST_DATASETS = {
    "small_or": {
        "description": "Small dataset with Odds Ratio data",
        "data": """study,event1,n1,event2,n2,year,quality
Smith2020,45,150,38,148,2020,high
Johnson2021,38,200,45,195,2021,moderate
Williams2019,52,175,40,180,2019,high
Brown2022,41,225,50,220,2022,low
Davis2021,48,160,42,165,2021,high"""
    },
    
    "medium_md": {
        "description": "Medium dataset with Mean Difference data",
        "data": """study,mean1,sd1,n1,mean2,sd2,n2,duration_weeks
Trial_A,85.2,12.5,120,92.1,13.2,118,12
Trial_B,83.7,11.8,95,89.5,12.1,98,12
Trial_C,86.1,13.1,110,93.8,14.2,112,8
Trial_D,84.5,12.2,105,91.2,13.5,103,16
Trial_E,85.8,11.9,115,92.5,12.8,117,12
Trial_F,84.2,12.7,100,90.8,13.1,102,10
Trial_G,85.5,12.3,108,92.1,13.0,110,12"""
    },
    
    "large_rr": {
        "description": "Large dataset with Risk Ratio data",
        "data": """study,events1,total1,events2,total2,region
Study01,23,250,31,245,Europe
Study02,18,180,25,175,Asia
Study03,29,300,38,295,NorthAmerica
Study04,15,150,22,148,Europe
Study05,21,200,28,198,Asia
Study06,26,275,35,270,SouthAmerica
Study07,19,190,26,188,Europe
Study08,24,240,32,235,NorthAmerica
Study09,17,170,24,168,Asia
Study10,22,220,30,215,Europe
Study11,20,210,27,208,Africa
Study12,25,260,34,255,NorthAmerica"""
    },
    
    "heterogeneous_smd": {
        "description": "Dataset with high heterogeneity for SMD",
        "data": """study,mean_exp,sd_exp,n_exp,mean_ctrl,sd_ctrl,n_ctrl,scale
Beck2020,18.5,5.2,60,24.3,5.8,58,BDI
Hamilton2021,22.1,6.1,75,28.7,6.5,73,HAM-D
Montgomery2019,15.3,4.8,50,19.8,5.1,52,MADRS
Zung2022,45.2,8.9,65,52.1,9.2,63,SDS
PHQ2021,12.4,3.2,55,16.8,3.5,57,PHQ-9"""
    }
}


@pytest.fixture(scope="session")
def gradio_server():
    """Fixture to start the Gradio server for the test session."""
    project_root = Path(__file__).parent.parent
    server_path = project_root / "chatbot_enhanced.py"

    env = os.environ.copy()
    env["PYTHONUNBUFFERED"] = "1"
    env["TEST_MODE"] = "1"
    if "OPENAI_API_KEY" not in env and "ANTHROPIC_API_KEY" not in env:
        # Placeholder for actual key management
        pass

    proc = subprocess.Popen(
        [sys.executable, str(server_path)],
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )

    # Wait for the server to be ready
    print("Waiting for Gradio UI server to start...")
    start_time = time.time()
    healthy = False
    health_url = TEST_CONFIG['base_url'] + '/health'
    while time.time() - start_time < 60:  # 60-second timeout for UI server
        try:
            response = requests.get(health_url, timeout=1)
            if response.status_code == 200 and response.json().get('status') == 'healthy':
                healthy = True
                print("Gradio UI server is healthy.")
                break
        except requests.ConnectionError:
            time.sleep(0.5)

    if not healthy:
        proc.terminate()
        pytest.fail("Gradio UI server did not become healthy within 60 seconds.")

    yield proc

    print("Stopping Gradio UI server...")
    proc.terminate()
    try:
        proc.wait(timeout=5)
    except subprocess.TimeoutExpired:
        proc.kill()
    print("Gradio UI server stopped.")

class TestGradioMetaAnalysisUI:
    """Test suite for Gradio Meta-Analysis Chatbot UI"""
    
    def test_ui_elements_present(self, page: Page, gradio_server):
        """Test that all UI elements are present and accessible"""
        page.goto(TEST_CONFIG["base_url"])
        
        # Check for main tabs
        assert page.locator("text=AI Chatbot").is_visible()
        assert page.locator("text=Direct Tools").is_visible()
        
        # Check chatbot tab elements
        page.click("text=AI Chatbot")
        assert page.locator(".gradio-chatbot").is_visible()
        
        # Check for input area (multimodal textbox or regular textbox)
        input_area = page.locator("textarea").first
        assert input_area.is_visible()
        
        # Check for submit button
        submit_button = page.locator("button:has-text('Submit')").first
        assert submit_button.is_visible()
    
    def test_chatbot_basic_conversation(self, page: Page, gradio_server):
        """Test basic chatbot conversation flow"""
        page.goto(TEST_CONFIG["base_url"])
        page.click("text=AI Chatbot")
        
        # Send a greeting
        input_area = page.locator("textarea").first
        input_area.fill("Hello, can you help me with meta-analysis?")
        
        submit_button = page.locator("button:has-text('Submit')").first
        submit_button.click()
        
        # Wait for response
        page.wait_for_timeout(3000)
        
        # Check for response in chatbot
        chatbot = page.locator(".gradio-chatbot")
        assert chatbot.is_visible()
        
        # Verify response contains relevant content
        response_text = chatbot.inner_text()
        assert len(response_text) > 50  # Should have substantial response
        assert any(word in response_text.lower() for word in ["meta-analysis", "help", "assist", "study"])
    
    def test_chatbot_meta_analysis_workflow(self, page: Page, gradio_server):
        """Test complete meta-analysis workflow through chatbot"""
        page.goto(TEST_CONFIG["base_url"])
        page.click("text=AI Chatbot")
        
        # Step 1: Initialize meta-analysis
        input_area = page.locator("textarea").first
        input_area.fill("I want to start a new meta-analysis for clinical trials with odds ratio")
        
        submit_button = page.locator("button:has-text('Submit')").first
        submit_button.click()
        
        page.wait_for_timeout(5000)
        
        # Check for initialization confirmation
        chatbot_text = page.locator(".gradio-chatbot").inner_text()
        assert any(word in chatbot_text.lower() for word in ["initialized", "created", "session", "ready"])
        
        # Step 2: Upload data
        input_area.fill(f"Here is my data:\n{TEST_DATASETS['small_or']['data']}")
        submit_button.click()
        
        page.wait_for_timeout(5000)
        
        # Check for upload confirmation
        chatbot_text = page.locator(".gradio-chatbot").inner_text()
        assert any(word in chatbot_text.lower() for word in ["uploaded", "received", "studies", "data"])
        
        # Step 3: Perform analysis
        input_area.fill("Please perform the meta-analysis with heterogeneity testing")
        submit_button.click()
        
        page.wait_for_timeout(8000)
        
        # Check for analysis results
        chatbot_text = page.locator(".gradio-chatbot").inner_text()
        assert any(word in chatbot_text.lower() for word in ["effect", "confidence", "heterogeneity", "i-squared", "i²"])
    
    def test_chatbot_educational_content(self, page: Page, gradio_server):
        """Test chatbot's ability to provide educational content"""
        page.goto(TEST_CONFIG["base_url"])
        page.click("text=AI Chatbot")
        
        # Ask about heterogeneity
        input_area = page.locator("textarea").first
        input_area.fill("What is heterogeneity in meta-analysis and how is it measured?")
        
        submit_button = page.locator("button:has-text('Submit')").first
        submit_button.click()
        
        page.wait_for_timeout(5000)
        
        # Check for educational response
        chatbot_text = page.locator(".gradio-chatbot").inner_text()
        assert "heterogeneity" in chatbot_text.lower()
        assert any(term in chatbot_text.lower() for term in ["i-squared", "i²", "tau", "q-test", "cochran"])
        
        # Ask about effect measures
        input_area.fill("What's the difference between odds ratio and risk ratio?")
        submit_button.click()
        
        page.wait_for_timeout(5000)
        
        chatbot_text = page.locator(".gradio-chatbot").inner_text()
        assert "odds ratio" in chatbot_text.lower()
        assert "risk ratio" in chatbot_text.lower()
    
    def test_direct_tools_initialization(self, page: Page, gradio_server):
        """Test direct tools tab initialization"""
        page.goto(TEST_CONFIG["base_url"])
        page.click("text=Direct Tools")
        
        # Check for initialization section
        assert page.locator("text=Initialize Meta-Analysis").is_visible()
        
        # Fill initialization form
        page.fill("input[placeholder*='Project']", "Test Project")
        
        # Select options if dropdowns exist
        study_type = page.locator("select").first
        if study_type.is_visible():
            study_type.select_option("clinical_trial")
        
        # Click initialize button
        init_button = page.locator("button:has-text('Initialize')").first
        if init_button.is_visible():
            init_button.click()
            page.wait_for_timeout(3000)
            
            # Check for success message
            output_text = page.inner_text()
            assert any(word in output_text.lower() for word in ["success", "initialized", "session"])
    
    def test_direct_tools_data_upload(self, page: Page, gradio_server):
        """Test data upload in direct tools"""
        page.goto(TEST_CONFIG["base_url"])
        page.click("text=Direct Tools")
        
        # First initialize
        page.fill("input[placeholder*='Project']", "Upload Test")
        init_button = page.locator("button:has-text('Initialize')").first
        if init_button.is_visible():
            init_button.click()
            page.wait_for_timeout(3000)
        
        # Look for upload section
        if page.locator("text=Upload Data").is_visible():
            # Create a test CSV file
            test_file = Path("/tmp/test_data.csv")
            test_file.write_text(TEST_DATASETS["small_or"]["data"])
            
            # Upload file
            file_input = page.locator("input[type='file']").first
            if file_input.is_visible():
                file_input.set_input_files(str(test_file))
                
                upload_button = page.locator("button:has-text('Upload')").first
                if upload_button.is_visible():
                    upload_button.click()
                    page.wait_for_timeout(3000)
                    
                    # Check for success
                    output_text = page.inner_text()
                    assert any(word in output_text.lower() for word in ["uploaded", "success", "studies"])
    
    def test_performance_small_dataset(self, page: Page, gradio_server):
        """Test performance with small dataset"""
        page.goto(TEST_CONFIG["base_url"])
        page.click("text=AI Chatbot")
        
        start_time = time.time()
        
        # Quick workflow
        input_area = page.locator("textarea").first
        input_area.fill("Initialize a meta-analysis for OR data")
        
        submit_button = page.locator("button:has-text('Submit')").first
        submit_button.click()
        
        page.wait_for_timeout(3000)
        
        input_area.fill(f"Upload this data:\n{TEST_DATASETS['small_or']['data']}")
        submit_button.click()
        
        page.wait_for_timeout(3000)
        
        input_area.fill("Perform the analysis")
        submit_button.click()
        
        page.wait_for_timeout(5000)
        
        elapsed = time.time() - start_time
        assert elapsed < 30  # Should complete within 30 seconds
        
        # Verify completion
        chatbot_text = page.locator(".gradio-chatbot").inner_text()
        assert any(word in chatbot_text.lower() for word in ["effect", "confidence", "result"])
    
    def test_performance_medium_dataset(self, page: Page, gradio_server):
        """Test performance with medium dataset"""
        page.goto(TEST_CONFIG["base_url"])
        page.click("text=AI Chatbot")
        
        start_time = time.time()
        
        input_area = page.locator("textarea").first
        input_area.fill("Initialize meta-analysis for mean difference")
        
        submit_button = page.locator("button:has-text('Submit')").first
        submit_button.click()
        
        page.wait_for_timeout(3000)
        
        input_area.fill(f"Data:\n{TEST_DATASETS['medium_md']['data']}")
        submit_button.click()
        
        page.wait_for_timeout(5000)
        
        input_area.fill("Analyze with heterogeneity")
        submit_button.click()
        
        page.wait_for_timeout(7000)
        
        elapsed = time.time() - start_time
        assert elapsed < 45  # Should complete within 45 seconds
    
    def test_performance_large_dataset(self, page: Page, gradio_server):
        """Test performance with large dataset"""
        page.goto(TEST_CONFIG["base_url"])
        page.click("text=AI Chatbot")
        
        start_time = time.time()
        
        input_area = page.locator("textarea").first
        input_area.fill("Start meta-analysis for risk ratio")
        
        submit_button = page.locator("button:has-text('Submit')").first
        submit_button.click()
        
        page.wait_for_timeout(3000)
        
        input_area.fill(f"Data:\n{TEST_DATASETS['large_rr']['data']}")
        submit_button.click()
        
        page.wait_for_timeout(7000)
        
        input_area.fill("Full analysis with bias assessment")
        submit_button.click()
        
        page.wait_for_timeout(10000)
        
        elapsed = time.time() - start_time
        assert elapsed < 60  # Should complete within 60 seconds
    
    def test_heterogeneity_detection(self, page: Page, gradio_server):
        """Test heterogeneity detection with heterogeneous data"""
        page.goto(TEST_CONFIG["base_url"])
        page.click("text=AI Chatbot")
        
        input_area = page.locator("textarea").first
        input_area.fill("Initialize SMD meta-analysis")
        
        submit_button = page.locator("button:has-text('Submit')").first
        submit_button.click()
        
        page.wait_for_timeout(3000)
        
        input_area.fill(f"Data:\n{TEST_DATASETS['heterogeneous_smd']['data']}")
        submit_button.click()
        
        page.wait_for_timeout(5000)
        
        input_area.fill("Analyze and check heterogeneity")
        submit_button.click()
        
        page.wait_for_timeout(7000)
        
        # Check for heterogeneity detection
        chatbot_text = page.locator(".gradio-chatbot").inner_text()
        assert any(term in chatbot_text.lower() for term in ["heterogeneity", "i-squared", "i²", "tau"])
        
        # Should detect substantial heterogeneity
        assert any(term in chatbot_text.lower() for term in ["substantial", "considerable", "high", "moderate"])
    
    def test_forest_plot_generation(self, page: Page, gradio_server):
        """Test forest plot generation"""
        page.goto(TEST_CONFIG["base_url"])
        page.click("text=AI Chatbot")
        
        # Quick setup
        input_area = page.locator("textarea").first
        input_area.fill("Initialize OR analysis")
        
        submit_button = page.locator("button:has-text('Submit')").first
        submit_button.click()
        
        page.wait_for_timeout(3000)
        
        input_area.fill(f"Data:\n{TEST_DATASETS['small_or']['data']}")
        submit_button.click()
        
        page.wait_for_timeout(5000)
        
        input_area.fill("Perform analysis and generate forest plot")
        submit_button.click()
        
        page.wait_for_timeout(10000)
        
        # Check for plot generation confirmation
        chatbot_text = page.locator(".gradio-chatbot").inner_text()
        assert any(word in chatbot_text.lower() for word in ["forest", "plot", "generated", "created", "visualization"])
    
    def test_publication_bias_assessment(self, page: Page, gradio_server):
        """Test publication bias assessment"""
        page.goto(TEST_CONFIG["base_url"])
        page.click("text=AI Chatbot")
        
        input_area = page.locator("textarea").first
        input_area.fill("Initialize RR analysis")
        
        submit_button = page.locator("button:has-text('Submit')").first
        submit_button.click()
        
        page.wait_for_timeout(3000)
        
        input_area.fill(f"Data:\n{TEST_DATASETS['large_rr']['data']}")
        submit_button.click()
        
        page.wait_for_timeout(5000)
        
        input_area.fill("Assess publication bias")
        submit_button.click()
        
        page.wait_for_timeout(8000)
        
        # Check for bias assessment
        chatbot_text = page.locator(".gradio-chatbot").inner_text()
        assert any(term in chatbot_text.lower() for term in ["bias", "egger", "begg", "funnel", "asymmetry"])
    
    def test_error_handling_invalid_data(self, page: Page, gradio_server):
        """Test error handling with invalid data"""
        page.goto(TEST_CONFIG["base_url"])
        page.click("text=AI Chatbot")
        
        input_area = page.locator("textarea").first
        input_area.fill("Initialize analysis")
        
        submit_button = page.locator("button:has-text('Submit')").first
        submit_button.click()
        
        page.wait_for_timeout(3000)
        
        # Send invalid data
        input_area.fill("Upload data: invalid,data,format\n123,abc,xyz")
        submit_button.click()
        
        page.wait_for_timeout(5000)
        
        # Should handle error gracefully
        chatbot_text = page.locator(".gradio-chatbot").inner_text()
        assert any(word in chatbot_text.lower() for word in ["error", "invalid", "format", "problem", "issue"])
    
    def test_error_handling_missing_session(self, page: Page, gradio_server):
        """Test error handling when session is missing"""
        page.goto(TEST_CONFIG["base_url"])
        page.click("text=AI Chatbot")
        
        # Try to perform analysis without initialization
        input_area = page.locator("textarea").first
        input_area.fill("Perform meta-analysis on my data")
        
        submit_button = page.locator("button:has-text('Submit')").first
        submit_button.click()
        
        page.wait_for_timeout(5000)
        
        # Should prompt for initialization
        chatbot_text = page.locator(".gradio-chatbot").inner_text()
        assert any(word in chatbot_text.lower() for word in ["initialize", "first", "start", "begin", "session"])


if __name__ == "__main__":
    pytest.main([
        __file__,
        "-v",
        "--headed" if os.getenv("DEBUG") else "",
        "--screenshot=only-on-failure",
        "--video=retain-on-failure",
        "--tracing=retain-on-failure"
    ])