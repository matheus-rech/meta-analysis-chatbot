from fastapi import FastAPI
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, conlist, confloat
import gradio as gr

from app import build_ui, call_tool, R_STATUS, PY_STATUS


app = FastAPI(title="MCP Meta-Analysis PoC API (typed endpoints)")

demo = build_ui()
app = gr.mount_gradio_app(app, demo, path="/")


@app.get("/api/health")
def health():
    return {"r_status": R_STATUS, "python_status": PY_STATUS}


class InitializeRequest(BaseModel):
    name: str
    study_type: str = Field(pattern=r"^(clinical_trial|observational|diagnostic)$")
    effect_measure: str = Field(pattern=r"^(OR|RR|MD|SMD|HR|PROP|MEAN)$")
    analysis_model: str = Field(pattern=r"^(fixed|random|auto)$")


@app.post("/api/initialize_meta_analysis")
def initialize_meta_analysis(req: InitializeRequest):
    try:
        result = call_tool("initialize_meta_analysis", req.model_dump())
        return JSONResponse(content={"status": "ok", "result": result})
    except Exception as e:
        return JSONResponse(status_code=500, content={"status": "error", "message": str(e)})


class UploadRequest(BaseModel):
    session_id: str
    data_format: str = Field(pattern=r"^(csv|excel|revman)$")
    # Provide either data_content (base64) or csv_text for PoC convenience, but not both
    data_content: Optional[str] = None
    csv_text: Optional[str] = None
    validation_level: str = Field(pattern=r"^(basic|comprehensive)$")

    @model_validator(mode='before')
    def check_mutually_exclusive(cls, values):
        data_content = values.get("data_content")
        csv_text = values.get("csv_text")
        if (data_content is None and csv_text is None) or (data_content is not None and csv_text is not None):
            raise ValueError("Provide either data_content or csv_text, but not both.")
        return values


@app.post("/api/upload_study_data")
def upload_study_data(req: UploadRequest):
    try:
        payload = req.model_dump()
        if not payload.get("data_content") and payload.get("csv_text"):
            import base64 as _b64
            payload["data_content"] = _b64.b64encode(payload["csv_text"].encode("utf-8")).decode("ascii")
            payload.pop("csv_text", None)
        result = call_tool("upload_study_data", payload)
        return JSONResponse(content={"status": "ok", "result": result})
    except Exception as e:
        return JSONResponse(status_code=500, content={"status": "error", "message": str(e)})


class PerformRequest(BaseModel):
    session_id: str
    heterogeneity_test: bool = True
    publication_bias: bool = True
    sensitivity_analysis: bool = False


@app.post("/api/perform_meta_analysis")
def perform_meta_analysis(req: PerformRequest):
    try:
        result = call_tool("perform_meta_analysis", req.model_dump())
        return JSONResponse(content={"status": "ok", "result": result})
    except Exception as e:
        return JSONResponse(status_code=500, content={"status": "error", "message": str(e)})


class ForestPlotRequest(BaseModel):
    session_id: str
    plot_style: str = Field(pattern=r"^(classic|modern|journal_specific)$")
    confidence_level: confloat(gt=0, lt=1) = 0.95
    custom_labels: Optional[dict] = None


@app.post("/api/generate_forest_plot")
def generate_forest_plot(req: ForestPlotRequest):
    try:
        result = call_tool("generate_forest_plot", req.model_dump())
        return JSONResponse(content={"status": "ok", "result": result})
    except Exception as e:
        return JSONResponse(status_code=500, content={"status": "error", "message": str(e)})


class PublicationBiasRequest(BaseModel):
    session_id: str
    methods: conlist(str, min_length=1)


@app.post("/api/assess_publication_bias")
def assess_publication_bias(req: PublicationBiasRequest):
    try:
        result = call_tool("assess_publication_bias", req.model_dump())
        return JSONResponse(content={"status": "ok", "result": result})
    except Exception as e:
        return JSONResponse(status_code=500, content={"status": "error", "message": str(e)})


class GenerateReportRequest(BaseModel):
    session_id: str
    format: str = Field(pattern=r"^(html|pdf|word)$")
    include_code: bool = False
    journal_template: Optional[str] = None


@app.post("/api/generate_report")
def generate_report(req: GenerateReportRequest):
    try:
        result = call_tool("generate_report", req.model_dump())
        return JSONResponse(content={"status": "ok", "result": result})
    except Exception as e:
        return JSONResponse(status_code=500, content={"status": "error", "message": str(e)})


class SessionStatusRequest(BaseModel):
    session_id: str


@app.post("/api/get_session_status")
def get_session_status(req: SessionStatusRequest):
    try:
        result = call_tool("get_session_status", req.model_dump())
        return JSONResponse(content={"status": "ok", "result": result})
    except Exception as e:
        return JSONResponse(status_code=500, content={"status": "error", "message": str(e)})


# Optional: expose the same tools via fastmcp under /mcp
try:
    from fastmcp import FastMCP

    fmcp = FastMCP()

    @fmcp.tool("health_check")
    def fmcp_health_check(detailed: bool = False):
        return call_tool("health_check", {"detailed": detailed})

    @fmcp.tool("initialize_meta_analysis")
    def fmcp_initialize(name: str, study_type: str, effect_measure: str, analysis_model: str):
        return call_tool(
            "initialize_meta_analysis",
            {
                "name": name,
                "study_type": study_type,
                "effect_measure": effect_measure,
                "analysis_model": analysis_model,
            },
        )

    @fmcp.tool("upload_study_data")
    def fmcp_upload(session_id: str, data_format: str, data_content: str, validation_level: str):
        return call_tool(
            "upload_study_data",
            {
                "session_id": session_id,
                "data_format": data_format,
                "data_content": data_content,
                "validation_level": validation_level,
            },
        )

    @fmcp.tool("perform_meta_analysis")
    def fmcp_perform(session_id: str, heterogeneity_test: bool = True, publication_bias: bool = True, sensitivity_analysis: bool = False):
        return call_tool(
            "perform_meta_analysis",
            {
                "session_id": session_id,
                "heterogeneity_test": heterogeneity_test,
                "publication_bias": publication_bias,
                "sensitivity_analysis": sensitivity_analysis,
            },
        )

    @fmcp.tool("generate_forest_plot")
    def fmcp_forest(session_id: str, plot_style: str = "classic", confidence_level: float = 0.95):
        return call_tool(
            "generate_forest_plot",
            {
                "session_id": session_id,
                "plot_style": plot_style,
                "confidence_level": confidence_level,
            },
        )

    @fmcp.tool("assess_publication_bias")
    def fmcp_bias(session_id: str, methods: List[str]):
        return call_tool(
            "assess_publication_bias",
            {
                "session_id": session_id,
                "methods": methods,
            },
        )

    @fmcp.tool("generate_report")
    def fmcp_report(session_id: str, format: str = "html", include_code: bool = False):
        return call_tool(
            "generate_report",
            {
                "session_id": session_id,
                "format": format,
                "include_code": include_code,
            },
        )

    @fmcp.tool("get_session_status")
    def fmcp_status(session_id: str):
        return call_tool("get_session_status", {"session_id": session_id})

    # Mount fastmcp router at /mcp
    app.include_router(fmcp.router, prefix="/mcp")
except Exception as _e:
    # fastmcp not available; plain FastAPI routes remain available
    pass
