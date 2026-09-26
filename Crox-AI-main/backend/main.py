from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from postgrest.exceptions import APIError as PostgrestAPIError

from agent.gemini_client import GeminiNotConfigured
from api.routes import router
from config import get_settings
from database.client import SupabaseNotConfigured

app = FastAPI(title="WorkFlowOS Backend")


@app.exception_handler(SupabaseNotConfigured)
async def supabase_not_configured_handler(request: Request, exc: SupabaseNotConfigured):
    return JSONResponse(status_code=503, content={"detail": str(exc)})


@app.exception_handler(GeminiNotConfigured)
async def gemini_not_configured_handler(request: Request, exc: GeminiNotConfigured):
    return JSONResponse(status_code=503, content={"detail": str(exc)})


@app.exception_handler(PostgrestAPIError)
async def postgrest_error_handler(request: Request, exc: PostgrestAPIError):
    if exc.code == "PGRST205":
        return JSONResponse(
            status_code=503,
            content={
                "detail": (
                    "Supabase schema not found -- run supabase/migrations/0001_init.sql "
                    "in your project's SQL editor before using the app."
                )
            },
        )
    return JSONResponse(status_code=502, content={"detail": f"Supabase error: {exc.message}"})

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Electron renderer runs on a file:// / app:// origin during packaging
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)


@app.get("/health")
async def health():
    settings = get_settings()
    return {"status": "ok", "demo_mode": settings.demo_mode}


if __name__ == "__main__":
    import uvicorn

    settings = get_settings()
    uvicorn.run("main:app", host=settings.backend_host, port=settings.backend_port, reload=True)
