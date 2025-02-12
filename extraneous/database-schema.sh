CREATE EXTENSION vector;

CREATE TABLE IF NOT EXISTS handbook_chunks (
    id SERIAL PRIMARY KEY,
    chunk_text TEXT NOT NULL,
    embedding VECTOR(768)