import os
import json
import requests
import markdown
import psycopg2
from cfenv import AppEnv
from flask import Flask, render_template, request, redirect, url_for

app = Flask(__name__)


# ------------------------------------------------------------------------------
# Get LLM, embeddings, and postgres connection details from VCAP_SERVICES

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


# ------------------------------------------------------------------------------
# Other configuration variables.
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
HANDBOOK_FILE = os.path.join(BASE_DIR, "handbook.md")

# ------------------------------------------------------------------------------
# Define functions for chunking text, getting embeddings, updating embeddings, and retrieve context.

def chunk_text(text, chunk_size=500):
    """
    Splits the text into chunks.
    In this example, we first split by double newlines (paragraphs).
    If any chunk is longer than chunk_size characters, it is further split by words.
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
    return chunks

def get_embedding(text):
    payload = {
        "input": text,
        "model": embeddings_api_name  # This variable comes from your CF environment.
    }
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {embeddings_api_key}"
    }
    
    # Debug print: Show payload before making the API call.
    print("Calling embeddings API with payload:", payload)
    
    response = requests.post(
        f"{embeddings_api_base}/embeddings",  # Using the CF-provided embeddings endpoint.
        json=payload,
        headers=headers
    )
    
    # Debug print: Show raw response status and text.
    print("Embeddings API response code:", response.status_code)
    
    if response.status_code == 200:
        data = response.json()
        embedding = data["data"][0]["embedding"]
        # Debug print: Show the embedding that was returned.
        print("Returned embeddings -- no need to print out embeddings")
        return embedding
    else:
        raise Exception(f"Embedding API error: {response.status_code} {response.text}")

def update_embeddings(text):
    print("update_embeddings called")
    chunks = chunk_text(text)
    print(f"Found {len(chunks)} chunks in the handbook.")

    try:
        # Use the new POSTGRES_URL variable directly
        conn = psycopg2.connect(POSTGRES_URL)
    except Exception as e:
        print("Error connecting to Postgres:", e)
        return

    cur = conn.cursor()

    try:
        # Clear any existing embeddings
        cur.execute("DELETE FROM handbook_chunks;")
        conn.commit()
        print("Cleared existing handbook_chunks.")
    except Exception as e:
        print("Error clearing handbook_chunks:", e)

    inserted = 0
    for chunk in chunks:
        try:
            embedding = get_embedding(chunk)
            # Print a preview of the chunk and the embedding length before insertion.
            print("Inserting chunk:", chunk[:50], "with embedding length:", len(embedding))
            
            cur.execute(
                "INSERT INTO handbook_chunks (chunk_text, embedding) VALUES (%s, %s);",
                (chunk, embedding)
            )
            conn.commit()
            inserted += 1
            print("Inserted successfully. Total inserted:", inserted)
        except Exception as e:
            print(f"Error processing chunk: {e}")
            continue

    print(f"update_embeddings: Inserted {inserted} chunks out of {len(chunks)}.")
    cur.close()
    conn.close()
    print("Embeddings updated.")


def retrieve_context(query, top_n=5):
    """
    Given a user query, compute its embedding and retrieve the top_n most similar
    handbook chunks from the database.
    """
    # Compute embedding for the query using the get_embedding function.
    query_embedding = get_embedding(query)
    
    # Connect to the Postgres database using the POSTGRES_URL variable.
    conn = psycopg2.connect(POSTGRES_URL)
    cur = conn.cursor()
    
    # Use PGVector's similarity operator (<->) to retrieve the most similar chunks.
    cur.execute("""
        SELECT chunk_text 
        FROM handbook_chunks 
        ORDER BY embedding <-> (%s)::vector
        LIMIT %s;
    """, (query_embedding, top_n))
    
    rows = cur.fetchall()
    cur.close()
    conn.close()
    
    # Concatenate the retrieved chunks into one context string.
    context = "\n\n".join(row[0] for row in rows)
    print(f"retrieve_context: Retrieved {len(rows)} chunks.")
    return context


# ------------------------------------------------------------------------------
# Define app routes for landing page, handbook, edit-handbook, update-handbook, chatbot, and api-chat

@app.route('/')
def landing():
    return render_template('landing.html')

@app.route('/handbook')
def handbook():
    # Read the Markdown handbook and convert to HTML
    with open(HANDBOOK_FILE, 'r', encoding='utf-8') as file:
        md_content = file.read()
    handbook_html = markdown.markdown(md_content)
    return render_template('handbook.html', handbook=handbook_html)

@app.route('/edit-handbook', methods=['GET'])
def edit_handbook():
    # Load the current handbook content for editing
    with open(HANDBOOK_FILE, 'r', encoding='utf-8') as file:
        content = file.read()
    return render_template('edit_handbook.html', content=content)

@app.route('/update-handbook', methods=['POST'])
def update_handbook():
    # Get the updated handbook content from the form
    new_content = request.form.get('handbook_content')
    print("Update-handbook route triggered; new content length:", len(new_content))
    # Save the updated content to the markdown file
    with open(HANDBOOK_FILE, 'w', encoding='utf-8') as file:
        file.write(new_content)
    
    # Process the new content: chunk it, generate embeddings, and store in the database
    try:
        update_embeddings(new_content)
    except Exception as e:
        print("Error updating embeddings:", e)
    
    return redirect(url_for('handbook'))

@app.route('/chatbot')
def chatbot():
    # Placeholder for the chatbot interface
    return render_template('chatbot.html')

@app.route('/api/chat', methods=['POST'])
def api_chat():
    data = request.get_json()
    user_message = data.get("message")
    if not user_message:
        return {"error": "No message provided"}, 400

    # Retrieve relevant context from the handbook
    context = retrieve_context(user_message, top_n=5)
    print("Retrieved context:", context)
    
    # Build an augmented conversation using a messages array
    payload = {
        "model": llm_api_name,  # e.g., "gemma2:2b"
        "messages": [
            {"role": "system", "content": f"Use the following context to answer the user's query:\n\n{context}"},
            {"role": "user", "content": user_message}
        ],
        "stream": False
    }
    
    print("Sending payload to LLM:", payload)
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {llm_api_key}"
    }

    # -- revised ollama api call
    ollama_response = requests.post(
        f"{llm_api_base}/chat/completions",
        json=payload,
        headers=headers,
        timeout=40
    )
    print("LLM API response:", ollama_response.status_code, ollama_response.text)

    if ollama_response.status_code == 200:
        response_data = ollama_response.json()
        return {
            "response": response_data["choices"][0]["message"]["content"]
        }, 200
    else:
        return {"error": "Failed to get response from LLM", "details": ollama_response.text}, 500


    '''
    # Send to the chat completions endpoint.
    ollama_response = requests.post(f"{llm_api_base}/chat/completions", json=payload, headers=headers)
    print("LLM API response:", ollama_response.status_code, ollama_response.text)
    
    if ollama_response.status_code == 200:
        response_data = ollama_response.json()
        return {
            "response": response_data["choices"][0]["message"]["content"]
        }, 200
    else:
        return {"error": "Failed to get response from LLM", "details": ollama_response.text}, 500
    '''


if __name__ == '__main__':
    app.run(debug=True)