"""
Flask Web Application & REST API Server for RAG Generator
"""

import os
import json
import time
from typing import Optional
from flask import Flask, request, jsonify, render_template, send_file, send_from_directory
from flask_cors import CORS
from werkzeug.utils import secure_filename

from rag_generator.core.factory import RAGFactory
from rag_generator.core.models import QueryRequest, RAGAppConfig
from rag_generator.export.exporter import AppExporter


def create_web_app(factory: Optional[RAGFactory] = None) -> Flask:
    """Create and configure the Flask web application and API."""
    current_dir = os.path.dirname(os.path.abspath(__file__))
    templates_dir = os.path.join(current_dir, "web", "templates")
    static_dir = os.path.join(current_dir, "web", "static")

    app = Flask(
        __name__,
        template_folder=templates_dir,
        static_folder=static_dir,
    )
    CORS(app)

    if factory is None:
        factory = RAGFactory(storage_root="./data/apps")

    # Ensure uploads temp folder exists
    upload_tmp = os.path.abspath("./data/uploads")
    os.makedirs(upload_tmp, exist_ok=True)

    # Auto-seed sample apps if none exist
    def seed_samples_if_empty():
        if not factory.list_apps():
            sample_root = os.path.abspath("./data/sample_documents")
            if os.path.exists(sample_root):
                # Sample 1: Quantum Computing
                qc_path = os.path.join(sample_root, "quantum_computing")
                if os.path.exists(qc_path):
                    factory.create_app(
                        name="Quantum Computing Research",
                        description="Deep tech documentation on superconducting transmon qubits and surface codes.",
                        files=[qc_path],
                    )

                # Sample 2: SaaS MSA
                saas_path = os.path.join(sample_root, "saas_enterprise_agreement")
                if os.path.exists(saas_path):
                    factory.create_app(
                        name="Enterprise SaaS MSA & SLA",
                        description="Master Services Agreement, 99.95% SLA terms, and GDPR data protection clauses.",
                        files=[saas_path],
                    )

                # Sample 3: Oncology Clinical Trial
                med_path = os.path.join(sample_root, "oncology_clinical_trial")
                if os.path.exists(med_path):
                    factory.create_app(
                        name="Oncology Clinical Trial (TX-409)",
                        description="Phase II protocol for Claudin-18.2 monoclonal antibody, endpoints, and adverse events.",
                        files=[med_path],
                    )

    try:
        seed_samples_if_empty()
    except Exception as e:
        print(f"Warning during sample seeding: {e}")

    # --- UI Route ---
    @app.route("/")
    def index():
        return render_template("index.html")

    # --- REST API Endpoints ---
    @app.route("/api/health", methods=["GET"])
    def health():
        return jsonify({
            "status": "healthy",
            "version": "1.0.0",
            "active_applications": len(factory.list_apps()),
            "supported_formats": [".pdf", ".docx", ".txt", ".md", ".csv", ".tsv", ".json", ".html"],
            "embedding_providers": ["sentence-transformers", "tfidf_fallback", "openai"],
            "llm_providers": ["local_grounded_synthesizer", "openai", "ollama"],
        })

    @app.route("/api/apps", methods=["GET"])
    def list_applications():
        apps = factory.list_apps()
        return jsonify([a.model_dump() for a in apps])

    @app.route("/api/apps", methods=["POST"])
    def create_application():
        # Handle multipart/form-data or JSON
        if request.content_type and "multipart/form-data" in request.content_type:
            name = request.form.get("name", "Untitled RAG Application").strip()
            desc = request.form.get("description", "").strip()
            chunk_size = int(request.form.get("chunk_size", 500))
            chunk_overlap = int(request.form.get("chunk_overlap", 80))
            alpha = float(request.form.get("hybrid_alpha", 0.5))
            provider = request.form.get("llm_provider", "local_grounded")
            emb_model = request.form.get("embedding_model", "all-MiniLM-L6-v2")

            config = RAGAppConfig(
                name=name,
                description=desc,
                chunk_size=chunk_size,
                chunk_overlap=chunk_overlap,
                hybrid_alpha=alpha,
                llm_provider=provider,
                embedding_model=emb_model,
            )

            # Create base app instance
            app_inst = factory.create_app(name=name, description=desc, config_override=config)

            # Process uploaded files
            files = request.files.getlist("files")
            uploaded_count = 0
            for f in files:
                if f and f.filename:
                    fname = secure_filename(f.filename)
                    file_bytes = f.read()
                    if file_bytes:
                        app_inst.ingest_bytes(file_bytes=file_bytes, filename=fname)
                        uploaded_count += 1

            # Ingest raw text if provided
            raw_text = request.form.get("raw_text", "").strip()
            text_title = request.form.get("text_title", "Uploaded_Text.txt").strip()
            if raw_text:
                app_inst.ingest_raw_text(text=raw_text, title=text_title)

            app_inst.save_to_disk()
            return jsonify({
                "message": "Application created successfully",
                "application": app_inst.get_metadata().model_dump(),
                "uploaded_files_count": uploaded_count,
            }), 201

        # JSON payload
        data = request.get_json(force=True) or {}
        name = data.get("name", "Untitled RAG Application").strip()
        desc = data.get("description", "").strip()
        chunk_size = int(data.get("chunk_size", 500))
        chunk_overlap = int(data.get("chunk_overlap", 80))
        alpha = float(data.get("hybrid_alpha", 0.5))
        provider = data.get("llm_provider", "local_grounded")
        emb_model = data.get("embedding_model", "all-MiniLM-L6-v2")

        config = RAGAppConfig(
            name=name,
            description=desc,
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            hybrid_alpha=alpha,
            llm_provider=provider,
            embedding_model=emb_model,
        )

        app_inst = factory.create_app(
            name=name,
            description=desc,
            config_override=config,
            files=data.get("files", []),
            raw_texts=data.get("raw_texts", []),
        )

        return jsonify({
            "message": "Application created successfully",
            "application": app_inst.get_metadata().model_dump(),
        }), 201

    @app.route("/api/apps/<app_id>", methods=["GET"])
    def get_application(app_id):
        inst = factory.get_app(app_id)
        if not inst:
            return jsonify({"error": f"Application '{app_id}' not found"}), 404
        return jsonify(inst.get_metadata().model_dump())

    @app.route("/api/apps/<app_id>", methods=["DELETE"])
    def delete_application(app_id):
        deleted = factory.delete_app(app_id)
        if not deleted:
            return jsonify({"error": f"Application '{app_id}' not found"}), 404
        return jsonify({"message": f"Application '{app_id}' successfully deleted"})

    @app.route("/api/apps/<app_id>/documents", methods=["POST"])
    def add_documents_at_runtime(app_id):
        """Dynamically ingest additional documents into an existing RAG app at runtime."""
        inst = factory.get_app(app_id)
        if not inst:
            return jsonify({"error": f"Application '{app_id}' not found"}), 404

        added_docs = 0
        added_chunks = 0

        if request.content_type and "multipart/form-data" in request.content_type:
            files = request.files.getlist("files")
            for f in files:
                if f and f.filename:
                    fname = secure_filename(f.filename)
                    fbytes = f.read()
                    if fbytes:
                        doc, chunks_count = inst.ingest_bytes(fbytes, filename=fname)
                        added_docs += 1
                        added_chunks += chunks_count

            raw_text = request.form.get("raw_text", "").strip()
            text_title = request.form.get("text_title", "Document.txt").strip()
            if raw_text:
                doc, chunks_count = inst.ingest_raw_text(raw_text, title=text_title)
                added_docs += 1
                added_chunks += chunks_count
        else:
            data = request.get_json(force=True) or {}
            if "raw_text" in data:
                text = data["raw_text"]
                title = data.get("title", "Document.txt")
                doc, chunks_count = inst.ingest_raw_text(text, title=title)
                added_docs += 1
                added_chunks += chunks_count

        inst.save_to_disk()
        return jsonify({
            "message": f"Successfully ingested {added_docs} documents ({added_chunks} chunks)",
            "application": inst.get_metadata().model_dump(),
        })

    @app.route("/api/apps/<app_id>/query", methods=["POST"])
    def query_application(app_id):
        inst = factory.get_app(app_id)
        if not inst:
            return jsonify({"error": f"Application '{app_id}' not found"}), 404

        data = request.get_json(force=True) or {}
        question = data.get("question", "").strip()
        if not question:
            return jsonify({"error": "Query 'question' is required"}), 400

        req = QueryRequest(
            question=question,
            top_k=data.get("top_k"),
            hybrid_alpha=data.get("hybrid_alpha"),
            llm_provider=data.get("llm_provider"),
            model_name=data.get("model_name"),
            api_key=data.get("api_key"),
            api_base=data.get("api_base"),
            min_relevance=data.get("min_relevance"),
            temperature=data.get("temperature", 0.1),
        )

        answer = inst.query(req)
        return jsonify(answer.model_dump())

    @app.route("/api/apps/<app_id>/chunks", methods=["GET"])
    def get_application_chunks(app_id):
        inst = factory.get_app(app_id)
        if not inst:
            return jsonify({"error": f"Application '{app_id}' not found"}), 404

        limit = int(request.args.get("limit", 100))
        search_kw = request.args.get("search", "").strip().lower()

        all_chunks = inst.get_chunks(limit=1000)
        if search_kw:
            all_chunks = [c for c in all_chunks if search_kw in c.get("content", "").lower()]

        return jsonify({
            "app_id": app_id,
            "total_chunks": len(inst.vector_store.chunks),
            "matched_chunks": len(all_chunks),
            "chunks": all_chunks[:limit],
        })

    @app.route("/api/apps/<app_id>/export", methods=["GET"])
    def export_application(app_id):
        inst = factory.get_app(app_id)
        if not inst:
            return jsonify({"error": f"Application '{app_id}' not found"}), 404

        export_dir = os.path.abspath("./exported_apps")
        os.makedirs(export_dir, exist_ok=True)
        zip_path = AppExporter.export_standalone_bundle(inst, export_dir, create_zip=True)

        return send_file(
            zip_path,
            as_attachment=True,
            download_name=f"{app_id}_standalone_rag.zip",
            mimetype="application/zip",
        )

    @app.route("/api/sample-apps/init", methods=["POST"])
    def reseed_sample_apps():
        seed_samples_if_empty()
        apps = factory.list_apps()
        return jsonify({
            "message": "Sample applications initialized",
            "applications": [a.model_dump() for a in apps],
        })

    return app
