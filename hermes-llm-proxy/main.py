from fastapi import FastAPI
from router import router as proxy_router

app = FastAPI(
    title="Hermes LLM Proxy",
    description="Internal OpenAI-compatible API router that reads credentials directly from database and decrypts them.",
    version="1.0.0"
)


@app.get("/health")
async def health():
    return {"status": "healthy"}

app.include_router(proxy_router)