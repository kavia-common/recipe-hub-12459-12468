# recipe-hub-12459-12468

## Backend (recipe_backend)

### Environment setup
1. Copy the environment file and adjust values for your environment:
   cp recipe_backend/.env.example recipe_backend/.env

2. By default the app uses a local SQLite database at ./data.db and a development JWT secret. For production, you must set a strong SECRET_KEY and a production-grade DATABASE_URL.

Environment variables consumed by the app (see src/core/config.py):
- DATABASE_URL: SQLAlchemy URL. Examples:
  - SQLite (dev): sqlite:///./data.db
  - PostgreSQL: postgresql+psycopg2://USER:PASS@HOST:5432/DBNAME
- SECRET_KEY: Strong random string used to sign JWTs.
- ACCESS_TOKEN_EXPIRE_MINUTES: Token lifetime in minutes (default 60).
- ALGORITHM: JWT signing algorithm (default HS256).
- CORS_ALLOW_ORIGINS: Comma-separated list of allowed origins for the browser (e.g., https://www.example.com,https://app.example.com). In dev a wildcard "*" is acceptable.
- CORS_ALLOW_CREDENTIALS: true|false (default true).
- CORS_ALLOW_METHODS: Allowed methods (comma-separated, default "*").
- CORS_ALLOW_HEADERS: Allowed headers (comma-separated, default "*").
- PERPLEXITY_API_KEY: API key for Perplexity (backend-only; never exposed to frontend).
- PERPLEXITY_MODEL (optional): Default model name (default "sonar").
- PERPLEXITY_MAX_TOKENS (optional): Default max tokens (default 512).
- PERPLEXITY_TEMPERATURE (optional): Default sampling temperature (default 0.2).

Note: Environment variables are loaded via python-dotenv when a .env file is present.

### Install dependencies
From the repo root:
   pip install -r recipe_backend/requirements.txt

### Run the API (development)
   uvicorn src.api.main:app --reload --app-dir recipe_backend

Note: The command assumes your working directory is recipe_backend when running.
Alternatively:
   cd recipe_backend && uvicorn src.api.main:app --reload

OpenAPI docs: /docs

### New: Title recommendation endpoint
- Path: POST /recommend-title
- Body:
  {
    "content": "Your note content here..."
  }
- Returns:
  {
    "suggestions": ["Title A", "Title B", "Title C"]
  }
- Behavior:
  - If PERPLEXITY_API_KEY is configured, titles are generated via Perplexity.
  - If not configured or on provider error, a local heuristic suggests titles.

### New: Chatbot endpoint (Perplexity proxy)
- Path: POST /chatbot
- Body:
  {
    "messages": [{"role": "user", "content": "Suggest a dinner recipe with salmon"}],
    "model": "sonar"          // optional
    "max_tokens": 400,        // optional
    "temperature": 0.2        // optional
  }
- Returns: A standardized response with choices[].message.content from Perplexity.
- Security: The PERPLEXITY_API_KEY is stored on the backend and never exposed to clients.

### Database setup and migrations
The project uses SQLAlchemy ORM, and tables are created automatically on app startup via:
- Base.metadata.create_all(bind=engine) in src/api/main.py

This is convenient for development and simple deployments. If you run against a managed database (e.g., PostgreSQL), ensure the DATABASE_URL is set and that the service account has permission to create tables on first run.

If you later add schema changes in production, consider adopting a migration tool (e.g., Alembic). For now:
- To initialize a fresh database: start the app (tables will be created), or run the seed script (which also ensures tables exist).
- To reset local SQLite dev data: delete data.db and restart the app or re-run seed.

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

### Production deployment

#### 1) Configure environment
Set environment variables securely (do not hard-code secrets):
- SECRET_KEY: Required. Use a long random value (e.g., 32+ chars).
- DATABASE_URL: Point to your production DB (e.g., PostgreSQL). Example:
  export DATABASE_URL="postgresql+psycopg2://user:pass@db-host:5432/recipehub"
- CORS_ALLOW_ORIGINS: Restrict to your frontend origins. Example:
  export CORS_ALLOW_ORIGINS="https://www.myrecipehub.com,https://app.myrecipehub.com"
- PERPLEXITY_API_KEY: Required to enable the /chatbot endpoint.

Optionally adjust:
- ACCESS_TOKEN_EXPIRE_MINUTES (default 60)
- CORS_ALLOW_METHODS / CORS_ALLOW_HEADERS / CORS_ALLOW_CREDENTIALS
- PERPLEXITY_MODEL / PERPLEXITY_MAX_TOKENS / PERPLEXITY_TEMPERATURE

#### 2) Install dependencies
From the repository root (or inside recipe_backend):
   pip install -r recipe_backend/requirements.txt

#### 3) Database connectivity
Ensure the database is reachable from your app host and that credentials are correct. On first startup, the app will attempt to connect to DATABASE_URL; if it fails, it will fall back to a local SQLite file (sqlite:///./data.db). In production you should verify the connection so you do not accidentally run on SQLite.

If deploying to PostgreSQL/MySQL:
- Ensure appropriate drivers are available (requirements already include SQLAlchemy; for PostgreSQL the psycopg2-binary or psycopg2 driver is required when using the postgresql+psycopg2 dialect).
- Provided requirements target psycopg2 via the SQLAlchemy dialect naming in your DATABASE_URL. If your platform requires an explicit driver package, install it accordingly.

#### 4) Running with a production server (Gunicorn + Uvicorn workers)
Use Gunicorn with Uvicorn workers behind a reverse proxy (nginx, Apache, or a cloud load balancer):

Example command (run from recipe_backend directory):
   gunicorn -k uvicorn.workers.UvicornWorker -w 2 -b 0.0.0.0:3001 src.api.main:app

Notes:
- Adjust -w (workers) based on CPU and load.
- Bind to an internal port (e.g., 3001) and place nginx in front to terminate TLS and serve as reverse proxy.

Alternatively, run raw Uvicorn (fewer features than Gunicorn but simpler):
   uvicorn src.api.main:app --host 0.0.0.0 --port 3001

#### 5) Reverse proxy and TLS
Configure your reverse proxy to:
- Forward requests to http://127.0.0.1:3001
- Set appropriate timeouts and headers
- Serve HTTPS to clients

#### 6) CORS configuration
Set CORS_ALLOW_ORIGINS to the exact origins that will host your frontend build (e.g., https://www.myrecipehub.com). The code applies CORSMiddleware with the configured origins/methods/headers.

#### 7) Health check
The root path "/" returns a simple JSON message to confirm service health.

#### 8) Regenerating OpenAPI (optional)
To regenerate the interfaces/openapi.json file:
   cd recipe_backend && python -m src.api.generate_openapi

This imports the FastAPI app and writes the OpenAPI schema to recipe_backend/interfaces/openapi.json.

### Operational tips
- Logs: Capture stdout/stderr from your process manager (systemd, Docker, etc.).
- Secrets: Use environment variables or your platform’s secret manager.
- Backups: If using SQLite, ensure the data.db file is persisted and backed up. Prefer a managed DB for production.
- Monitoring: Expose /docs and /openapi.json only as needed, and consider auth/ACLs or environment gating for production.