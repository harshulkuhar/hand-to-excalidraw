#!/usr/bin/env bash

# Kill background processes (backend) when script exits
trap 'kill $BACKEND_PID 2>/dev/null' SIGINT SIGTERM EXIT

# Start Backend
echo "Starting Backend..."
eval "$(conda shell.bash hook)"
conda activate hand2excal
uvicorn app.server:app --reload --port 8000 
BACKEND_PID=$!
