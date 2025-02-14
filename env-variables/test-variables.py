import os
import json
from cfenv import AppEnv

env = AppEnv()
genai_llm_service = env.get_service(name="gemma2")

if genai_llm_service:
    llm_api_name = genai_llm_service.credentials.get("model_name")
    llm_api_base = genai_llm_service.credentials.get("api_base")
    llm_api_key = genai_llm_service.credentials.get("api_key")

print(llm_api_name)
print(llm_api_base)
print(llm_api_key)

genai_embeddings_service = env.get_service(name="nomic")

if genai_embeddings_service:
    embeddings_api_name = genai_embeddings_service.credentials.get("model_name")
    embeddings_api_base = genai_embeddings_service.credentials.get("api_base")
    embeddings_api_key = genai_embeddings_service.credentials.get("api_key")

print(embeddings_api_name)
print(embeddings_api_base)
print(embeddings_api_key)

postgres_service = env.get_service(name="postgres")

postgres_service = env.get_service(name="postgres")

postgres_service = env.get_service(name="postgres")

if postgres_service:
    raw_jdbc_url = postgres_service.credentials.get("jdbcUrl")
    # Strip "jdbc:" prefix if it exists.
    if raw_jdbc_url.startswith("jdbc:"):
        POSTGRES_URL = raw_jdbc_url[5:]
    else:
        POSTGRES_URL = raw_jdbc_url
    POSTGRES_PASSWORD = postgres_service.credentials.get("password")
else:
    POSTGRES_URL = os.environ.get("DATABASE_URL", "postgresql://postgres:postgres@127.0.0.1:5432/postgres-db")
    POSTGRES_PASSWORD = os.environ.get("DATABASE_PASSWORD", "postgres")

print(POSTGRES_URL)
print(POSTGRES_PASSWORD)
