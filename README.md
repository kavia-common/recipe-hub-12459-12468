# recipe-hub-12459-12468

## Backend (recipe_backend)

### Environment setup
1. Copy the example environment file and adjust if needed:
   cp recipe_backend/.env.example recipe_backend/.env

2. The defaults use a local SQLite database at ./data.db and a dev JWT secret.

### Install dependencies
From the repo root:
   pip install -r recipe_backend/requirements.txt

### Run the API (dev)
   uvicorn src.api.main:app --reload --app-dir recipe_backend

Note: The command assumes your working directory is recipe_backend when running.
Alternatively:
   cd recipe_backend && uvicorn src.api.main:app --reload

OpenAPI docs: /docs

### Seed the database with demo data
You can populate demo users, recipes, and favorites:

Option A (module path):
   cd recipe_backend
   python -m src.scripts.seed

Option B (direct file):
   python recipe_backend/src/scripts/seed.py

Demo accounts:
- alice / password123
- bob   / password123
- carol / password123