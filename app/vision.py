"""
Vision module: Uses Qwen2.5-VL via HuggingFace Inference API
to extract structured flowchart data from handwritten images.
"""

import base64
import io
import json
import os
import re
from pathlib import Path

from PIL import Image
try:
    import pillow_heif
    pillow_heif.register_heif_opener()
except ImportError:
    pass  # HEIC support optional

from dotenv import load_dotenv
from huggingface_hub import InferenceClient

load_dotenv()

QWEN_MODEL = "Qwen/Qwen2.5-VL-7B-Instruct"
# QWEN_MODEL = "Qwen/Qwen3-VL-235B-A22B-Instruct"
TEXT_MODEL = "meta-llama/Meta-Llama-3-8B-Instruct"

SYSTEM_PROMPT = """You are an expert at analyzing handwritten flowcharts and diagrams. 
Given an image of a handwritten flowchart, you must extract ALL shapes, text, and connections into a precise structured JSON format.

Rules:
1. Identify every shape: rectangles, rounded rectangles, ellipses/ovals, diamonds, squares.
2. Read ALL text inside or near each shape accurately.
3. Identify ALL arrows/connections between shapes, including any labels on them.
4. Estimate the relative position (x, y) and size (width, height) of each shape.
   - Use a coordinate system where top-left is (0, 0).
   - Estimate positions in pixels assuming a 1200x900 canvas.
   - IMPORTANT: Space shapes far apart. Minimum 120px gap between connected shapes.
   - Shapes should NOT overlap. Leave plenty of room for arrows between them.
   - Try to match the spatial layout from the original image (which shapes are on the left, right, top, bottom).
5. Detect colors if visible (use CSS color names). Default to "#1e1e1e" for strokes and "transparent" for fills.
6. Map shape types: 
   - Rectangles/squares → "rectangle"
   - Rounded rectangles → "rectangle" (with roundness flag)
   - Ovals/circles/ellipses → "ellipse"  
   - Diamonds/rhombus → "diamond"

Return ONLY valid JSON with this exact structure (no markdown, no explanation):
{
  "nodes": [
    {
      "id": "node_1",
      "type": "rectangle",
      "label": "Text inside the shape",
      "x": 300,
      "y": 50,
      "width": 160,
      "height": 60,
      "strokeColor": "#1e1e1e",
      "backgroundColor": "transparent",
      "rounded": false
    }
  ],
  "arrows": [
    {
      "from_id": "node_1",
      "to_id": "node_2",
      "label": "optional label on arrow",
      "strokeColor": "#1e1e1e"
    }
  ]
}

Important:
- Every node MUST have a unique id starting with "node_"
- Arrow from_id and to_id MUST reference valid node ids
- Labels must capture the actual text from the image 
- Positions should roughly match the spatial layout in the image
- CRITICAL: Do NOT miss any arrows! Count all arrows in the image before responding.
  - Text written near an arrow line (like "Yes", "No", "Registration", etc.) is an arrow LABEL, not a separate node.
  - If you see a line/arrow from shape A to shape B with text "X" written near it, create an arrow with from_id=A, to_id=B, label="X".
  - Every arrow drawn in the image MUST appear in the "arrows" array.
- Return ONLY the JSON object, nothing else"""


TEXT_SYSTEM_PROMPT = """You are an expert at analyzing process flows, documents, and textual descriptions to generate structured flowcharts.
Given a text description, you must extract ALL logical steps, decisions, and connections into a precise structured JSON format.

Rules:
1. Identify every logical step or decision as a shape:
   - Normal steps/actions → "rectangle"
   - Decisions/Questions (IF/THEN) → "diamond"
   - Start/End points → "ellipse"
2. Create concise labels for each shape based on the text.
3. Identify ALL connections (arrows) between steps, including labels for conditional paths (e.g., "Yes", "No", "If valid").
4. Estimate the relative position (x, y) and size (width, height) of each shape to create a clean, readable layout.
   - Use a coordinate system where top-left is (0, 0).
   - Layout the flowchart logically (e.g., top-to-bottom or left-to-right).
   - IMPORTANT: Space shapes far apart. Minimum 120px gap between connected shapes.
   - Shapes should NOT overlap. Leave plenty of room for arrows between them.
5. Default to "#1e1e1e" for strokes and "transparent" for fills, unless the text implies a specific color (e.g., "warning step" -> "red").

Return ONLY valid JSON with this exact structure (no markdown, no explanation):
{
  "nodes": [
    {
      "id": "node_1",
      "type": "rectangle",
      "label": "Text inside the shape",
      "x": 300,
      "y": 50,
      "width": 160,
      "height": 60,
      "strokeColor": "#1e1e1e",
      "backgroundColor": "transparent",
      "rounded": false
    }
  ],
  "arrows": [
    {
      "from_id": "node_1",
      "to_id": "node_2",
      "label": "optional label on arrow",
      "strokeColor": "#1e1e1e"
    }
  ]
}

Important:
- Every node MUST have a unique id starting with "node_"
- Arrow from_id and to_id MUST reference valid node ids
- Return ONLY the JSON object, nothing else"""


def _image_to_data_url(image_path: str) -> str:
    """Convert a local image to a base64 data URL, converting unsupported formats."""
    path = Path(image_path)
    suffix = path.suffix.lower()
    mime_map = {
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".png": "image/png",
        ".webp": "image/webp",
        ".gif": "image/gif",
        ".bmp": "image/bmp",
        ".heic": "image/heic",
    }
    content_type = mime_map.get(suffix, "image/jpeg")
    image_bytes = path.read_bytes()
    image_bytes, content_type = _ensure_jpeg(image_bytes, content_type)
    b64 = base64.b64encode(image_bytes).decode("utf-8")
    return f"data:{content_type};base64,{b64}"


def _ensure_jpeg(image_bytes: bytes, content_type: str) -> tuple[bytes, str]:
    """Resize and convert images to JPEG for the API (keeps payload small)."""
    img = Image.open(io.BytesIO(image_bytes))
    img = img.convert("RGB")

    # Resize if larger than 1200px on any side
    max_dim = 1200
    if max(img.size) > max_dim:
        img.thumbnail((max_dim, max_dim), Image.LANCZOS)

    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=85)
    return buf.getvalue(), "image/jpeg"


def _image_bytes_to_data_url(image_bytes: bytes, content_type: str = "image/jpeg") -> str:
    """Convert image bytes to a base64 data URL, converting unsupported formats first."""
    image_bytes, content_type = _ensure_jpeg(image_bytes, content_type)
    b64 = base64.b64encode(image_bytes).decode("utf-8")
    return f"data:{content_type};base64,{b64}"


def _extract_json(text: str) -> dict:
    """Extract JSON from model response, handling markdown fences."""
    # Try direct parse first
    text = text.strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # Try extracting from markdown code fence
    match = re.search(r"```(?:json)?\s*\n?(.*?)\n?\s*```", text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(1).strip())
        except json.JSONDecodeError:
            pass

    # Try finding first { ... } block
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(0))
        except json.JSONDecodeError:
            pass

    raise ValueError(f"Could not extract valid JSON from model response:\n{text[:500]}")


def _validate_flowchart_data(data: dict) -> dict:
    """Validate and normalize the extracted flowchart data."""
    if "nodes" not in data:
        raise ValueError("Missing 'nodes' in extracted data")
    if "arrows" not in data:
        data["arrows"] = []

    node_ids = set()
    for i, node in enumerate(data["nodes"]):
        if "id" not in node:
            node["id"] = f"node_{i + 1}"
        node_ids.add(node["id"])

        # Defaults
        node.setdefault("type", "rectangle")
        node.setdefault("label", "")
        node.setdefault("x", 100 + (i % 4) * 200)
        node.setdefault("y", 100 + (i // 4) * 150)
        node.setdefault("width", 150)
        node.setdefault("height", 60)
        node.setdefault("strokeColor", "#1e1e1e")
        node.setdefault("backgroundColor", "transparent")
        node.setdefault("rounded", False)

        # Clamp type
        if node["type"] not in ("rectangle", "ellipse", "diamond"):
            node["type"] = "rectangle"

    # Validate arrows
    valid_arrows = []
    for arrow in data["arrows"]:
        if arrow.get("from_id") in node_ids and arrow.get("to_id") in node_ids:
            arrow.setdefault("label", "")
            arrow.setdefault("strokeColor", "#1e1e1e")
            valid_arrows.append(arrow)

    data["arrows"] = valid_arrows
    return data


def extract_flowchart_from_image(image_path: str) -> dict:
    """
    Extract flowchart structure from a handwritten image file.
    Returns validated dict with 'nodes' and 'arrows'.
    """
    token = os.getenv("HF_API_TOKEN")
    if not token:
        raise ValueError("HF_API_TOKEN not set. Copy .env.example to .env and add your token.")

    client = InferenceClient(token=token)
    data_url = _image_to_data_url(image_path)

    response = client.chat_completion(
        model=QWEN_MODEL,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {
                "role": "user",
                "content": [
                    {"type": "image_url", "image_url": {"url": data_url}},
                    {
                        "type": "text",
                        "text": "Analyze this handwritten flowchart and extract all shapes, text, and connections into the JSON format specified.",
                    },
                ],
            },
        ],
        max_tokens=4096,
        temperature=0.1,
    )

    raw_text = response.choices[0].message.content
    flowchart_data = _extract_json(raw_text)
    return _validate_flowchart_data(flowchart_data)


def extract_flowchart_from_bytes(image_bytes: bytes, content_type: str = "image/jpeg") -> dict:
    """
    Extract flowchart structure from image bytes (used by the API endpoint).
    Returns validated dict with 'nodes' and 'arrows'.
    """
    token = os.getenv("HF_API_TOKEN")
    if not token:
        raise ValueError("HF_API_TOKEN not set. Copy .env.example to .env and add your token.")

    client = InferenceClient(token=token)
    data_url = _image_bytes_to_data_url(image_bytes, content_type)

    response = client.chat_completion(
        model=QWEN_MODEL,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {
                "role": "user",
                "content": [
                    {"type": "image_url", "image_url": {"url": data_url}},
                    {
                        "type": "text",
                        "text": "Analyze this handwritten flowchart and extract all shapes, text, and connections into the JSON format specified.",
                    },
                ],
            },
        ],
        max_tokens=4096,
        temperature=0.1,
    )

    raw_text = response.choices[0].message.content
    flowchart_data = _extract_json(raw_text)
    return _validate_flowchart_data(flowchart_data)


def extract_flowchart_from_text(text: str) -> dict:
    """
    Extract flowchart structure from text description.
    Returns validated dict with 'nodes' and 'arrows'.
    """
    token = os.getenv("HF_API_TOKEN")
    if not token:
        raise ValueError("HF_API_TOKEN not set. Copy .env.example to .env and add your token.")

    client = InferenceClient(token=token)

    response = client.chat_completion(
        model=TEXT_MODEL,
        messages=[
            {"role": "system", "content": TEXT_SYSTEM_PROMPT},
            {
                "role": "user",
                "content": text,
            },
        ],
        max_tokens=4096,
        temperature=0.1,
    )

    raw_text = response.choices[0].message.content
    flowchart_data = _extract_json(raw_text)
    return _validate_flowchart_data(flowchart_data)
