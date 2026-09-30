"""
RAG Application Factory - Orchestrates runtime creation, lifecycle, and persistence of RAG apps
"""

import os
import shutil
import uuid
import re
from typing import Dict, List, Optional, Union
from rag_generator.core.models import (
    RAGAppConfig,
    RAGAppMetadata,
    Document,
)
from rag_generator.core.instance import RAGApplicationInstance


class RAGFactory:
    """Factory responsible for instantiating, discovering, and managing RAG applications."""

    def __init__(self, storage_root: str = "./data/apps"):
        self.storage_root = os.path.abspath(storage_root)
        os.makedirs(self.storage_root, exist_ok=True)
        self._instances: Dict[str, RAGApplicationInstance] = {}
        self._load_persisted_apps()

    def _slugify(self, text: str) -> str:
        """Create URL-safe slug from app name."""
        s = re.sub(r"[^\w\s-]", "", text.lower()).strip()
        s = re.sub(r"[-\s]+", "-", s)
        return s or "rag-app"

    def create_app(
        self,
        name: str,
        description: str = "",
        config_override: Optional[RAGAppConfig] = None,
        files: Optional[List[str]] = None,
        raw_texts: Optional[List[Dict[str, str]]] = None,
    ) -> RAGApplicationInstance:
        """
        Dynamically instantiate a new RAG Application over provided documents at runtime.
        """
        slug = self._slugify(name)
        short_id = uuid.uuid4().hex[:6]
        app_id = f"{slug}-{short_id}"

        if config_override:
            config = config_override
            config.app_id = app_id
            config.name = name
            if description:
                config.description = description
        else:
            config = RAGAppConfig(
                app_id=app_id,
                name=name,
                description=description or f"RAG Application for {name}",
            )

        # Instantiate isolated app pipeline
        instance = RAGApplicationInstance(config=config, storage_dir=self.storage_root)

        # Ingest files if provided
        if files:
            for file_path in files:
                if os.path.exists(file_path):
                    if os.path.isdir(file_path):
                        for root, _, fnames in os.walk(file_path):
                            for fn in fnames:
                                full_p = os.path.join(root, fn)
                                try:
                                    instance.ingest_file(full_p)
                                except Exception as e:
                                    print(f"Error ingesting {full_p}: {e}")
                    else:
                        try:
                            instance.ingest_file(file_path)
                        except Exception as e:
                            print(f"Error ingesting {file_path}: {e}")

        # Ingest raw text snippets if provided
        if raw_texts:
            for item in raw_texts:
                content = item.get("content", "")
                title = item.get("title", "Document.txt")
                if content.strip():
                    instance.ingest_raw_text(content, title=title)

        # Register in memory and save to disk
        self._instances[app_id] = instance
        instance.save_to_disk()

        return instance

    def get_app(self, app_id: str) -> Optional[RAGApplicationInstance]:
        """Fetch active application instance by ID."""
        if app_id in self._instances:
            return self._instances[app_id]

        # Check if exists on disk
        app_dir = os.path.join(self.storage_root, app_id)
        if os.path.isdir(app_dir):
            try:
                instance = RAGApplicationInstance.load_from_disk(app_dir, self.storage_root)
                self._instances[app_id] = instance
                return instance
            except Exception as e:
                print(f"Failed to load app {app_id} from disk: {e}")

        return None

    def list_apps(self) -> List[RAGAppMetadata]:
        """List metadata for all available applications."""
        result = []
        for app_id, inst in self._instances.items():
            result.append(inst.get_metadata())
        # Sort by updated_at descending
        result.sort(key=lambda x: x.updated_at, reverse=True)
        return result

    def delete_app(self, app_id: str) -> bool:
        """Delete application instance and its storage directory."""
        if app_id in self._instances:
            del self._instances[app_id]

        app_dir = os.path.join(self.storage_root, app_id)
        if os.path.exists(app_dir):
            shutil.rmtree(app_dir, ignore_errors=True)
            return True
        return False

    def _load_persisted_apps(self) -> None:
        """Discover and load apps previously created and saved in storage_root."""
        if not os.path.exists(self.storage_root):
            return

        for item in os.listdir(self.storage_root):
            app_dir = os.path.join(self.storage_root, item)
            if os.path.isdir(app_dir) and os.path.exists(os.path.join(app_dir, "config.json")):
                try:
                    instance = RAGApplicationInstance.load_from_disk(app_dir, self.storage_root)
                    self._instances[instance.app_id] = instance
                except Exception as e:
                    print(f"Failed to auto-load app in {item}: {e}")
