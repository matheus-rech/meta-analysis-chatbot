# MCP Server Testing Plan for Meta-Analysis Chatbot

## Executive Summary

This document outlines a comprehensive testing plan for the Meta-Analysis Chatbot's MCP (Model Context Protocol) server implementation, including integration with Claude Desktop, Cursor, and other MCP-compatible clients.

## Current Implementation Analysis

### ✅ What We Have

1. **Custom stdio JSON-RPC Server** (`server.py`)
   - Implements minimal JSON-RPC 2.0 protocol
   - Supports `tools/list` and `tools/call` methods
   - Subprocess-based R script execution
   - File-based argument passing for large payloads

2. **Multiple Gradio Interfaces**
   - `chatbot_langchain.py`: LangChain-based orchestration
   - `gradio_native_mcp.py`: Native Gradio patterns
   - `api_server.py`: FastAPI with optional FastMCP integration

3. **R Statistical Backend**
   - Complete tool implementations in R
   - Session-based state management
   - JSON I/O with file support

### ⚠️ Gaps vs Standard M

1. **Missing Standard MCP Features**
   - No SSE (Server-Sent Events) transport
   - No resource management endpoints
   - No prompt managementCP
   - Limited error response format

2. **Protocol Differences**
   - Custom JSON-RPC implementation vs MCP standard
   - Non-standard tool response format
   - Missing MCP metadata fields

## Testing Plan

### Phase 1: Core Functionality Testing

#### 1.1 Unit Tests for MCP Server

```python
# test_mcp_server.py
import pytest
import json
import subprocess

def test_tools_list():
    """Test that server returns correct tool list"""
    # Start server and send tools/list request
    # Verify all 8 tools are returned

def test_tool_initialization():
    """Test initialize_meta_analysis creates session"""
    # Call initialize tool
    # Verify session directory created
    # Verify session.json exists

def test_large_payload_handling():
    """Test file-based argument passing"""
    # Create 10MB CSV data
    # Upload via tool call
    # Verify no CLI arg errors

def test_timeout_handling():
    """Test RSCRIPT_TIMEOUT_SEC enforcement"""
    # Set short timeout
    # Call long-running tool
    # Verify timeout error returned
```

#### 1.2 Integration Tests

```python
def test_full_workflow():
    """Test complete analysis workflow"""
    # Initialize session
    # Upload data
    # Perform analysis
    # Generate forest plot
    # Assess publication bias
    # Generate report
    # Verify all outputs exist
```

### Phase 2: Claude Desktop Integration

#### 2.1 Configuration Setup

Create `claude_desktop_config.json`:
```json
{
  "mcpServers": {
    "meta-analysis": {
      "command": "python",
      "args": ["/absolute/path/to/server.py"],
      "env": {
        "RSCRIPT_TIMEOUT_SEC": "300",
        "DEBUG_R": "1",
        "SESSIONS_DIR": "/path/to/sessions"
      }
    }
  }
}
```

#### 2.2 Test Scenarios

1. **Basic Tool Discovery**
   ```
   User: "What tools do you have available for meta-analysis?"
   Expected: Claude lists all 8 available tools
   ```

2. **Session Management**
   ```
   User: "Start a new meta-analysis for clinical trials using odds ratios"
   Expected: Claude calls initialize_meta_analysis with correct parameters
   ```

3. **Data Upload**
   ```
   User: "Here's my CSV data: [paste data]"
   Expected: Claude encodes and uploads data correctly
   ```

4. **Analysis Workflow**
   ```
   User: "Perform a complete meta-analysis with forest plot and bias assessment"
   Expected: Claude orchestrates multiple tool calls in sequence
   ```

### Phase 3: Cursor Integration

#### 3.1 Native Gradio MCP Server Setup

Modify `gradio_native_mcp.py` to enable true MCP:
```python
if __name__ == "__main__":
    app = create_gradio_app()
    app.launch(
        server_name="0.0.0.0",
        server_port=7860,
        mcp_server=True  # Enable MCP server
    )
```

#### 3.2 Cursor Configuration

```json
{
  "mcpServers": {
    "meta-analysis-gradio": {
      "url": "http://127.0.0.1:7860/gradio_api/mcp/sse"
    }
  }
}
```

#### 3.3 Test Cases

1. **SSE Transport Verification**
   - Confirm SSE endpoint is accessible
   - Test real-time updates during analysis

2. **Tool Invocation via Cursor**
   - Use Cursor's agent mode
   - Test each tool individually
   - Verify response formatting

### Phase 4: Standard MCP Compliance

#### 4.1 Implement MCP-Compliant Server

Create `mcp_standard_server.py`:
```python
from mcp import Server, Tool
import asyncio

class MetaAnalysisMCPServer(Server):
    def __init__(self):
        super().__init__("meta-analysis-server")
        self.register_tools()
    
    def register_tools(self):
        # Register all 8 tools with proper schemas
        pass
    
    async def handle_initialize_meta_analysis(self, params):
        # Implement tool logic
        pass

if __name__ == "__main__":
    server = MetaAnalysisMCPServer()
    asyncio.run(server.run_stdio())
```

#### 4.2 Compliance Testing

1. **Protocol Validation**
   - Test against MCP specification
   - Verify JSON-RPC 2.0 compliance
   - Check error response formats

2. **Transport Testing**
   - stdio transport (Claude Desktop)
   - SSE transport (Cursor)
   - WebSocket transport (future)

### Phase 5: Performance & Reliability

#### 5.1 Load Testing

```python
def test_concurrent_sessions():
    """Test multiple simultaneous sessions"""
    # Create 10 concurrent sessions
    # Run analyses in parallel
    # Verify no cross-contamination

def test_memory_usage():
    """Monitor memory during large analyses"""
    # Process 10,000 study dataset
    # Monitor Python and R memory
    # Verify cleanup after completion
```

#### 5.2 Error Recovery

```python
def test_r_script_failure_recovery():
    """Test graceful handling of R failures"""
    # Cause intentional R error
    # Verify error message clarity
    # Confirm server remains operational

def test_session_recovery():
    """Test session persistence"""
    # Start analysis
    # Kill and restart server
    # Resume from saved session
```

### Phase 6: Security Testing

#### 6.1 Input Validation

```python
def test_injection_prevention():
    """Test against code injection"""
    # Try R code injection in data
    # Try shell command injection
    # Verify all are blocked

def test_file_path_traversal():
    """Test path traversal prevention"""
    # Try accessing files outside session
    # Verify access is restricted
```

#### 6.2 Resource Limits

```python
def test_resource_limits():
    """Test resource consumption limits"""
    # Upload 100MB file (should fail)
    # Run 1-hour analysis (should timeout)
    # Create 1000 sessions (should limit)
```

## Implementation Roadmap

### Week 1: Core Testing
- [ ] Implement unit tests for current server.py
- [ ] Create integration test suite
- [ ] Document test results

### Week 2: Claude Desktop Integration
- [ ] Configure Claude Desktop
- [ ] Test all 8 tools via Claude
- [ ] Document conversation patterns

### Week 3: Gradio MCP Enhancement
- [ ] Enable native MCP in Gradio
- [ ] Test with Cursor
- [ ] Compare stdio vs SSE performance

### Week 4: Standards Compliance
- [ ] Implement standard MCP server
- [ ] Validate against specification
- [ ] Performance benchmarking

## Success Metrics

1. **Functional Coverage**
   - 100% of tools testable via Claude Desktop
   - 100% of tools testable via Cursor
   - Full workflow completion rate > 95%

2. **Performance**
   - Response time < 2s for simple tools
   - Analysis completion < 30s for 100 studies
   - Memory usage < 500MB per session

3. **Reliability**
   - Server uptime > 99.9%
   - Error recovery success rate > 95%
   - No data loss during failures

4. **Security**
   - Zero code injection vulnerabilities
   - Zero unauthorized file access
   - All inputs properly validated

## Testing Tools & Resources

### Required Software
- Python 3.8+
- R 4.0+
- Claude Desktop (latest)
- Cursor IDE (latest)
- pytest for Python testing
- testthat for R testing

### Environment Variables
```bash
export RSCRIPT_BIN=/usr/local/bin/Rscript
export RSCRIPT_TIMEOUT_SEC=300
export DEBUG_R=1
export SESSIONS_DIR=/tmp/test_sessions
export GRADIO_MCP_SERVER=True
```

### Monitoring Tools
- Process monitoring: `htop`, `ps`
- Network monitoring: `netstat`, `tcpdump`
- Log aggregation: `tail -f *.log`

## Appendix: Current Tool Inventory

1. **initialize_meta_analysis** - Create new analysis session
2. **upload_study_data** - Upload CSV/Excel data
3. **perform_meta_analysis** - Run statistical analysis
4. **generate_forest_plot** - Create visualization
5. **assess_publication_bias** - Test for bias
6. **generate_report** - Create HTML/PDF report
7. **get_session_status** - Check progress
8. **health_check** - Verify system status

## Next Steps

1. **Immediate Actions**
   - Run existing test_subprocess_bridge.py
   - Verify all tools work with current implementation
   - Document any failures

2. **Short-term (1-2 weeks)**
   - Implement Phase 1 unit tests
   - Test Claude Desktop integration
   - Fix any discovered issues

3. **Medium-term (3-4 weeks)**
   - Enhance Gradio MCP compliance
   - Implement SSE transport
   - Add resource management

4. **Long-term (1-2 months)**
   - Full MCP specification compliance
   - Production deployment readiness
   - Performance optimization

## Contact & Support

- **Project Lead**: [Your Name]
- **Technical Issues**: Open GitHub issue
- **Security Concerns**: Email security@project.com

---

*Last Updated: [Current Date]*
*Version: 1.0*
