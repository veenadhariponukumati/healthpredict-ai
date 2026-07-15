-- n8n uses its own database (kept separate from the app's "readmission"
-- database so its internal tables don't pollute the app schema). This
-- script runs automatically on first Postgres init (only when the data
-- directory is empty), via /docker-entrypoint-initdb.d/.
CREATE DATABASE n8n;
