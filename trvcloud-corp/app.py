import os
import json
import requests
import markdown
import psycopg2
from flask import Flask, render_template, request, redirect, url_for
from cfenv import AppEnv

app = Flask(__name__)

# Instantiate the CF environment helper.
env = AppEnv()

# ------------------------------------------------------------------------------
# Helper: Find a Genai service by capability from CF services.
def get_genai_service(capability):
    """
    Searches through the CF services for one with label 'genai' and with the given capability
    (e.g., "chat" or "embedding") in its credentials.
    """
    for service in env.services:
        if service.label.lower() == "genai":
            creds = service.credentials
            if "model_capabilities" in creds and capability in creds["model_capabilities"]:
                return service
    return None

# ------------------------------------------------------------------------------
# Configure LLM (chat) endpoint using CF service.
chat_service = get_genai_service("chat")
if chat_service:
    LLM_API_BASE = chat_service.credentials.get("api_base")
    LLM_API_KEY = chat_service.credentials.get("api_key")
    # Assume the chat endpoint is the API base with '/api/generate' appended.
    LLM_GENERATE_ENDPOINT = LLM_API_BASE.rstrip("/") + "/api/generate"
    print("Using CF LLM endpoint:", LLM_GENERATE_ENDPOINT)
else:
    LLM_GENERATE_ENDPOINT = os.environ.get("LLM_GENERATE_ENDPOINT", "http://localhost:11434/api/generate")
    LLM_API_KEY = os.environ.get("LLM_API_KEY", "")
    print("Using local LLM endpoint:", LLM_GENERATE_ENDPOINT)

# ------------------------------------------------------------------------------
# Configure Embedding endpoint using CF service.
embedding_service = get_genai_service("embedding")
if embedding_service:
    EMBEDDING_API_BASE = embedding_service.credentials.get("api_base")
    EMBEDDING_API_KEY = embedding_service.credentials.get("api_key")
    # Assume the embeddings endpoint is at '/api/embeddings' appended to the API base.
    EMBEDDING_ENDPOINT = EMBEDDING_API_BASE.rstrip("/") + "/api/embeddings"
    print("Using CF Embedding endpoint:", EMBEDDING_ENDPOINT)
else:
    EMBEDDING_ENDPOINT = os.environ.get("EMBEDDING_ENDPOINT", "http://localhost:11434/api/embeddings")
    EMBEDDING_API_KEY = os.environ.get("EMBEDDING_API_KEY", "")
    print("Using local Embedding endpoint:", EMBEDDING_ENDPOINT)

# ------------------------------------------------------------------------------
# Configure Postgres connection using CF service.
postgres_service = env.get_service(label="postgres")
if postgres_service:
    DB_URL = postgres_service.credentials.get("uri")
    print("Using CF Postgres URI:", DB_URL)
else:
    DB_URL = os.environ.get("DATABASE_URL", "postgresql://postgres:postgres@127.0.0.1:5432/postgres-db")
    print("Using local Postgres URI:", DB_URL)

# ------------------------------------------------------------------------------
# Other configuration variables.
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
HANDBOOK_FILE = os.path.join(BASE_DIR, "handbook.md")

# ------------------------------------------------------------------------------
# Helper Functions for Embeddings and Retrieval

def get_embedding(text):
    """
    Sends a request to the embeddings model endpoint.
    Payload includes the model, prompt, and stream flag.
    """
    payload = {
        "model": "nomic-embed-text",
        "prompt": text,
        "stream": False
    }
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {EMBEDDING_API_KEY}"
    }
    response = requests.post(EMBEDDING_ENDPOINT, json=payload, headers=headers)
    if response.status_code == 200:
        data = response.json()
        return data.get("embedding")
    else:
        raise Exception(f"Embedding API error: {response.status_code} {response.text}")

def chunk_text(text, chunk_size=500):
    """
    Splits the text into chunks based on double newlines, and further splits
    long paragraphs if they exceed chunk_size.
    """
    paragraphs = text.split('\n\n')
    chunks = []
    for para in paragraphs:
        para = para.strip()
        if not para:
            continue
        if len(para) > chunk_size:
            words = para.split()
            current_chunk = ""
            for word in words:
                if len(current_chunk) + len(word) + 1 > chunk_size:
                    chunks.append(current_chunk.strip())
                    current_chunk = word + " "
                else:
                    current_chunk += word + " "
            if current_chunk:
                chunks.append(current_chunk.strip())
        else:
            chunks.append(para)
    print(f"chunk_text: Found {len(chunks)} chunks.")
    return chunks

def retrieve_context(query, top_n=5):
    """
    Computes the query embedding and retrieves the top_n most similar handbook chunks
    from the database using PGVector similarity search.
    """
    query_embedding = get_embedding(query)
    
    conn = psycopg2.connect(DB_URL)
    cur = conn.cursor()
    
    # Cast the query_embedding to vector type for comparison.
    cur.execute("""
        SELECT chunk_text 
        FROM handbook_chunks 
        ORDER BY embedding <-> (%s)::vector
        LIMIT %s;
    """, (query_embedding, top_n))
    
    rows = cur.fetchall()
    cur.close()
    conn.close()
    
    context = "\n\n".join(row[0] for row in rows)
    print(f"retrieve_context: Retrieved {len(rows)} chunks.")
    return context

# ------------------------------------------------------------------------------
# Routes

@app.route('/')
def landing():
    return render_template('landing.html')

@app.route('/handbook')
def handbook():
    with open(HANDBOOK_FILE, 'r', encoding='utf-8') as file:
        md_content = file.read()
    handbook_html = markdown.markdown(md_content)
    return render_template('handbook.html', handbook=handbook_html)

@app.route('/edit-handbook', methods=['GET'])
def edit_handbook():
    with open(HANDBOOK_FILE, 'r', encoding='utf-8') as file:
        content = file.read()
    return render_template('edit_handbook.html', content=content)

@app.route('/update-handbook', methods=['POST'])
def update_handbook():
    new_content = request.form.get('handbook_content')
    print("Update-handbook route triggered; new content length:", len(new_content))
    with open(HANDBOOK_FILE, 'w', encoding='utf-8') as file:
        file.write(new_content)
    
    try:
        # Here you would call your update_embeddings(new_content) function
        # if you have it defined. For now, we assume it processes the text.
        pass
    except Exception as e:
        print("Error updating embeddings:", e)
    
    return redirect(url_for('handbook'))

@app.route('/api/chat', methods=['POST'])
def api_chat():
    data = request.get_json()
    user_message = data.get("message")
    if not user_message:
        return {"error": "No message provided"}, 400

    # Retrieve relevant context from the handbook via vector search.
    context = retrieve_context(user_message, top_n=5)
    print("Retrieved context:", context)
    
    # Build an augmented prompt with the context and the user's query.
    full_prompt = f"Context:\n{context}\n\nUser Query: {user_message}\n\nAnswer based on the above context:"
    
    payload = {
        "model": "gemma2:2b",
        "prompt": full_prompt,
        "stream": False
    }
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {LLM_API_KEY}"
    }
    
    print("Sending payload to LLM:", payload)
    ollama_response = requests.post(LLM_GENERATE_ENDPOINT, json=payload, headers=headers)
    print("LLM response:", ollama_response.status_code, ollama_response.text)
    
    if ollama_response.status_code == 200:
        return ollama_response.json(), 200
    else:
        return {"error": "Failed to get response from LLM", "details": ollama_response.text}, 500

@app.route('/chatbot')
def chatbot():
    return render_template('chatbot.html')

if __name__ == '__main__':
    app.run(debug=True)
