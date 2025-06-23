from fastapi import FastAPI, HTTPException, Request
from typing import List
from pydantic import BaseModel
import os
from rag_query import rag_query, get_pg_conn, get_query_embedding
from fastapi.responses import StreamingResponse, Response
import json

app = FastAPI()
wiki = "Clair Obscur"

class RAGRequest(BaseModel):
    query: str
    wiki: str

class OllamaGenerateRequest(BaseModel):
    model: str
    prompt: str

class OllamaChatMessage(BaseModel): 
    role: str
    content: str

class OllamaChatRequest(BaseModel):
    model: str
    messages: List[OllamaChatMessage]

def normalize_model_name(model):
    # Remove any :tag suffix (e.g., :latest)
    return model.split(":")[0]

@app.get("/api/ps")
def ollama_ps():
    return {"models": [{"model": f"{wiki}:latest", "name": f"{wiki}:latest"}]}

@app.post("/api/pull")
async def ollama_pull(request: Request):
    data = await request.json()
    model = data.get("name")
    if model != wiki:
        raise HTTPException(status_code=404, detail=f"Model '{model}' not found.")

    async def event_stream():
        # Progress message (optional, but helps)
        yield json.dumps({
            "status": "pulling manifest",
        }) + "\n"
        yield json.dumps({
            "status": f"downloading {model}",
            "digest":"",
            "total": 100000,
            "completed": 25000
        }) + "\n"
        yield json.dumps({
            "status": f"downloading {model}",
            "digest":"",
            "total": 100000,
            "completed": 100000
        }) + "\n" 
        yield json.dumps({
            "status": "verifying sha256 digest",
        }) + "\n"
        yield json.dumps({
            "status": "writing manifest",
        }) + "\n"
        yield json.dumps({
            "status": "removing any unused layers",
        }) + "\n"
        yield json.dumps({
            "status": "success",
        }) + "\n"                                                       

    return StreamingResponse(event_stream(), media_type="text/event-stream")

@app.delete("/api/delete")
async def ollama_delete(request: Request):
    return Response(status_code=200)

@app.post("/api/show")
async def ollama_show(request: Request):
    data = await request.json()
    model = data.get("name")
    if model != wiki:
        raise HTTPException(status_code=404, detail=f"Model '{model}' not found.")
    
    # Return minimal model info
    return {
        "name": model,
        "modelfile": "RAG",
        "parameters": {},
        "details": f"RAG-backed model for wiki: {model}"
    }

@app.get("/api/tags")
def list_models():
    return {
        "models": [
            {
                "model": f"{wiki}:latest",
                "name": f"{wiki}:latest",
                "size": 100000,
                "tags": ["latest"]  # Add tags here
            }
        ]
    }

@app.post("/rag_query")
def rag_query_endpoint(request: RAGRequest):
    try:
        pg_conn = get_pg_conn()
        result = rag_query(request.query, request.wiki, pg_conn)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/generate")
def ollama_generate(request: OllamaGenerateRequest):
    try:
        pg_conn = get_pg_conn()
        result = rag_query(request.prompt, wiki, pg_conn)
        return {"response": result["answer"]}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
@app.post("/api/chat")
async def ollama_chat(request: OllamaChatRequest):
    try:
        pg_conn = get_pg_conn()
        result = rag_query(request.messages[-1].content, wiki, pg_conn)
        return {
            "model": wiki,
            "message": { "role": "user", "content": result["answer"] },
            "done_reason": "stop",
            "done": True,
            }
        return {"response": result["answer"]}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
@app.get("/api/version")
def ollama_version():
    # Return a static version string or your own versioning
    return {"version": "fandom-rag-1.0.0"}