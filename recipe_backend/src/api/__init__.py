# PUBLIC_INTERFACE
def get_app():
    """Return the FastAPI application instance for external tools and scripts.

    This helper imports the app from src.api.main and returns it, allowing
    other modules (like CLI tools, tests, or OpenAPI generators) to get the
    configured FastAPI application without causing circular imports.
    """
    from .main import app
    return app
