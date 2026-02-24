"""Main FastAPI application for Dental PMS wrapper."""

from fastapi import FastAPI
from api.infrastructure.global_exception_handler import global_exception_handler
from api.infrastructure.register_routers import register_routers


app = FastAPI(
    title="Dental PMS Wrapper API",
    description="Normalized wrapper around the DentalTrack Pro legacy PMS API",
    version="1.0.0",
)

app.middleware("http")(global_exception_handler)
register_routers(app)


@app.get("/")
async def root() -> dict[str, str]:
    """Root endpoint."""
    return {"message": "Dental PMS Wrapper API is running", "version": "1.0.0"}


@app.get("/health")
async def health() -> dict[str, str]:
    """Health endpoint."""
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("api.main:app", host="0.0.0.0", port=3000, reload=False)
