from fastapi import APIRouter, HTTPException
from app.services.synthesizer import RTLSynthesizer, SynthesizeRequest, SynthesizeResponse

router = APIRouter(prefix="/v1/rtl", tags=["Logic Synthesis & Cell Area"])

@router.post("/synthesize", response_model=SynthesizeResponse, summary="Synthesize RTL & calculate gate/ASIC area")
async def synthesize_rtl(request: SynthesizeRequest):
    """
    Synthesizes Verilog RTL and generates:
    - Standard cell count (D-Flip-Flops, Full Adders, MUXes, Logic Gates)
    - Estimated FPGA LUT utilization
    - Silicon Area in micrometers squared (um²) using SkyWater 130nm standard cells
    - Critical path timing delay (ns) and Maximum Clock Frequency (Fmax in MHz)
    """
    if not request.code or not request.code.strip():
        raise HTTPException(status_code=400, detail="Source code cannot be empty.")

    synth = RTLSynthesizer(code=request.code, target=request.target)
    return synth.synthesize()
