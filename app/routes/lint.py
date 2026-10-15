from fastapi import APIRouter, HTTPException
from app.models import LintRequest, LintResponse
from app.services.linter import VerilogLinter

router = APIRouter(prefix="/v1/rtl", tags=["Linting & Verification"])

@router.post("/lint", response_model=LintResponse, summary="Analyze and lint RTL code")
async def lint_rtl(request: LintRequest):
    """
    Analyzes Verilog / SystemVerilog code for:
    - Synthesizability and structural issues
    - Inferred latch hazards (missing default/else branches)
    - Blocking vs. non-blocking assignment violations
    - Multi-driven nets (dead shorts in silicon)
    - Educational advice tailored for students and freshers
    """
    if not request.code or not request.code.strip():
        raise HTTPException(status_code=400, detail="Source code cannot be empty.")
    
    linter = VerilogLinter(
        code=request.code,
        top_module=request.top_module,
        strict_mode=request.strict_mode
    )
    return linter.analyze()
