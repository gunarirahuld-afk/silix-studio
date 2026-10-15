from fastapi import APIRouter, HTTPException
from app.models import SchematicRequest, SchematicResponse
from app.services.schematic import SchematicGenerator

router = APIRouter(prefix="/v1/rtl", tags=["Schematics & Structure"])

@router.post("/schematic", response_model=SchematicResponse, summary="Generate circuit schematic and port map")
async def generate_schematic(request: SchematicRequest):
    """
    Extracts module I/O ports, registers, and interconnects, and produces
    a Mermaid flowchart diagram representing the physical hardware topology.
    """
    if not request.code or not request.code.strip():
        raise HTTPException(status_code=400, detail="Code cannot be empty.")

    gen = SchematicGenerator(code=request.code, top_module=request.top_module)
    return gen.analyze()
