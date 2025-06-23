import argparse
import os
import uvicorn

def parse_args():
    parser = argparse.ArgumentParser(description="Start RAG API with DB connection details.")
    parser.add_argument('--db-host', required=True)
    parser.add_argument('--db-name', required=True)
    parser.add_argument('--db-user', required=True)
    parser.add_argument('--db-pass', required=True)
    parser.add_argument('--host', default='0.0.0.0')
    parser.add_argument('--port', type=int, default=8000)
    return parser.parse_args()

if __name__ == "__main__":
    args = parse_args()
    # Set as environment variables for the FastAPI app to read
    os.environ["DB_HOST"] = args.db_host
    os.environ["DB_NAME"] = args.db_name
    os.environ["DB_USER"] = args.db_user
    os.environ["DB_PASS"] = args.db_pass

    uvicorn.run("rag_api:app", host=args.host, port=args.port, reload=True)