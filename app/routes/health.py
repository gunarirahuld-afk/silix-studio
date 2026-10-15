from fastapi import APIRouter

router = APIRouter(tags=["Health & Status"])

@router.get("/health", summary="API Health Check")
async def health_check():
    return {
        "status": "online",
        "service": "Silix Cloud Semiconductor Studio",
        "version": "2.0.0-production",
        "engine": "SkyWater 130nm & Event-Driven Cycle Core",
        "docs_url": "/docs"
    }

@router.get("/v1/info", summary="Supported EDA Capabilities")
async def api_info():
    return {
        "name": "Silix Cloud Semiconductor Studio",
        "description": "Next-Gen Cloud RTL & ASIC Verification Platform for students, freshers, and semiconductor teams worldwide.",
        "supported_languages": ["Verilog-2001", "Verilog-2005", "SystemVerilog (subset)"],
        "waveform_formats": ["IEEE-1364 VCD", "WaveDrom JSON"],
        "endpoints": [
            {"path": "/v1/rtl/lint", "method": "POST", "desc": "Hardware syntax linting & latch detection"},
            {"path": "/v1/rtl/simulate", "method": "POST", "desc": "Cycle-accurate simulation & waveform dump"},
            {"path": "/v1/rtl/schematic", "method": "POST", "desc": "Mermaid block diagram and port extraction"},
            {"path": "/v1/rtl/synthesize", "method": "POST", "desc": "SkyWater 130nm standard cell synthesis & area estimation"}
        ]
    }
