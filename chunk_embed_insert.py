from transformers import AutoTokenizer
import requests
import json
import psycopg2
from typing import List
import jsonlines
from dataclasses import dataclass
import argparse

# Load the Qwen3 tokenizer
tokenizer = AutoTokenizer.from_pretrained("Qwen/Qwen3-Embedding-8B")

@dataclass
class ArticleChunk:
    start_token: int
    end_token: int
    text: str

# Chunk token ids into 512-token chunks with 128-token overlap
def chunk_tokens(input_ids: List[int], max_tokens: int = 512, overlap: int = 128) -> List[ArticleChunk]:
    step = max_tokens - overlap
    chunks = []
    i = 0
    while i < len(input_ids):
        chunk_ids = input_ids[i:i + max_tokens]
        chunk_text = tokenizer.decode(chunk_ids, skip_special_tokens=True)
        if not chunks:
            # Always append the first chunk
            chunks.append(ArticleChunk(start_token=i, end_token=i + len(chunk_ids), text=chunk_text))
        elif len(chunk_ids) <= 15:
            # Merge this chunk into the previous chunk using the full token range for decoding
            prev = chunks[-1]
            merged_start = prev.start_token
            merged_end = i + len(chunk_ids)
            merged_ids = input_ids[merged_start:merged_end]
            merged_text = tokenizer.decode(merged_ids, skip_special_tokens=True)
            chunks[-1] = ArticleChunk(start_token=merged_start, end_token=merged_end, text=merged_text)
        else:
            # Normal chunk
            chunks.append(ArticleChunk(start_token=i, end_token=i + len(chunk_ids), text=chunk_text))
        i += step
    return chunks

# Get embedding from local Ollama
def get_embedding_ollama(text: str, model: str = "dengcao/Qwen3-Embedding-8B:Q8_0", host: str = "http://fnordstation.home.arpa:11434") -> List[float]:
    response = requests.post(
        f"{host}/api/embeddings",
        headers={"Content-Type": "application/json"},
        data=json.dumps({
            "model": model,
            "prompt": text
        })
    )
    response.raise_for_status()
    return response.json()["embedding"]

# PostgreSQL connection helper
def get_pg_connection(db_params):
    return psycopg2.connect(**db_params)

# Insert chunk + embedding into Postgres
def insert_into_postgres(article_id: int, chunk_index: int, start_token: int, end_token: int,
                         content: str, embedding: List[float], token_count: int, db_params=None):
    conn = get_pg_connection(db_params)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO chunks (article_id, chunk_index, chunk_start_token, chunk_end_token,
                                 content, embedding, token_count)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
    """, (article_id, chunk_index, start_token, end_token, content, embedding, token_count))
    conn.commit()
    cursor.close()
    conn.close()

def insert_article(title: str, content: str, token_count: int, metadata: dict, db_params=None) -> int:
    """Insert article and return its ID"""
    conn = get_pg_connection(db_params)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO articles (title, full_content, token_count, metadata)
        VALUES (%s, %s, %s, %s)
        RETURNING article_id
    """, (title, content, token_count, json.dumps(metadata)))
    article_id = cursor.fetchone()[0]
    conn.commit()
    cursor.close()
    conn.close()
    return article_id

def parse_args():
    parser = argparse.ArgumentParser(description="Insert article chunks and embeddings into Postgres.")
    parser.add_argument('--db-host', required=True, help='PostgreSQL host')
    parser.add_argument('--db-name', required=True, help='PostgreSQL database name')
    parser.add_argument('--db-user', required=True, help='PostgreSQL user')
    parser.add_argument('--db-pass', required=True, help='PostgreSQL password')
    parser.add_argument('--input-file', default='data.jsonl', help='Input JSONL file')
    args = parser.parse_args()
    # Custom error handling for missing arguments
    missing = []
    for arg in ['db_host', 'db_name', 'db_user', 'db_pass']:
        if not getattr(args, arg):
            missing.append(arg)
    if missing:
        print("\nERROR: Missing required arguments: " + ", ".join(missing))
        print("\nSample usage:")
        print("python chunk_embed_insert.py --db-host <host> --db-name <dbname> --db-user <user> --db-pass <password> --input-file data.jsonl")
        exit(1)
    return args

# Example usage
if __name__ == "__main__":
    # Print sample command for user
    print("Sample usage:")
    print("python chunk_embed_insert.py --db-host <host> --db-name <dbname> --db-user <user> --db-pass <password> --input-file data.jsonl")
    args = parse_args()
    pg_conn_params = dict(
        dbname=args.db_name,
        user=args.db_user,
        password=args.db_pass,
        host=args.db_host
    )
    input_file = args.input_file
    
    with jsonlines.open(input_file) as reader:
        for article in reader:
            # Insert the article first
            title = article['title']
            text = article['text']
            # Get token ids and token count for full article
            input_ids = tokenizer.encode(text, add_special_tokens=False)
            token_count = len(input_ids)
            
            # Create metadata with url and any other fields
            metadata = {'url': article['url']}
            
            # Insert article and get its ID
            article_id = insert_article(title, text, token_count, metadata, pg_conn_params)
            print(f"Processing article: {title} (ID: {article_id})")
            
            # Now process chunks
            chunks = chunk_tokens(input_ids)
            for idx, chunk in enumerate(chunks):
                try:
                    embedding = get_embedding_ollama(chunk.text)
                    insert_into_postgres(article_id, idx, chunk.start_token, chunk.end_token, chunk.text, embedding, chunk.end_token - chunk.start_token, pg_conn_params)
                    print(f"  Inserted chunk {idx+1}/{len(chunks)}")
                except Exception as e:
                    print(f"Error processing chunk {idx} for article {title}: {e}")
