import json
import requests
import psycopg2
from psycopg2.extras import RealDictCursor
from transformers import AutoTokenizer
import argparse
import os

OLLAMA_EMBEDDING_MODEL = "dengcao/Qwen3-Embedding-8B:Q8_0"
OLLAMA_LLM_MODEL = "hf.co/Qwen/Qwen3-32B-GGUF:Q8_0"
OLLAMA_HOST = "http://fnordstation.home.arpa:11434"
MAX_CONTEXT_TOKENS = 39000
MAX_TOP_K = 300

tokenizer = AutoTokenizer.from_pretrained("Qwen/Qwen3-Embedding-8B")

def get_pg_conn(args=None):

    def get_db_param(arg_val, env_var):
        return arg_val if arg_val is not None else os.environ.get(env_var)
    
    PG_CONN = {
        "dbname": get_db_param(getattr(args, "db_name", None), "DB_NAME"),
        "user": get_db_param(getattr(args, "db_user", None), "DB_USER"),
        "password": get_db_param(getattr(args, "db_pass", None), "DB_PASS"),
        "host": get_db_param(getattr(args, "db_host", None), "DB_HOST")
    }

    for k, v in PG_CONN.items():
        if not v:
            raise ValueError(f"Database parameter '{k}' is missing.")
        
    return PG_CONN

def get_query_embedding(text):
    resp = requests.post(
        f"{OLLAMA_HOST}/api/embeddings",
        headers={"Content-Type": "application/json"},
        data=json.dumps({"model": OLLAMA_EMBEDDING_MODEL, "prompt": text})
    )
    resp.raise_for_status()
    return resp.json()["embedding"]

def retrieve_relevant_chunks(embedding, top_k, pg_conn):
    conn = psycopg2.connect(**pg_conn)
    cur = conn.cursor(cursor_factory=RealDictCursor)
    cur.execute("""
        SELECT content, article_id, chunk_index
        FROM chunks
        ORDER BY embedding <=> %s::vector
        LIMIT %s;
    """, (embedding, top_k))
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return rows

def trim_chunks_to_fit(chunks, query, max_tokens=MAX_CONTEXT_TOKENS):
    used_tokens = len(tokenizer.encode(query, add_special_tokens=False)) + 300
    selected = []
    for chunk in chunks:
        chunk_tokens = tokenizer.encode(chunk["content"], add_special_tokens=False)
        if used_tokens + len(chunk_tokens) > max_tokens:
            break
        selected.append(chunk)
        used_tokens += len(chunk_tokens)
    return selected, used_tokens

def build_prompt(chunks, query, wiki):
    context = "\n\n".join(chunk["content"] for chunk in chunks)
    return f"""You are an expert assistant helping answer questions about the world of {wiki}.

Use only the context provided below. If the answer is not present, say so.

### Context:
{context}

### Question:
{query}

### Answer:"""

def generate_answer(prompt):
    resp = requests.post(
        f"{OLLAMA_HOST}/api/generate",
        headers={"Content-Type": "application/json"},
        data=json.dumps({"model": OLLAMA_LLM_MODEL, "prompt": prompt})
    )
    resp.raise_for_status()
    output = ""
    for line in resp.iter_lines():
        if line:
            output += json.loads(line)["response"]
    return output

def rag_query(query, wiki, pg_conn):
    query_embedding = get_query_embedding(query)
    raw_chunks = retrieve_relevant_chunks(query_embedding, MAX_TOP_K, pg_conn)
    chunks, used_tokens = trim_chunks_to_fit(raw_chunks, query)
    rag_prompt = build_prompt(chunks, query, wiki)
    answer = generate_answer(rag_prompt)
    return {
        "answer": answer,
        "chunks_used": len(chunks),
        "tokens_used": used_tokens
    }

def main():
    parser = argparse.ArgumentParser(description="RAG query fandom wiki.")
    parser.add_argument('--wiki', required=True, help='the name of the wiki')
    parser.add_argument('--query', required=True, help='The user query/question')
    parser.add_argument('--db-host', help='Database host')
    parser.add_argument('--db-name', help='Database name')
    parser.add_argument('--db-user', help='Database user')
    parser.add_argument('--db-pass', help='Database password')
    args = parser.parse_args()
    pg_conn = get_pg_conn(args)
    result = rag_query(args.query, args.wiki, pg_conn)
    print(f"\n[debug] Using {result['chunks_used']} chunks and total prompt tokens = {result['tokens_used']} / {MAX_CONTEXT_TOKENS}")
    print(result["answer"])

if __name__ == "__main__":
    main()