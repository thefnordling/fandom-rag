-- User creation logic (from create_user.sql)
DO $$
BEGIN
   IF NOT EXISTS (
      SELECT FROM pg_catalog.pg_roles WHERE rolname = '$DB_USER'
   ) THEN
      EXECUTE format('CREATE USER %I WITH PASSWORD %L', '$DB_USER', '$DB_PASS');
   END IF;
END$$;

-- Table and permission logic (from create_tables.sql)
CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS articles (
    article_id SERIAL PRIMARY KEY,
    title TEXT NOT NULL,
    full_content TEXT NOT NULL,
    token_count INTEGER,
    metadata JSONB,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS chunks (
    chunk_id SERIAL PRIMARY KEY,
    article_id INTEGER NOT NULL REFERENCES articles(article_id) ON DELETE CASCADE,
    chunk_index INTEGER NOT NULL,
    chunk_start_token INTEGER,
    chunk_end_token INTEGER,
    content TEXT NOT NULL,
    embedding VECTOR(4096),
    token_count INTEGER,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

DO $$
BEGIN
  IF EXISTS (SELECT 1 FROM information_schema.schemata WHERE schema_name = 'public') THEN
    EXECUTE 'ALTER SCHEMA public OWNER TO "$DB_USER"';
  END IF;
END$$;

DO $$
BEGIN
  IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'articles') THEN
    EXECUTE 'ALTER TABLE articles OWNER TO "$DB_USER"';
  END IF;
  IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'chunks') THEN
    EXECUTE 'ALTER TABLE chunks OWNER TO "$DB_USER"';
  END IF;
END$$;

GRANT CONNECT ON DATABASE "$DB_NAME" TO "$DB_USER";
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO "$DB_USER";
GRANT SELECT, INSERT, UPDATE, DELETE ON articles TO "$DB_USER";
GRANT SELECT, INSERT, UPDATE, DELETE ON chunks TO "$DB_USER";
