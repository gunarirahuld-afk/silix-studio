import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from app.routes import lint, simulate, schematic, health, synthesize

app = FastAPI(
    title="SILIX Studio",
    description=(
        "**Next-Gen Silicon RTL Engineering Platform.**\n\n"
        "Provides cloud-native RTL linting, latch-inference detection, educational advice, "
        "cycle-accurate simulation with IEEE 1364 VCD traces, WaveDrom timing diagrams, "
        "hardware block schematics, and logic synthesis with SkyWater 130nm ASIC area estimation."
    ),
    version="2.0.0-production",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Enable Cross-Origin Resource Sharing (CORS) for global browser access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register route modules
app.include_router(health.router)
app.include_router(lint.router)
app.include_router(simulate.router)
app.include_router(schematic.router)
app.include_router(synthesize.router)

# Mount static folder
static_dir = os.path.join(os.path.dirname(__file__), "static")
if os.path.isdir(static_dir):
    app.mount("/static", StaticFiles(directory=static_dir), name="static")

@app.get("/", include_in_schema=False)
def root():
    index_file = os.path.join(static_dir, "index.html")
    if os.path.isfile(index_file):
        return FileResponse(index_file)
    return {"message": "RTL Cloud API is online. Go to /docs for Swagger."}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
