"""
Server Entry Point for RAG Generator
Runs the Flask application and REST API server.
"""

import os
import sys
from rag_generator.core.factory import RAGFactory
from rag_generator.app import create_web_app

def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")

    host = os.getenv("HOST", "127.0.0.1")
    port = int(os.getenv("PORT", 5000))
    storage_root = os.getenv("STORAGE_ROOT", "./data/apps")

    print("=" * 65)
    print("   [+] RAG GENERATOR - DYNAMIC AGENTIC RAG PLATFORM")
    print("=" * 65)
    print(f" * Web UI & Dashboard: http://{host}:{port}")
    print(f" * REST API Endpoint:  http://{host}:{port}/api/apps")
    print(f" * Storage Directory:  {os.path.abspath(storage_root)}")
    print(f" * Sample Datasets:    Quantum Computing, Enterprise SaaS, Oncology")
    print("=" * 65)

    factory = RAGFactory(storage_root=storage_root)
    app = create_web_app(factory=factory)
    app.run(host=host, port=port, debug=False)

if __name__ == "__main__":
    main()
