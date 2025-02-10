docker run -e POSTGRES_USER=postgres \
           -e POSTGRES_PASSWORD=postgres \
           -e POSTGRES_DB=postgres-db \
           --name postgres-container\
           -p 5432:5432 \
           -d ankane/pgvector