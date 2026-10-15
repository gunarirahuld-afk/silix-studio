from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field

# ============================================================================
# Linting & Pedagogical Diagnostics
# ============================================================================
class LintRequest(BaseModel):
    code: str = Field(..., description="Verilog or SystemVerilog source code")
    top_module: Optional[str] = Field(None, description="Name of the top-level module (optional)")
    strict_mode: bool = Field(False, description="Treat best-practice warnings as errors")

class LintIssue(BaseModel):
    line: Optional[int] = Field(None, description="Line number of the issue")
    severity: str = Field(..., description="Severity level: 'error', 'warning', or 'tip'")
    rule: str = Field(..., description="Identifier of the rule violated")
    message: str = Field(..., description="Short diagnostic message")
    explanation: str = Field(..., description="Detailed explanation of the hardware concept for students & freshers")
    fix_suggestion: str = Field(..., description="Recommended code pattern or fix")

class LintResponse(BaseModel):
    valid: bool
    module_name: Optional[str]
    total_errors: int
    total_warnings: int
    total_tips: int
    issues: List[LintIssue]
    pedagogical_summary: str

# ============================================================================
# Simulation & Waveform Generation
# ============================================================================
class SimulateRequest(BaseModel):
    module_code: str = Field(..., description="RTL module source code (Verilog)")
    testbench_code: Optional[str] = Field(None, description="Optional custom testbench code")
    cycles: int = Field(16, ge=1, le=1024, description="Number of clock cycles to simulate")
    top_module: Optional[str] = Field(None, description="Top module name")
    reset_active_low: bool = Field(True, description="True if reset is active low (rst_n), False if active high (rst)")

class WaveDromSignal(BaseModel):
    name: str
    wave: str
    data: Optional[List[str]] = None

class WaveDromData(BaseModel):
    signal: List[Dict[str, Any]]

class SimulateResponse(BaseModel):
    success: bool
    module_name: str
    cycles_simulated: int
    signals: List[str]
    vcd_content: str = Field(..., description="Standard IEEE 1364 VCD output")
    wavedrom: Dict[str, Any] = Field(..., description="WaveDrom JSON for rendering browser waveforms")
    console_log: str

# ============================================================================
# Circuit Schematic & Structural Analysis
# ============================================================================
class SchematicRequest(BaseModel):
    code: str = Field(..., description="Verilog source code")
    top_module: Optional[str] = Field(None, description="Top module name")

class PortInfo(BaseModel):
    direction: str  # input, output, inout
    name: str
    width: int
    range_str: str

class RegisterInfo(BaseModel):
    name: str
    width: int
    clock: Optional[str]
    reset: Optional[str]

class SchematicBlock(BaseModel):
    id: str
    type: str  # 'gate', 'mux', 'alu', 'dff', 'fsm', 'counter', 'logic'
    label: str
    subtext: Optional[str] = ""
    inputs: List[str]
    outputs: List[str]
    verilog_snippet: Optional[str] = ""
    internal_components: Optional[List[str]] = []
    bit_width: Optional[int] = 1

class SchematicResponse(BaseModel):
    module_name: str
    ports: List[PortInfo]
    registers: List[RegisterInfo]
    wires: List[str]
    mermaid_diagram: str
    summary: str
    blocks: Optional[List[SchematicBlock]] = []
