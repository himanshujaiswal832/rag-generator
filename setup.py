from setuptools import setup, find_packages

setup(
    name="rag-generator",
    version="1.0.0",
    description="Dynamic RAG Application Generator - Ingest documents at runtime, create isolated RAG apps, query with grounded citations",
    author="Candidate",
    packages=find_packages(),
    python_requires=">=3.9",
    install_requires=[
        "flask>=3.0.0",
        "flask-cors>=4.0.0",
        "pydantic>=2.0.0",
        "rank-bm25>=0.2.2",
        "sentence-transformers>=2.2.0",
        "torch>=2.0.0",
        "pypdf>=4.0.0",
        "python-docx>=1.0.0",
        "numpy>=1.24.0",
        "scikit-learn>=1.1.0",
        "openai>=1.0.0",
        "requests>=2.28.0",
        "beautifulsoup4>=4.11.0",
    ],
    entry_points={
        "console_scripts": [
            "rag-generator=rag_generator.cli:main",
        ],
    },
)
