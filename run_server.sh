#!/bin/bash
# Script to run the Alfred AI Agent API server

cd "$(dirname "$0")"
uvicorn core.main:app --host 0.0.0.0 --port 8000 --reload
