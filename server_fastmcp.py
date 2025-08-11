"""
Meta-Analysis MCP Server using FastMCP Pattern
Fully compliant with MCP specification using official SDK
"""

import os
import json
import asyncio
import subprocess
import tempfile
import uuid
from pathlib import Path
from typing import Optional, Dict, Any, List
from datetime import datetime

try:
    from fastmcp import FastMCP, Context
    FASTMCP_AVAILABLE = True
except ImportError:
    FASTMCP_AVAILABLE = False
    print("Warning: FastMCP not installed. Run: pip install fastmcp")

# Initialize FastMCP server (2.0 syntax)
mcp = FastMCP("Meta-Analysis Server 🔬")

# Server configuration
SESSIONS_DIR = Path(os.getenv("SESSIONS_DIR", "./sessions"))
SESSIONS_DIR.mkdir(exist_ok=True)
RSCRIPT_BIN = os.getenv("RSCRIPT_BIN", "Rscript")
SCRIPTS_PATH = Path(__file__).parent / "scripts"
MCP_TOOLS_PATH = SCRIPTS_PATH / "entry" / "mcp_tools.R"

# Session storage
sessions: Dict[str, Dict[str, Any]] = {}

# =====================================================================================
#  Helper Functions
# =====================================================================================

async def call_r_tool(tool_name: str, args: Dict[str, Any], session_path: str = None) -> Dict[str, Any]:
    """Execute R tool via subprocess"""
    session_dir = session_path or str(SESSIONS_DIR / "temp")
    
    # Write args to temp file
    fd, args_file = tempfile.mkstemp(suffix=".json")
    os.close(fd)
    
    try:
        with open(args_file, "w") as f:
            json.dump(args, f)
        
        # Execute R script
        process = await asyncio.create_subprocess_exec(
            RSCRIPT_BIN, "--vanilla",
            str(MCP_TOOLS_PATH),
            tool_name,
            args_file,
            session_dir,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        stdout, stderr = await process.communicate()
        
        if process.returncode != 0:
            error_msg = stderr.decode() if stderr else "R script failed"
            return {"status": "error", "error": error_msg}
        
        # Parse JSON response
        try:
            result = json.loads(stdout.decode())
            return result
        except json.JSONDecodeError:
            # Try to extract JSON from R output
            output = stdout.decode()
            json_start = output.find('{')
            if json_start >= 0:
                return json.loads(output[json_start:])
            return {"status": "error", "error": "Invalid R output", "raw": output}
            
    finally:
        if os.path.exists(args_file):
            os.remove(args_file)

def get_session_path(session_id: str) -> Path:
    """Get session directory path"""
    return SESSIONS_DIR / session_id

# =====================================================================================
#  MCP Tools (with FastMCP decorators)
# =====================================================================================

@mcp.tool
async def initialize_meta_analysis(
    name: str,
    study_type: str = "clinical_trial",
    effect_measure: str = "OR",
    analysis_model: str = "random",
    ctx: Optional[Context] = None
) -> Dict[str, Any]:
    """
    Initialize a new meta-analysis session
    
    Args:
        name: Project name
        study_type: Type of study (clinical_trial, observational, diagnostic)
        effect_measure: Effect measure (OR, RR, MD, SMD, HR, PROP, MEAN)
        analysis_model: Analysis model (fixed, random, auto)
        ctx: MCP context for logging
    
    Returns:
        Session initialization result with session_id
    """
    if ctx:
        ctx.info(f"Initializing meta-analysis: {name}")
    
    # Generate session ID
    session_id = uuid.uuid4().hex[:16]
    session_path = get_session_path(session_id)
    session_path.mkdir(parents=True, exist_ok=True)
    
    # Create session subdirectories
    for subdir in ["input", "processing", "results", "tmp"]:
        (session_path / subdir).mkdir(exist_ok=True)
    
    # Store session metadata
    session_meta = {
        "session_id": session_id,
        "name": name,
        "study_type": study_type,
        "effect_measure": effect_measure,
        "analysis_model": analysis_model,
        "created": datetime.now().isoformat(),
        "status": "initialized"
    }
    
    with open(session_path / "session.json", "w") as f:
        json.dump(session_meta, f, indent=2)
    
    # Store in memory
    sessions[session_id] = session_meta
    
    if ctx:
        ctx.info(f"Session created: {session_id}")
    
    return {
        "status": "success",
        "session_id": session_id,
        "message": f"Meta-analysis session '{name}' initialized",
        "configuration": {
            "study_type": study_type,
            "effect_measure": effect_measure,
            "analysis_model": analysis_model
        }
    }

@mcp.tool
async def upload_study_data(
    session_id: str,
    csv_content: str,
    data_format: str = "csv",
    validation_level: str = "comprehensive",
    ctx: Optional[Context] = None
) -> Dict[str, Any]:
    """
    Upload study data for analysis
    
    Args:
        session_id: Session identifier
        csv_content: CSV data content (base64 encoded or plain text)
        data_format: Format of data (csv, excel, revman)
        validation_level: Validation level (basic, comprehensive)
        ctx: MCP context
    
    Returns:
        Upload result with validation summary
    """
    if ctx:
        ctx.info(f"Uploading data to session {session_id}")
        ctx.progress(0.1, "Validating session...")
    
    session_path = get_session_path(session_id)
    if not session_path.exists():
        return {"status": "error", "error": "Session not found"}
    
    if ctx:
        ctx.progress(0.3, "Processing data...")
    
    # Call R tool
    result = await call_r_tool("upload_study_data", {
        "session_id": session_id,
        "csv_content": csv_content,
        "data_format": data_format,
        "validation_level": validation_level
    }, str(session_path))
    
    if ctx:
        if result.get("status") == "success":
            ctx.progress(1.0, "Data uploaded successfully")
            ctx.info(f"Uploaded {result.get('n_studies', 0)} studies")
        else:
            ctx.error(f"Upload failed: {result.get('error')}")
    
    return result

@mcp.tool
async def perform_meta_analysis(
    session_id: str,
    heterogeneity_test: bool = True,
    publication_bias: bool = True,
    sensitivity_analysis: bool = False,
    ctx: Optional[Context] = None
) -> Dict[str, Any]:
    """
    Execute meta-analysis on uploaded data
    
    Args:
        session_id: Session identifier
        heterogeneity_test: Test for heterogeneity
        publication_bias: Test for publication bias
        sensitivity_analysis: Perform sensitivity analysis
        ctx: MCP context
    
    Returns:
        Analysis results with statistics
    """
    if ctx:
        ctx.info(f"Starting meta-analysis for session {session_id}")
        ctx.progress(0.1, "Loading data...")
    
    session_path = get_session_path(session_id)
    
    if ctx:
        ctx.progress(0.3, "Running statistical analysis...")
    
    # Call R tool
    result = await call_r_tool("perform_meta_analysis", {
        "session_id": session_id,
        "heterogeneity_test": heterogeneity_test,
        "publication_bias": publication_bias,
        "sensitivity_analysis": sensitivity_analysis
    }, str(session_path))
    
    if ctx:
        if result.get("status") == "success":
            ctx.progress(0.8, "Generating summary...")
            summary = result.get("summary", {})
            ctx.info(f"Analysis complete: Effect={summary.get('estimate')}, I²={summary.get('i_squared')}%")
            ctx.progress(1.0, "Analysis complete")
        else:
            ctx.error(f"Analysis failed: {result.get('error')}")
    
    return result

@mcp.tool
async def generate_forest_plot(
    session_id: str,
    plot_style: str = "modern",
    confidence_level: float = 0.95,
    ctx: Optional[Context] = None
) -> Dict[str, Any]:
    """
    Generate forest plot visualization
    
    Args:
        session_id: Session identifier
        plot_style: Visual style (classic, modern, journal_specific)
        confidence_level: Confidence interval level
        ctx: MCP context
    
    Returns:
        Plot generation result with base64 image
    """
    if ctx:
        ctx.info(f"Generating forest plot for session {session_id}")
    
    session_path = get_session_path(session_id)
    
    result = await call_r_tool("generate_forest_plot", {
        "session_id": session_id,
        "plot_style": plot_style,
        "confidence_level": confidence_level
    }, str(session_path))
    
    if ctx and result.get("status") == "success":
        ctx.info("Forest plot generated successfully")
    
    return result

@mcp.tool
async def assess_publication_bias(
    session_id: str,
    methods: List[str] = None,
    ctx: Optional[Context] = None
) -> Dict[str, Any]:
    """
    Assess publication bias using multiple methods
    
    Args:
        session_id: Session identifier
        methods: List of methods (funnel_plot, egger_test, begg_test, trim_fill)
        ctx: MCP context
    
    Returns:
        Bias assessment results
    """
    if ctx:
        ctx.info(f"Assessing publication bias for session {session_id}")
    
    if methods is None:
        methods = ["funnel_plot", "egger_test"]
    
    session_path = get_session_path(session_id)
    
    result = await call_r_tool("assess_publication_bias", {
        "session_id": session_id,
        "methods": methods
    }, str(session_path))
    
    if ctx and result.get("status") == "success":
        ctx.info("Publication bias assessment complete")
    
    return result

@mcp.tool
async def generate_report(
    session_id: str,
    format: str = "html",
    include_code: bool = False,
    ctx: Optional[Context] = None
) -> Dict[str, Any]:
    """
    Generate comprehensive analysis report
    
    Args:
        session_id: Session identifier
        format: Report format (html, pdf, word)
        include_code: Include R code in report
        ctx: MCP context
    
    Returns:
        Report generation result with file path
    """
    if ctx:
        ctx.info(f"Generating {format.upper()} report for session {session_id}")
        ctx.progress(0.2, "Collecting results...")
    
    session_path = get_session_path(session_id)
    
    if ctx:
        ctx.progress(0.5, "Generating report...")
    
    result = await call_r_tool("generate_report", {
        "session_id": session_id,
        "format": format,
        "include_code": include_code
    }, str(session_path))
    
    if ctx:
        if result.get("status") == "success":
            ctx.progress(1.0, "Report generated")
            ctx.info(f"Report saved to: {result.get('report_path')}")
        else:
            ctx.error(f"Report generation failed: {result.get('error')}")
    
    return result

# =====================================================================================
#  MCP Resources (data exposure)
# =====================================================================================

@mcp.resource(uri="sessions")
async def list_sessions() -> List[Dict[str, Any]]:
    """
    List all analysis sessions
    
    Returns:
        List of session metadata
    """
    session_list = []
    
    for session_dir in SESSIONS_DIR.glob("*"):
        if session_dir.is_dir():
            session_file = session_dir / "session.json"
            if session_file.exists():
                with open(session_file) as f:
                    session_list.append(json.load(f))
    
    return sorted(session_list, key=lambda x: x.get("created", ""), reverse=True)

@mcp.resource(uri="session/{session_id}")
async def get_session_info(session_id: str) -> Dict[str, Any]:
    """
    Get detailed session information
    
    Args:
        session_id: Session identifier
    
    Returns:
        Session metadata and status
    """
    session_path = get_session_path(session_id)
    
    if not session_path.exists():
        return {"error": "Session not found"}
    
    # Load session metadata
    with open(session_path / "session.json") as f:
        session_meta = json.load(f)
    
    # Check for results
    results_file = session_path / "results" / "analysis_results.rds"
    has_results = results_file.exists()
    
    # Check for data
    data_file = session_path / "processing" / "processed_data.rds"
    has_data = data_file.exists()
    
    return {
        **session_meta,
        "has_data": has_data,
        "has_results": has_results,
        "path": str(session_path)
    }

@mcp.resource(uri="session/{session_id}/results")
async def get_analysis_results(session_id: str) -> Dict[str, Any]:
    """
    Get analysis results for a session
    
    Args:
        session_id: Session identifier
    
    Returns:
        Analysis results if available
    """
    # Call R to get results
    result = await call_r_tool("get_session_status", {
        "session_id": session_id
    }, str(get_session_path(session_id)))
    
    return result

# =====================================================================================
#  MCP Prompts (dynamic prompt generation)
# =====================================================================================

@mcp.prompt
async def meta_analysis_workflow() -> str:
    """
    Generate a comprehensive meta-analysis workflow prompt
    
    Returns:
        Workflow guidance prompt
    """
    return """You are an expert meta-analysis assistant using Cochrane guidelines.

## Workflow Steps:

1. **Initialize Session**
   - Use `initialize_meta_analysis` tool
   - Specify study type, effect measure, and model

2. **Upload Data**
   - Use `upload_study_data` tool
   - Ensure proper CSV format with required columns

3. **Perform Analysis**
   - Use `perform_meta_analysis` tool
   - Include heterogeneity and bias tests

4. **Generate Visualizations**
   - Use `generate_forest_plot` for main results
   - Use `assess_publication_bias` for bias plots

5. **Create Report**
   - Use `generate_report` for comprehensive output
   - Choose appropriate format (HTML, PDF, Word)

## Important Considerations:

- **Study Selection**: Follow PICO framework
- **Statistical Methods**: Choose appropriate model based on heterogeneity
- **Interpretation**: Consider clinical and statistical significance
- **Reporting**: Follow PRISMA guidelines

Always explain statistical concepts clearly and suggest appropriate next steps."""

@mcp.prompt
async def cochrane_guidance(
    analysis_stage: str = "planning"
) -> str:
    """
    Generate Cochrane-aligned guidance for specific analysis stage
    
    Args:
        analysis_stage: Current stage (planning, execution, interpretation)
    
    Returns:
        Stage-specific guidance
    """
    guidance_map = {
        "planning": """## Planning Your Meta-Analysis (Cochrane Guidelines)

1. **Define Clear Question** (PICO)
   - Population: Specific patient characteristics
   - Intervention: Treatment being evaluated
   - Comparator: Control or alternative treatment
   - Outcome: Primary and secondary endpoints

2. **Inclusion Criteria**
   - Study designs to include
   - Minimum quality standards
   - Language restrictions
   - Time period

3. **Statistical Considerations**
   - Choose effect measure based on outcome type
   - Plan for heterogeneity assessment
   - Consider subgroup analyses upfront""",
        
        "execution": """## Executing Your Meta-Analysis

1. **Data Extraction**
   - Use standardized forms
   - Double-check critical values
   - Document all decisions

2. **Statistical Analysis**
   - Start with fixed-effect if low heterogeneity expected
   - Use random-effects if clinical diversity exists
   - Always report I² and τ²

3. **Sensitivity Analyses**
   - Exclude high risk of bias studies
   - Test different statistical models
   - Explore influence of individual studies""",
        
        "interpretation": """## Interpreting Results

1. **Statistical Significance vs Clinical Importance**
   - Consider magnitude of effect
   - Evaluate confidence interval width
   - Assess practical implications

2. **Heterogeneity Interpretation**
   - I² < 40%: Low heterogeneity
   - I² 40-75%: Moderate heterogeneity
   - I² > 75%: High heterogeneity

3. **Publication Bias**
   - Requires ≥10 studies for reliable testing
   - Consider multiple assessment methods
   - Discuss potential impact on conclusions"""
    }
    
    base_prompt = f"""You are providing Cochrane-aligned guidance for meta-analysis.

Current Stage: {analysis_stage}

{guidance_map.get(analysis_stage, guidance_map["planning"])}

## Key Principles:
- Transparency in all decisions
- Systematic and reproducible methods
- Clear reporting of limitations
- Focus on clinical relevance

Always cite Cochrane Handbook when providing specific recommendations."""
    
    return base_prompt

# =====================================================================================
#  Server Lifecycle & Configuration
# =====================================================================================

async def setup_server():
    """Initialize server resources"""
    ctx.info("Meta-Analysis MCP Server starting...")
    
    # Verify R is available
    try:
        process = await asyncio.create_subprocess_exec(
            RSCRIPT_BIN, "--version",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        await process.communicate()
        if process.returncode == 0:
            ctx.info("R backend verified")
        else:
            ctx.error("R backend not available")
    except Exception as e:
        ctx.error(f"Failed to verify R: {e}")
    
    # Create necessary directories
    SESSIONS_DIR.mkdir(exist_ok=True)
    ctx.info(f"Sessions directory: {SESSIONS_DIR}")

async def cleanup_server():
    """Cleanup server resources"""
    ctx.info("Meta-Analysis MCP Server shutting down...")
    # Could add session cleanup here if needed

# =====================================================================================
#  Main Entry Point
# =====================================================================================

if __name__ == "__main__":
    import sys
    
    if not FASTMCP_AVAILABLE:
        print("Error: FastMCP not installed")
        print("Install with: pip install fastmcp")
        sys.exit(1)
    
    # Run the server (FastMCP 2.0 handles transports automatically)
    print("Starting Meta-Analysis MCP Server 🔬")
    print("Tools available: initialize, upload, analyze, plot, bias, report")
    print("Resources: sessions, results")
    print("Prompts: workflow guidance, Cochrane guidance")
    
    # Run with stdio by default (FastMCP 2.0 syntax)
    mcp.run()