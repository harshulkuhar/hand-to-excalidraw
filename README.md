---
title: Hand2Excal
emoji: ✏️
colorFrom: purple
colorTo: blue
sdk: docker
app_port: 7860
---

# ✏️ Hand2Excal

Convert handwritten flowcharts into editable [Excalidraw](https://excalidraw.com) diagrams using **Qwen2.5-VL** AI vision model via HuggingFace Inference API.

## ✨ Features

- 📸 Upload a photo of your handwritten flowchart
- 🤖 AI extracts shapes, text, colors, and connections
- 📐 Generates a valid `.excalidraw` file with proper bindings
- 🖊️ Open directly in Excalidraw web app
- 🌙 Beautiful dark-themed web UI + CLI support

## 🚀 Quick Start

### Prerequisites

- [Conda](https://docs.conda.io/) (or Miniconda)
- [Node.js](https://nodejs.org/) 18+
- A [HuggingFace API token](https://huggingface.co/settings/tokens) with access to Qwen3-VL.

### 1. Set up the environment

```bash
# The conda env should already be created, but if not:
conda create -n hand2excal python=3.11 -y
conda activate hand2excal

# Install Python dependencies
pip install -e .
```

### 2. Configure your API token

Create a `.env` file in the project root with your HuggingFace token:

```
HF_API_TOKEN=hf_your_token_here
```

### 3. Run the web app

```bash
# Terminal 1: Start the backend
conda activate hand2excal
uvicorn app.server:app --reload --port 8000

# Terminal 2: Start the frontend
cd frontend
npm run dev
```

Open [http://localhost:5173](http://localhost:5173) in your browser.

### 4. CLI usage

```bash
conda activate hand2excal
python -m app.cli path/to/photo.jpg -o flowchart.excalidraw
```

## 🛠️ Tech Stack

| Component | Technology |
|-----------|-----------|
| AI Model | Qwen2.5-VL-72B-Instruct via HuggingFace |
| Backend | Python, FastAPI |
| Frontend | Vite + React |
| Output | Excalidraw JSON format |

## 📁 Project Structure

```
hand2excal/
├── app/
│   ├── vision.py              # Qwen2.5-VL image analysis
│   ├── excalidraw_builder.py  # Excalidraw JSON generator
│   ├── server.py              # FastAPI endpoints
│   └── cli.py                 # CLI interface
├── frontend/
│   └── src/
│       ├── App.jsx            # Main app (state machine)
│       ├── components/
│       │   ├── UploadZone.jsx # Drag-and-drop upload
│       │   └── ResultPanel.jsx# Download & open results
│       └── index.css          # Dark theme + animations
├── .env.example               # API token template
└── pyproject.toml             # Python project config
```
