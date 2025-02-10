from flask import Flask, render_template, request, redirect, url_for
import markdown
import os
import requests
import psycopg2

app = Flask(__name__)

# Define file paths and endpoints
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
HANDBOOK_FILE = os.path.join(BASE_DIR, 'handbook.md')

# Local embedding API endpoint (update if needed)
EMBEDDING_ENDPOINT = os.environ.get("EMBEDDING_ENDPOINT", "http://localhost:11435/api/embeddings")

# Database connection details (set these as environment variables in production)
DB_HOST = os.environ.get("DB_HOST", "127.0.0.1")
DB_PORT = os.environ.get("DB_PORT", "5432")
DB_NAME = os.environ.get("DB_NAME", "postgres-db")
DB_USER = os.environ.get("DB_USER", "postgres")
DB_PASS = os.environ.get("DB_PASS", "postgres")

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
        "model": "nomic-embed-text",
        "prompt": text
    }
    headers = {"Content-Type": "application/json"}
    response = requests.post(EMBEDDING_ENDPOINT, json=payload, headers=headers)
    if response.status_code == 200:
        data = response.json()
        return data.get("embedding")
    else:
        raise Exception(f"Embedding API error: {response.status_code} {response.text}")

def update_embeddings(text):
    """
    Processes the updated handbook text:
      1. Chunks the text.
      2. Retrieves an embedding for each chunk.
      3. Clears the existing embeddings and stores the new data in the database.
    """
    chunks = chunk_text(text)
    print(f"Found {len(chunks)} chunks in the handbook.")

    # Connect to the Postgres database
    conn = psycopg2.connect(
        host=DB_HOST,
        database=DB_NAME,
        user=DB_USER,
        password=DB_PASS
    )
    cur = conn.cursor()

    # Clear any existing embeddings
    cur.execute("DELETE FROM handbook_chunks;")
    conn.commit()

    # Process each chunk: get its embedding and store it
    for chunk in chunks:
        try:
            embedding = get_embedding(chunk)
            # Insert into the database; assuming embedding is a list of floats
            cur.execute("INSERT INTO handbook_chunks (chunk_text, embedding) VALUES (%s, %s);", (chunk, embedding))
            conn.commit()
        except Exception as e:
            print(f"Error processing chunk: {e}")
            continue

    cur.close()
    conn.close()
    print("Embeddings updated.")

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

    # Build the payload with the necessary parameters
    payload = {
        "model": "gemma2:2b",
        "prompt": user_message,
        "stream": False
    }
    
    print("Sending payload to Ollama API:", payload)
    # Call the correct endpoint without " -d" in the URL.
    ollama_response = requests.post("http://localhost:11434/api/generate", json=payload)
    print("Ollama API response:", ollama_response.status_code, ollama_response.text)
    
    if ollama_response.status_code == 200:
        return ollama_response.json(), 200
    else:
        return {"error": "Failed to get response from Ollama", "details": ollama_response.text}, 500



if __name__ == '__main__':
    app.run(debug=True)
