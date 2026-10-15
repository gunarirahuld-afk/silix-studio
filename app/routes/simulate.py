from fastapi import APIRouter, HTTPException
from app.models import SimulateRequest, SimulateResponse
from app.services.simulator import RTLSimulator

router = APIRouter(prefix="/v1/rtl", tags=["Simulation & Waveforms"])

@router.post("/simulate", response_model=SimulateResponse, summary="Simulate RTL and generate VCD / WaveDrom")
async def simulate_rtl(request: SimulateRequest):
    """
    Executes cycle-accurate hardware simulation:
    - Produces standard IEEE 1364 VCD (Value Change Dump) traces
    - Generates WaveDrom JSON for instant browser UI waveform rendering
    - Provides execution cycle logs
    """
    if not request.module_code or not request.module_code.strip():
        raise HTTPException(status_code=400, detail="Module code cannot be empty.")

    sim = RTLSimulator(
        module_code=request.module_code,
        testbench_code=request.testbench_code,
        cycles=request.cycles,
        top_module=request.top_module,
        reset_active_low=request.reset_active_low
    )
    return sim.run()
