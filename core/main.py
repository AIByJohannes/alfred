from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException

from llm import LLMEngine
from models import PromptRequest, PromptResponse
from prompts import FIBONACCI_PROMPT

# Global engine instance
engine = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    global engine
    try:
        engine = LLMEngine()
    except Exception as e:
        print(
            f"Failed to initialize LLM engine: {e}. "
            "API will still start; /run endpoints will return 503 until fixed."
        )
        engine = None
    yield
    # Shutdown
    engine = None


app = FastAPI(
    title="Alfred AI Agent API",
    description="A REST API for running AI agent tasks",
    version="1.0.0",
    lifespan=lifespan,
)


@app.get("/")
async def root():
    return {"message": "Alfred AI Agent API is running"}


@app.get("/health")
async def health_check():
    return {"status": "healthy", "engine_ready": engine is not None}


@app.post("/run", response_model=PromptResponse)
async def run_prompt(request: PromptRequest):
    """Run a prompt through the AI agent"""
    if engine is None:
        raise HTTPException(status_code=503, detail="Engine not initialized")

    try:
        result = engine.run(request.prompt)
        return PromptResponse(result=result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error running prompt: {str(e)}")


@app.get("/fibonacci")
async def run_fibonacci():
    """Run the default Fibonacci prompt"""
    if engine is None:
        raise HTTPException(status_code=503, detail="Engine not initialized")

    try:
        result = engine.run(FIBONACCI_PROMPT)
        return PromptResponse(result=result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error running Fibonacci prompt: {str(e)}")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
