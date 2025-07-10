#!/usr/bin/env python3
"""
Simple API Test for process_13
"""

import os
import uvicorn
from fastapi import FastAPI
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

app = FastAPI(title="Process 13 Test API")

@app.get("/")
async def root():
    return {"message": "Process 13 is running!", "status": "operational"}

@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "process_13"}

@app.get("/ping")
async def ping():
    return {"message": "pong"}

@app.get("/test")
async def test_endpoint():
    return {
        "message": "Test endpoint working",
        "features": [
            "AI Learning Engine",
            "Dynamic Module Generator", 
            "Enhanced LLM Runner",
            "Real-time Streaming"
        ]
    }

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)