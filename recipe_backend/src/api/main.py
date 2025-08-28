from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi import Depends

from src.core.config import get_settings
from src.core.db import engine, Base
from src.core.db import get_db
from src.api.auth import router as auth_router
from src.api.recipes import router as recipes_router

settings = get_settings()

# Create all tables on startup (for initial infrastructure)
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description=settings.APP_DESCRIPTION,
    openapi_tags=[
        {"name": "Health", "description": "Health and diagnostics"},
        {"name": "Authentication", "description": "User registration, login, and profile"},
        {"name": "Recipes", "description": "Browse, search, create, edit, and delete recipes"},
    ],
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ALLOW_ORIGINS,
    allow_credentials=settings.CORS_ALLOW_CREDENTIALS,
    allow_methods=settings.CORS_ALLOW_METHODS,
    allow_headers=settings.CORS_ALLOW_HEADERS,
)

# Register routers
app.include_router(auth_router)
app.include_router(recipes_router)


@app.get(
    "/",
    summary="Health Check",
    description="Return a basic health status for the API.",
    tags=["Health"],
    responses={200: {"description": "Service is healthy"}},
)
def health_check(db=Depends(get_db)):
    """Health check endpoint to verify service and database availability.

    Parameters:
      - None

    Returns:
      JSON with a status message.
    """
    # simple query-free check, session was obtained successfully
    return {"message": "Healthy"}
