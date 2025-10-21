#!/bin/bash
# Azure App Service startup script for FastAPI

# Run uvicorn on port 8000 (Azure will map this to 80/443)
python -m uvicorn src.api.main:app --host 0.0.0.0 --port 8000
