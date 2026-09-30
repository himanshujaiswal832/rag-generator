"""
Command-Line Interface (CLI) for RAG Generator
"""

import os
import sys
import argparse
from typing import Optional
from rag_generator.core.factory import RAGFactory
from rag_generator.core.models import QueryRequest, RAGAppConfig


def format_table(rows, headers):
    """Simple terminal table formatter."""
    col_widths = [len(h) for h in headers]
    for row in rows:
        for i, val in enumerate(row):
            col_widths[i] = max(col_widths[i], len(str(val)))

    header_str = " | ".join(h.ljust(col_widths[i]) for i, h in enumerate(headers))
    sep_str = "-+-".join("-" * col_widths[i] for i in range(len(headers)))
    out = [header_str, sep_str]
    for row in rows:
        out.append(" | ".join(str(val).ljust(col_widths[i]) for i, val in enumerate(row)))
    return "\n".join(out)


def cmd_create(args, factory: RAGFactory):
    print(f"\n[*] Creating RAG Application '{args.name}'...")
    config = RAGAppConfig(
        name=args.name,
        description=args.desc or f"RAG Application for {args.name}",
        chunk_size=args.chunk_size,
        chunk_overlap=args.chunk_overlap,
        hybrid_alpha=args.alpha,
        llm_provider=args.provider,
    )

    files_list = []
    if args.docs:
        for p in args.docs:
            if os.path.exists(p):
                files_list.append(os.path.abspath(p))
            else:
                print(f"[!] Warning: Path not found: {p}")

    app_instance = factory.create_app(
        name=args.name,
        description=args.desc or "",
        config_override=config,
        files=files_list,
    )

    meta = app_instance.get_metadata()
    print(f"[+] Successfully created RAG Application!")
    print(f"    • App ID: {meta.app_id}")
    print(f"    • Documents Ingested: {meta.document_count}")
    print(f"    • Total Chunks: {meta.chunk_count}")
    print(f"    • Total Tokens (est): {meta.total_tokens_estimate}")
    print(f"    • Storage Directory: {os.path.join(factory.storage_root, meta.app_id)}")
    print(f"\nTo query this app, run:")
    print(f"  python -m rag_generator.cli query --app {meta.app_id} --question \"Your question\"\n")


def cmd_list(args, factory: RAGFactory):
    apps = factory.list_apps()
    print(f"\n=== Registered RAG Applications ({len(apps)}) ===")
    if not apps:
        print("No applications created yet. Run 'rag-generator create --help' to create one.")
        return

    rows = []
    for a in apps:
        rows.append([
            a.app_id,
            a.name[:25],
            a.document_count,
            a.chunk_count,
            ", ".join(a.file_types) or "None",
        ])

    headers = ["App ID", "Name", "Docs", "Chunks", "File Types"]
    print(format_table(rows, headers))
    print()


def cmd_query(args, factory: RAGFactory):
    app_id = args.app
    if not app_id:
        apps = factory.list_apps()
        if not apps:
            print("[!] No RAG applications found. Please create one first.")
            return
        app_id = apps[0].app_id
        print(f"[*] Defaulting to latest application: {app_id}")

    instance = factory.get_app(app_id)
    if not instance:
        print(f"[!] Error: Application '{app_id}' not found.")
        return

    q = args.question
    if not q:
        q = input("\nEnter your question: ").strip()
        if not q:
            return

    print(f"\n[*] Querying RAG App '{instance.config.name}' ({app_id})...")
    req = QueryRequest(
        question=q,
        top_k=args.top_k,
        hybrid_alpha=args.alpha,
        llm_provider=args.provider,
        api_key=args.api_key,
    )

    answer = instance.query(req)

    print(f"\n{'='*60}")
    print(f"QUESTION: {answer.question}")
    print(f"{'='*60}")
    print(f"ANSWER:\n{answer.answer}")
    print(f"\n{'-'*60}")
    print(f"GROUNDING & EVALUATION METRICS:")
    print(f"  • Confidence: {answer.confidence}")
    print(f"  • Groundedness Score: {answer.groundedness_score * 100:.1f}%")
    print(f"  • Latency: {answer.latency_ms:.1f}ms (Retrieval: {answer.retrieval_latency_ms:.1f}ms, Gen: {answer.generation_latency_ms:.1f}ms)")
    print(f"  • Model Used: {answer.model_used}")
    print(f"  • Retrieved Chunks: {answer.retrieved_chunk_count}")

    if answer.citations:
        print(f"\nVERIFIED CITATIONS ({len(answer.citations)}):")
        for idx, cit in enumerate(answer.citations, 1):
            print(f"  [{idx}] {cit.source_name} (Page {cit.page_number}) | Relevance: {cit.relevance_score:.2f}")
            print(f"      Quote: \"{cit.snippet}\"")
    print(f"{'='*60}\n")


def cmd_export(args, factory: RAGFactory):
    instance = factory.get_app(args.app)
    if not instance:
        print(f"[!] Error: Application '{args.app}' not found.")
        return

    out_dir = args.output or "./exported_apps"
    os.makedirs(out_dir, exist_ok=True)
    from rag_generator.export.exporter import AppExporter
    zip_p = AppExporter.export_standalone_bundle(instance, out_dir, create_zip=True)
    print(f"[+] Successfully exported standalone application:")
    print(f"    {zip_p}\n")


def cmd_serve(args, factory: RAGFactory):
    from rag_generator.app import create_web_app
    app = create_web_app(factory)
    print(f"\n🚀 Starting RAG Generator Web UI & REST API on http://{args.host}:{args.port}")
    app.run(host=args.host, port=args.port, debug=args.debug)


def main():
    parser = argparse.ArgumentParser(
        prog="rag-generator",
        description="Dynamic RAG Application Generator - Ingest documents at runtime, create isolated RAG apps, query with grounded citations",
    )
    parser.add_argument("--storage", default="./data/apps", help="Directory for RAG apps storage")

    subparsers = parser.add_subparsers(dest="command", help="Command to run")

    # Create command
    create_p = subparsers.add_parser("create", help="Create a new RAG application over documents")
    create_p.add_argument("--name", required=True, help="Application name")
    create_p.add_argument("--desc", default="", help="Application description")
    create_p.add_argument("--docs", nargs="+", help="Files or directory containing documents to ingest")
    create_p.add_argument("--chunk-size", type=int, default=500, help="Chunk size in characters")
    create_p.add_argument("--chunk-overlap", type=int, default=80, help="Chunk overlap in characters")
    create_p.add_argument("--alpha", type=float, default=0.5, help="Hybrid alpha (0.0 BM25 to 1.0 Dense)")
    create_p.add_argument("--provider", default="local_grounded", help="LLM provider: local_grounded, openai, ollama")

    # List command
    subparsers.add_parser("list", help="List all generated RAG applications")

    # Query command
    query_p = subparsers.add_parser("query", help="Query a RAG application")
    query_p.add_argument("--app", help="Application ID")
    query_p.add_argument("--question", "-q", help="Question to ask")
    query_p.add_argument("--top-k", type=int, default=4, help="Top K retrieved chunks")
    query_p.add_argument("--alpha", type=float, default=0.5, help="Hybrid alpha balance")
    query_p.add_argument("--provider", default="local_grounded", help="LLM provider")
    query_p.add_argument("--api-key", help="API Key if using OpenAI")

    # Export command
    export_p = subparsers.add_parser("export", help="Export standalone RAG app package")
    export_p.add_argument("--app", required=True, help="Application ID to export")
    export_p.add_argument("--output", default="./exported_apps", help="Output directory")

    # Serve command
    serve_p = subparsers.add_parser("serve", help="Launch Web UI & REST API")
    serve_p.add_argument("--host", default="127.0.0.1", help="Host address")
    serve_p.add_argument("--port", type=int, default=5000, help="Port")
    serve_p.add_argument("--debug", action="store_true", help="Enable Flask debug mode")

    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        return

    factory = RAGFactory(storage_root=args.storage)

    if args.command == "create":
        cmd_create(args, factory)
    elif args.command == "list":
        cmd_list(args, factory)
    elif args.command == "query":
        cmd_query(args, factory)
    elif args.command == "export":
        cmd_export(args, factory)
    elif args.command == "serve":
        cmd_serve(args, factory)


if __name__ == "__main__":
    main()
