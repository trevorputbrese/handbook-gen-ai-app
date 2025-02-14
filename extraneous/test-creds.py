def get_vcap_services():
    """Parse VCAP_SERVICES environment variable into a Python dict."""
    vcap_services = os.getenv('VCAP_SERVICES')
    if vcap_services:
        return json.loads(vcap_services)
    return {}

def get_genai_service(capability):
    """
    Searches through the VCAP_SERVICES for a genai service with the given capability.
    Returns the service credentials if found, None otherwise.
    """
    vcap_services = get_vcap_services()
    genai_services = vcap_services.get('genai', [])
    
    for service in genai_services:
        creds = service.get('credentials', {})
        capabilities = creds.get('model_capabilities', [])
        if capability in capabilities:
            return creds
    return None

# ------------------------------------------------------------------------------
# Configure LLM (chat) endpoint using CF service
chat_service = get_genai_service("chat")
if chat_service:
    LLM_API_BASE = chat_service.get("api_base")
    LLM_API_KEY = chat_service.get("api_key")
    # The API base already includes the full path in your VCAP_SERVICES
    LLM_GENERATE_ENDPOINT = LLM_API_BASE
    print("Using CF LLM endpoint:", LLM_GENERATE_ENDPOINT)
else:
    LLM_GENERATE_ENDPOINT = os.environ.get("LLM_GENERATE_ENDPOINT", "http://localhost:11434/api/generate")
    LLM_API_KEY = os.environ.get("LLM_API_KEY", "")
    print("Using local LLM endpoint:", LLM_GENERATE_ENDPOINT)

# ------------------------------------------------------------------------------
# Configure Embedding endpoint using CF service
embedding_service = get_genai_service("embedding")
if embedding_service:
    EMBEDDING_API_BASE = embedding_service.get("api_base")
    EMBEDDING_API_KEY = embedding_service.get("api_key")
    # The API base already includes the full path in your VCAP_SERVICES
    EMBEDDING_ENDPOINT = EMBEDDING_API_BASE
    print("Using CF Embedding endpoint:", EMBEDDING_ENDPOINT)
else:
    EMBEDDING_ENDPOINT = os.environ.get("EMBEDDING_ENDPOINT", "http://localhost:11434/api/embeddings")
    EMBEDDING_API_KEY = os.environ.get("EMBEDDING_API_KEY", "")
    print("Using local Embedding endpoint:", EMBEDDING_ENDPOINT)

# ------------------------------------------------------------------------------
# Configure Postgres connection using CF service
def get_postgres_credentials():
    """Get Postgres credentials from VCAP_SERVICES."""
    vcap_services = get_vcap_services()
    postgres_services = vcap_services.get('postgres', [])
    
    if postgres_services:
        return postgres_services[0].get('credentials', {})
    return None

postgres_creds = get_postgres_credentials()
if postgres_creds:
    DB_URL = postgres_creds.get('uri')
    print("Using CF Postgres URI:", DB_URL)
else:
    DB_URL = os.environ.get("DATABASE_URL", "postgresql://postgres:postgres@127.0.0.1:5432/postgres-db")
    print("Using local Postgres URI:", DB_URL)

