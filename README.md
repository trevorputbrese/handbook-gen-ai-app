# TRVCloud Intranet Demo App

## Installation and Setup

### Branches
This project includes two primary branches:

- **CF-Push-Ready branch**: Intended for deployment to **Tanzu Platform for Cloud Foundry**. Use this branch if you want to deploy the demo app to Cloud Foundry.  Requires you to pre-provision services (described below)
- **Main branch**: Primarily for local development. It requires **Ollama** running locally with an embeddings model (e.g., **nomic-embed-text**) and an LLM model (e.g., **gemma2:2b**), plus a Postgres database with the PGVector extension.

### Cloud Foundry (Tanzu Platform for Cloud Foundry) Setup

1. **Provision Services on Cloud Foundry**  
   Provision the following services:
   - **Postgres** service (with PGVector extension enabled by default)
   - **Embeddings Model** service (e.g., nomic-embed-text) via the **GenAI** tile
   - **LLM Model** service (e.g., gemma2:2b) via the **GenAI** tile

2. **Deploy to Cloud Foundry**  
   Switch to the **CF-Push-Ready** branch and push the app:
   ```bash
   git checkout CF-Push-Ready
   cf push
