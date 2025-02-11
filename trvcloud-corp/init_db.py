import os
import psycopg2
import cfenv

# Create an AppEnv instance to parse Cloud Foundry environment variables.
app_env = cfenv.AppEnv()

# Try to get the database service using its Cloud Foundry service name.
# Replace 'postgres-db' with the actual service name as it appears in your VCAP_SERVICES.
try:
    pg_service = app_env.get_service('postgres')
    # The service credentials might store the connection URI under 'uri' or 'url'.
    db_url = pg_service.credentials.get('uri') or pg_service.credentials.get('url')
    if not db_url:
        raise Exception("No DB URL found in service credentials.")
    print("Using database URL from Cloud Foundry:", db_url)
except Exception as e:
    # If no service is found or there's an error, fall back to a default or environment variable.
    db_url = os.environ.get("DATABASE_URL", "postgresql://postgres:postgres@127.0.0.1:5432/postgres-db")
    print("Falling back to local database URL:", db_url)

# Connect to the Postgres database using psycopg2.
conn = psycopg2.connect(db_url)
cur = conn.cursor()

# Create the PGVector extension if it doesn't exist.
cur.execute("CREATE EXTENSION IF NOT EXISTS vector;")

# Create the handbook_chunks table if it doesn't exist.
cur.execute("""
CREATE TABLE IF NOT EXISTS handbook_chunks (
    id SERIAL PRIMARY KEY,
    chunk_text TEXT NOT NULL,
    embedding VECTOR(768)
);
""")
conn.commit()

cur.close()
conn.close()

print("Database schema initialized.")
