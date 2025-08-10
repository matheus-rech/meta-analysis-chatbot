# Meta-Analysis Chatbot Test Suite

Comprehensive testing framework for the Meta-Analysis Chatbot, including UI testing with Playwright, functional testing with real data, and MCP server debugging with MCP Inspector.

## Test Coverage

### 1. **UI Testing (Playwright)**
- `test_gradio_ui_playwright.py`: Comprehensive UI tests
  - Element presence and visibility
  - Functional conversation flows
  - Meta-analysis workflow testing
  - Performance testing with different dataset sizes
  - Error handling and edge cases
  - Forest plot generation
  - Publication bias assessment

### 2. **Functional Testing**
- `test_mcp_server_functional.py`: Server functionality with real data
  - Clinical trial analysis with odds ratios
  - Continuous outcomes with mean differences
  - Standardized mean differences
  - Publication bias detection (>10 studies)
  - Heterogeneity investigation
  - Sensitivity analysis
  - Cochrane recommendations integration

### 3. **Integration Testing**
- `test_mcp_clients.py`: MCP client integration
  - STDIO server tests (Claude Desktop)
  - Gradio server tests (Cursor)
  - Configuration validation
  - Tool discovery and execution

### 4. **MCP Inspector Testing**
- `test_mcp_inspector_setup.py`: Interactive debugging
  - Automated setup of MCP Inspector
  - Guided testing procedures
  - Performance profiling
  - Error debugging

## Quick Start

### Prerequisites

```bash
# Install Python dependencies
pip install -r requirements-test.txt

# Install Playwright browsers
playwright install chromium

# Install R packages
Rscript -e "install.packages(c('meta', 'metafor', 'jsonlite', 'ggplot2', 'rmarkdown', 'knitr'))"

# Install Node.js (for MCP Inspector)
# Download from https://nodejs.org/
```

### Running Tests

#### Run All Tests
```bash
python tests/run_all_tests.py
```

#### Run Specific Test Suite
```bash
# Functional tests
python tests/run_all_tests.py functional

# UI tests
python tests/run_all_tests.py ui

# Integration tests
python tests/run_all_tests.py integration

# MCP Inspector (interactive)
python tests/run_all_tests.py inspector
```

#### Run Individual Test Files
```bash
# Run with pytest directly
pytest tests/test_mcp_server_functional.py -v

# Run UI tests with HTML report
pytest tests/test_gradio_ui_playwright.py --html=report.html --self-contained-html

# Run in headed mode for debugging
HEADLESS=false pytest tests/test_gradio_ui_playwright.py -v
```

## Test Data

All tests use **real data**, not mock data:

### Clinical Trial Data (Odds Ratio)
- Diabetes trials: ACCORD, ADVANCE, VADT, UKPDS, etc.
- Real event counts and sample sizes
- Quality assessments included

### Continuous Outcome Data
- Blood pressure studies: HOPE, EUROPA, PEACE, etc.
- Mean differences with standard deviations
- Multiple follow-up durations

### Depression Scale Data (SMD)
- Different scales: BDI, HAM-D, MADRS, SDS, PHQ-9
- Realistic effect sizes and variations
- High heterogeneity scenarios

### Publication Bias Testing
- Datasets with 12+ studies
- Realistic publication bias patterns
- Various effect sizes and precisions

## MCP Inspector Usage

The MCP Inspector provides interactive debugging capabilities:

1. **Start Inspector**
```bash
python tests/test_mcp_inspector_setup.py
```

2. **Access Interface**
- Open http://localhost:5173 in your browser
- Select "meta-analysis" server

3. **Test Tools**
- Tool discovery
- Parameter validation
- Response inspection
- Performance profiling

4. **Debug Workflow**
- Initialize session
- Upload data
- Perform analysis
- Generate visualizations
- Check error handling

## Performance Benchmarks

Expected performance targets:

| Dataset Size | Analysis Time | Target |
|-------------|---------------|---------|
| Small (5 studies) | < 30s | ✓ |
| Medium (7 studies) | < 45s | ✓ |
| Large (12 studies) | < 60s | ✓ |

## Test Reports

### HTML Reports
- Playwright tests generate HTML reports
- Located in `tests/` directory
- Self-contained with screenshots

### JSON Reports
- Comprehensive test results
- Timestamped: `test_report_YYYYMMDD_HHMMSS.json`
- Includes all metrics and timings

### Coverage Reports
```bash
# Generate coverage report
pytest tests/ --cov=. --cov-report=html
# Open htmlcov/index.html
```

## Continuous Integration

### GitHub Actions Workflow
```yaml
name: Test Suite

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - uses: actions/setup-python@v2
      - uses: r-lib/actions/setup-r@v2
      - run: pip install -r requirements-test.txt
      - run: playwright install chromium
      - run: python tests/run_all_tests.py
```

## Debugging Failed Tests

### UI Test Failures
1. Run in headed mode: `HEADLESS=false pytest`
2. Add `--slowmo=1000` for slow motion
3. Check screenshots in test reports
4. Use `page.pause()` for breakpoints

### Functional Test Failures
1. Enable debug mode: `DEBUG_R=1`
2. Check R script output
3. Verify session directories
4. Inspect JSON payloads

### Integration Test Failures
1. Check server is running
2. Verify port availability
3. Check API keys are set
4. Review server logs

## Test Development

### Adding New UI Tests
```python
@pytest.mark.asyncio
async def test_new_feature(self, page: Page):
    """Test description"""
    await page.click("selector")
    await expect(page.locator("result")).to_be_visible()
```

### Adding New Functional Tests
```python
def test_new_analysis(self, server_process):
    """Test description"""
    response = self.send_request(server_process, "tools/call", {
        "name": "tool_name",
        "arguments": {}
    })
    result = self.extract_result(response)
    assert result["status"] == "success"
```

## Known Issues

1. **Playwright on M1 Macs**: May need Rosetta
2. **R Package Installation**: May need admin rights
3. **Port Conflicts**: Ensure 7860 is available
4. **API Keys**: Tests work without real keys for UI

## Support

For issues or questions:
1. Check test output for detailed errors
2. Review logs in `sessions/` directory
3. Enable debug mode for verbose output
4. Use MCP Inspector for interactive debugging
