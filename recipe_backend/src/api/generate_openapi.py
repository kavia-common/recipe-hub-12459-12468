import json
import os

# PUBLIC_INTERFACE
def generate_openapi_to_file():
    """Generate the FastAPI OpenAPI schema and write it to interfaces/openapi.json.

    This script imports the FastAPI app via src.api.get_app() to avoid circular imports,
    then calls app.openapi() and writes the resulting schema for external consumers.
    """
    from src.api import get_app

    app = get_app()
    openapi_schema = app.openapi()

    output_dir = "interfaces"
    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, "openapi.json")

    with open(output_path, "w") as f:
        json.dump(openapi_schema, f, indent=2)

if __name__ == "__main__":
    generate_openapi_to_file()
