"""
FastAPI server: Serves the frontend and provides the /api/convert endpoint.
"""

import json
import logging
from pathlib import Path

from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from .vision import extract_flowchart_from_bytes, extract_flowchart_from_text
from .excalidraw_builder import build_excalidraw

app = FastAPI(
    title="Hand2Excal",
    description="Convert handwritten flowcharts to Excalidraw files",
    version="0.1.0",
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(message)s", datefmt="%H:%M:%S")
log = logging.getLogger("hand2excal")

# CORS for Vite dev server
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173", "https://*.hf.space"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.post("/api/convert")
async def convert_image(file: UploadFile = File(...)):
    """
    Upload a handwritten flowchart image, returns Excalidraw JSON.
    """
    # Validate file type
    allowed_types = {
        "image/jpeg", "image/png", "image/webp",
        "image/gif", "image/bmp", "image/heic",
    }
    content_type = file.content_type or "image/jpeg"
    if content_type not in allowed_types:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type: {content_type}. Use JPG, PNG, or WebP.",
        )

    # Read image bytes
    image_bytes = await file.read()
    size_mb = len(image_bytes) / (1024 * 1024)
    if len(image_bytes) > 20 * 1024 * 1024:  # 20MB limit
        raise HTTPException(status_code=400, detail="Image too large. Max 20MB.")

    log.info(f"📸 Received: {file.filename} ({size_mb:.1f} MB, {content_type})")

    try:
        # Step 1: Extract flowchart data using Qwen
        log.info("🤖 Sending to Qwen for analysis...")
        flowchart_data = extract_flowchart_from_bytes(image_bytes, content_type)
        nodes = flowchart_data.get("nodes", [])
        arrows = flowchart_data.get("arrows", [])
        log.info(f"📐 Extracted: {len(nodes)} shapes, {len(arrows)} connections")
        for n in nodes:
            log.info(f"   🔷 {n.get('id')}: {n.get('type')} \"{n.get('label')}\" at ({n.get('x')},{n.get('y')})")
        for a in arrows:
            log.info(f"   ➡️  {a.get('from_id')} → {a.get('to_id')} \"{a.get('label', '')}\"")

        # Step 2: Build Excalidraw JSON
        log.info("🔧 Building Excalidraw file...")
        excalidraw_json = build_excalidraw(flowchart_data)
        log.info("✅ Conversion complete!")

        return JSONResponse(content={
            "success": True,
            "excalidraw": excalidraw_json,
            "metadata": {
                "nodes_count": len(nodes),
                "arrows_count": len(arrows),
            },
        })

    except ValueError as e:
        log.error(f"❌ Validation error: {e}")
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        log.error(f"❌ Conversion failed: {e}")
        raise HTTPException(status_code=500, detail=f"Conversion failed: {str(e)}")


from pydantic import BaseModel

class TextConvertRequest(BaseModel):
    text: str

@app.post("/api/convert-text")
async def convert_text(request: TextConvertRequest):
    """
    Upload a text document/process flow, returns Excalidraw JSON.
    """
    if not request.text or not request.text.strip():
        raise HTTPException(status_code=400, detail="Text cannot be empty.")

    log.info(f"📝 Received text for conversion ({len(request.text)} characters)")

    try:
        # Step 1: Extract flowchart data using Llama
        log.info("🤖 Sending to LLM for text analysis...")
        flowchart_data = extract_flowchart_from_text(request.text)
        nodes = flowchart_data.get("nodes", [])
        arrows = flowchart_data.get("arrows", [])
        log.info(f"📐 Extracted: {len(nodes)} shapes, {len(arrows)} connections")
        
        # Step 2: Build Excalidraw JSON
        log.info("🔧 Building Excalidraw file...")
        excalidraw_json = build_excalidraw(flowchart_data)
        log.info("✅ Text Conversion complete!")

        return JSONResponse(content={
            "success": True,
            "excalidraw": excalidraw_json,
            "metadata": {
                "nodes_count": len(nodes),
                "arrows_count": len(arrows),
            },
        })

    except ValueError as e:
        log.error(f"❌ Validation error: {e}")
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        log.error(f"❌ Conversion failed: {e}")
        raise HTTPException(status_code=500, detail=f"Conversion failed: {str(e)}")


@app.get("/api/health")
async def health():
    return {"status": "ok"}


# Serve frontend static files (production build)
class NoCacheStaticFiles(StaticFiles):
    def is_not_modified(self, response_headers, request_headers) -> bool:
        return False
    async def get_response(self, path: str, scope):
        response = await super().get_response(path, scope)
        if hasattr(response, 'headers') and getattr(response, 'media_type', None) == 'text/html':
            response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
            response.headers["Pragma"] = "no-cache"
            response.headers["Expires"] = "0"
        return response

frontend_dist = Path(__file__).parent.parent / "frontend" / "dist"
if frontend_dist.exists():
    app.mount("/", NoCacheStaticFiles(directory=str(frontend_dist), html=True), name="frontend")
