#!/usr/bin/env python3
import sys
import json
import requests
import numpy as np

OLLAMA_EMBEDDING_MODEL = "dengcao/Qwen3-Embedding-8B:Q8_0"
OLLAMA_HOST = "http://fnordstation.home.arpa:11434"

def get_embedding(text):
    resp = requests.post(
        f"{OLLAMA_HOST}/api/embeddings",
        headers={"Content-Type": "application/json"},
        data=json.dumps({"model": OLLAMA_EMBEDDING_MODEL, "prompt": text})
    )
    resp.raise_for_status()
    return np.array(resp.json()["embedding"], dtype=np.float32)

def cosine_similarity(a, b):
    return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b)))

def main():
    if len(sys.argv) != 3:
        print("Usage: python embedding_compare.py <phrase1> <phrase2>")
        sys.exit(1)
    phrase1, phrase2 = sys.argv[1], sys.argv[2]
    emb1 = get_embedding(phrase1)
    emb2 = get_embedding(phrase2)
    cos_sim = cosine_similarity(emb1, emb2)
    print(f"Cosine similarity: {cos_sim:.6f}")

if __name__ == "__main__":
    main()
