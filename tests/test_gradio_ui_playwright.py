#!/usr/bin/env python3
"""
Comprehensive Playwright tests for Gradio Meta-Analysis Chatbot UI
Tests functional conversations, meta-analysis performance, and UI interactions
"""

import pytest
import asyncio
import json
import os
import time
from pathlib import Path
from typing import Dict, List, Any
from playwright.async_api import async_playwright, Page, expect
import pandas as pd
import numpy as np

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


class TestGradioMetaAnalysisUI:
    """Test suite for Gradio Meta-Analysis Chatbot UI"""
    
    @pytest.fixture(scope="function")
    async def browser_context(self):
        """Create browser context for testing"""
        async with async_playwright() as p:
            browser = await p.chromium.launch(
                headless=TEST_CONFIG["headless"],
                slow_mo=TEST_CONFIG["slow_mo"]
            )
            context = await browser.new_context(
                viewport={"width": 1280, "height": 720},
                ignore_https_errors=True
            )
            yield context
            await browser.close()
    
    @pytest.fixture(scope="function")
    async def page(self, browser_context):
        """Create a new page for each test"""
        page = await browser_context.new_page()
        await page.goto(TEST_CONFIG["base_url"])
        await page.wait_for_load_state("networkidle")
        yield page
        await page.close()
    
    # ========== UI Element Tests ==========
    
    @pytest.mark.asyncio
    async def test_ui_elements_present(self, page: Page):
        """Test that all required UI elements are present"""
        
        # Check for main tabs
        await expect(page.locator("button:has-text('AI Assistant')")).to_be_visible()
        await expect(page.locator("button:has-text('Direct Tools')")).to_be_visible()
        await expect(page.locator("button:has-text('File Upload')")).to_be_visible()
        
        # Check AI Assistant tab elements
        await page.click("button:has-text('AI Assistant')")
        await expect(page.locator(".chatbot")).to_be_visible()
        await expect(page.locator("textarea[placeholder*='Ask']")).to_be_visible()
        
        # Check Direct Tools tab elements
        await page.click("button:has-text('Direct Tools')")
        await expect(page.locator("text=Initialize Meta-Analysis")).to_be_visible()
        await expect(page.locator("text=Upload Data")).to_be_visible()
        await expect(page.locator("text=Perform Analysis")).to_be_visible()
        
        # Check File Upload tab elements
        await page.click("button:has-text('File Upload')")
        await expect(page.locator("text=Upload CSV")).to_be_visible()
    
    # ========== Functional Conversation Tests ==========
    
    @pytest.mark.asyncio
    async def test_chatbot_basic_conversation(self, page: Page):
        """Test basic chatbot conversation flow"""
        
        await page.click("button:has-text('AI Assistant')")
        
        # Send a greeting
        chat_input = page.locator("textarea[placeholder*='Ask']")
        await chat_input.fill("Hello, I need help with a meta-analysis")
        await chat_input.press("Enter")
        
        # Wait for response
        await page.wait_for_selector(".message.bot", timeout=10000)
        
        # Check response contains helpful information
        bot_response = await page.locator(".message.bot").last.inner_text()
        assert any(word in bot_response.lower() for word in ["help", "assist", "meta-analysis", "analysis"])
    
    @pytest.mark.asyncio
    async def test_chatbot_meta_analysis_workflow(self, page: Page):
        """Test complete meta-analysis workflow through chatbot"""
        
        await page.click("button:has-text('AI Assistant')")
        chat_input = page.locator("textarea[placeholder*='Ask']")
        
        # Step 1: Initialize
        await chat_input.fill("Initialize a meta-analysis for clinical trials with odds ratio")
        await chat_input.press("Enter")
        await page.wait_for_selector(".message.bot:has-text('initialized')", timeout=15000)
        
        # Extract session ID from response
        bot_response = await page.locator(".message.bot").last.inner_text()
        assert "session" in bot_response.lower()
        
        # Step 2: Request data upload guidance
        await chat_input.fill("What format should my data be in for odds ratio analysis?")
        await chat_input.press("Enter")
        await page.wait_for_selector(".message.bot", timeout=10000)
        
        bot_response = await page.locator(".message.bot").last.inner_text()
        assert any(word in bot_response.lower() for word in ["event", "n1", "n2", "study"])
    
    @pytest.mark.asyncio
    async def test_chatbot_educational_content(self, page: Page):
        """Test chatbot's ability to provide educational content"""
        
        await page.click("button:has-text('AI Assistant')")
        chat_input = page.locator("textarea[placeholder*='Ask']")
        
        # Ask about heterogeneity
        await chat_input.fill("What is heterogeneity in meta-analysis and how do I interpret I-squared?")
        await chat_input.press("Enter")
        await page.wait_for_selector(".message.bot", timeout=10000)
        
        bot_response = await page.locator(".message.bot").last.inner_text()
        
        # Check for educational content
        assert "heterogeneity" in bot_response.lower()
        assert any(term in bot_response.lower() for term in ["i-squared", "i²", "i2"])
        assert any(word in bot_response.lower() for word in ["variation", "studies", "chance"])
    
    # ========== Direct Tools Tests ==========
    
    @pytest.mark.asyncio
    async def test_direct_tools_initialization(self, page: Page):
        """Test meta-analysis initialization through direct tools"""
        
        await page.click("button:has-text('Direct Tools')")
        
        # Fill initialization form
        await page.fill("input[label='Analysis Name']", "Test Meta-Analysis")
        await page.select_option("select[label='Study Type']", "clinical_trial")
        await page.select_option("select[label='Effect Measure']", "OR")
        await page.select_option("select[label='Analysis Model']", "random")
        
        # Click initialize
        await page.click("button:has-text('Initialize')")
        
        # Wait for success message
        await expect(page.locator("text=Success")).to_be_visible(timeout=10000)
        
        # Check session ID is displayed
        session_display = page.locator(".session-id")
        await expect(session_display).to_contain_text("Session:")
    
    @pytest.mark.asyncio
    async def test_direct_tools_data_upload(self, page: Page):
        """Test data upload through direct tools"""
        
        await page.click("button:has-text('Direct Tools')")
        
        # First initialize
        await self._initialize_session(page)
        
        # Upload data
        await page.click("button:has-text('Upload Data')")
        
        # Create temp file with test data
        import tempfile
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            f.write(TEST_DATASETS["small_or"]["data"])
            temp_file = f.name
        
        # Upload file
        file_input = page.locator("input[type='file']")
        await file_input.set_input_files(temp_file)
        
        # Wait for preview
        await expect(page.locator(".dataframe")).to_be_visible(timeout=10000)
        
        # Confirm upload
        await page.click("button:has-text('Confirm Upload')")
        
        # Check success
        await expect(page.locator("text=uploaded successfully")).to_be_visible(timeout=10000)
        
        # Clean up
        os.unlink(temp_file)
    
    # ========== Performance Tests ==========
    
    @pytest.mark.asyncio
    async def test_performance_small_dataset(self, page: Page):
        """Test performance with small dataset"""
        
        start_time = time.time()
        
        # Initialize and upload small dataset
        await self._complete_analysis_workflow(page, TEST_DATASETS["small_or"])
        
        end_time = time.time()
        duration = end_time - start_time
        
        # Assert reasonable performance (< 30 seconds for small dataset)
        assert duration < 30, f"Small dataset analysis took {duration:.2f} seconds"
        
        # Check results quality
        await self._verify_analysis_results(page)
    
    @pytest.mark.asyncio
    async def test_performance_medium_dataset(self, page: Page):
        """Test performance with medium dataset"""
        
        start_time = time.time()
        
        # Initialize and upload medium dataset
        await self._complete_analysis_workflow(page, TEST_DATASETS["medium_md"])
        
        end_time = time.time()
        duration = end_time - start_time
        
        # Assert reasonable performance (< 45 seconds for medium dataset)
        assert duration < 45, f"Medium dataset analysis took {duration:.2f} seconds"
        
        # Check results quality
        await self._verify_analysis_results(page)
    
    @pytest.mark.asyncio
    async def test_performance_large_dataset(self, page: Page):
        """Test performance with large dataset"""
        
        start_time = time.time()
        
        # Initialize and upload large dataset
        await self._complete_analysis_workflow(page, TEST_DATASETS["large_rr"])
        
        end_time = time.time()
        duration = end_time - start_time
        
        # Assert reasonable performance (< 60 seconds for large dataset)
        assert duration < 60, f"Large dataset analysis took {duration:.2f} seconds"
        
        # Check results quality
        await self._verify_analysis_results(page)
    
    # ========== Heterogeneity Tests ==========
    
    @pytest.mark.asyncio
    async def test_heterogeneity_detection(self, page: Page):
        """Test detection and reporting of heterogeneity"""
        
        # Use heterogeneous dataset
        await self._complete_analysis_workflow(page, TEST_DATASETS["heterogeneous_smd"])
        
        # Check heterogeneity reporting
        results_text = await page.locator(".analysis-results").inner_text()
        
        assert "heterogeneity" in results_text.lower()
        assert any(term in results_text.lower() for term in ["i-squared", "i²", "tau"])
        
        # Check for Cochrane recommendations
        assert "cochrane" in results_text.lower()
    
    # ========== Forest Plot Tests ==========
    
    @pytest.mark.asyncio
    async def test_forest_plot_generation(self, page: Page):
        """Test forest plot generation and display"""
        
        # Complete analysis
        await self._complete_analysis_workflow(page, TEST_DATASETS["small_or"])
        
        # Generate forest plot
        await page.click("button:has-text('Generate Forest Plot')")
        
        # Wait for plot
        await expect(page.locator("img.forest-plot")).to_be_visible(timeout=15000)
        
        # Verify plot is actually displayed (has src)
        plot_element = page.locator("img.forest-plot")
        src = await plot_element.get_attribute("src")
        assert src and len(src) > 0
    
    # ========== Publication Bias Tests ==========
    
    @pytest.mark.asyncio
    async def test_publication_bias_assessment(self, page: Page):
        """Test publication bias assessment"""
        
        # Use large dataset for bias assessment
        await self._complete_analysis_workflow(page, TEST_DATASETS["large_rr"])
        
        # Assess publication bias
        await page.click("button:has-text('Assess Publication Bias')")
        
        # Select methods
        await page.check("input[value='egger']")
        await page.check("input[value='begg']")
        
        await page.click("button:has-text('Run Assessment')")
        
        # Wait for results
        await expect(page.locator(".bias-results")).to_be_visible(timeout=15000)
        
        # Check results contain expected elements
        bias_text = await page.locator(".bias-results").inner_text()
        assert any(test in bias_text.lower() for test in ["egger", "begg"])
        assert "p-value" in bias_text.lower()
    
    # ========== Error Handling Tests ==========
    
    @pytest.mark.asyncio
    async def test_error_handling_invalid_data(self, page: Page):
        """Test error handling with invalid data"""
        
        await page.click("button:has-text('Direct Tools')")
        
        # Initialize session
        await self._initialize_session(page)
        
        # Try to upload invalid data
        invalid_data = "This is not CSV data\nJust random text"
        
        import tempfile
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            f.write(invalid_data)
            temp_file = f.name
        
        file_input = page.locator("input[type='file']")
        await file_input.set_input_files(temp_file)
        
        # Should show error
        await expect(page.locator(".error-message")).to_be_visible(timeout=10000)
        
        error_text = await page.locator(".error-message").inner_text()
        assert "error" in error_text.lower() or "invalid" in error_text.lower()
        
        os.unlink(temp_file)
    
    @pytest.mark.asyncio
    async def test_error_handling_missing_session(self, page: Page):
        """Test error handling when session is missing"""
        
        await page.click("button:has-text('Direct Tools')")
        
        # Try to perform analysis without initialization
        await page.click("button:has-text('Perform Analysis')")
        
        # Should show error about missing session
        await expect(page.locator(".error-message")).to_be_visible(timeout=10000)
        
        error_text = await page.locator(".error-message").inner_text()
        assert "session" in error_text.lower()
    
    # ========== Helper Methods ==========
    
    async def _initialize_session(self, page: Page, effect_measure: str = "OR") -> str:
        """Helper to initialize a meta-analysis session"""
        
        await page.fill("input[label='Analysis Name']", "Test Analysis")
        await page.select_option("select[label='Study Type']", "clinical_trial")
        await page.select_option("select[label='Effect Measure']", effect_measure)
        await page.select_option("select[label='Analysis Model']", "random")
        
        await page.click("button:has-text('Initialize')")
        await page.wait_for_selector("text=Success", timeout=10000)
        
        # Extract session ID
        session_element = page.locator(".session-id")
        session_text = await session_element.inner_text()
        session_id = session_text.split(":")[-1].strip()
        
        return session_id
    
    async def _upload_data(self, page: Page, dataset: Dict[str, str]):
        """Helper to upload data"""
        
        import tempfile
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            f.write(dataset["data"])
            temp_file = f.name
        
        file_input = page.locator("input[type='file']")
        await file_input.set_input_files(temp_file)
        
        await page.click("button:has-text('Confirm Upload')")
        await page.wait_for_selector("text=uploaded successfully", timeout=10000)
        
        os.unlink(temp_file)
    
    async def _complete_analysis_workflow(self, page: Page, dataset: Dict[str, str]):
        """Helper to complete full analysis workflow"""
        
        await page.click("button:has-text('Direct Tools')")
        
        # Determine effect measure from dataset
        if "event" in dataset["data"]:
            effect_measure = "OR"
        elif "mean" in dataset["data"]:
            effect_measure = "MD" if "sd1" in dataset["data"] else "SMD"
        else:
            effect_measure = "RR"
        
        # Initialize
        session_id = await self._initialize_session(page, effect_measure)
        
        # Upload data
        await self._upload_data(page, dataset)
        
        # Perform analysis
        await page.click("button:has-text('Perform Analysis')")
        await page.check("input[value='heterogeneity_test']")
        await page.click("button:has-text('Run Analysis')")
        
        # Wait for results
        await page.wait_for_selector(".analysis-results", timeout=20000)
    
    async def _verify_analysis_results(self, page: Page):
        """Helper to verify analysis results are valid"""
        
        results_element = page.locator(".analysis-results")
        results_text = await results_element.inner_text()
        
        # Check for required elements
        assert "effect" in results_text.lower()
        assert "confidence interval" in results_text.lower() or "ci" in results_text.lower()
        assert "p-value" in results_text.lower() or "p =" in results_text.lower()
        
        # Check for numerical values
        import re
        numbers = re.findall(r'\d+\.?\d*', results_text)
        assert len(numbers) > 0, "No numerical results found"


# ========== Test Runner Configuration ==========

if __name__ == "__main__":
    # Run tests with pytest
    pytest.main([
        __file__,
        "-v",  # Verbose output
        "--tb=short",  # Short traceback format
        "--asyncio-mode=auto",  # Auto async mode
        "-s",  # Don't capture output
        "--html=test_results.html",  # Generate HTML report
        "--self-contained-html"  # Include CSS/JS in HTML
    ])
