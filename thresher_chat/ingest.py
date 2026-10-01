#!/usr/bin/env python3
"""Index the THRESHER repository into a ChromaDB vector store for RAG."""

import glob
import json
import os
import sys

from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import TextLoader
from langchain_chroma import Chroma
from langchain_ollama import OllamaEmbeddings

from thresher_chat.config import (
    CODE_CHUNK_OVERLAP,
    CODE_CHUNK_SIZE,
    CODE_EXTENSIONS,
    DOC_CHUNK_OVERLAP,
    DOC_CHUNK_SIZE,
    DOC_EXTENSIONS,
    SKIP_DIRS,
    SKIP_FILES,
    DEFAULT_EMBED_MODEL,
)


def should_skip(path):
    """Check if a path should be skipped based on SKIP_DIRS or SKIP_FILES."""
    parts = path.split(os.sep)
    if any(skip_dir in parts for skip_dir in SKIP_DIRS):
        return True
    if os.path.basename(path) in SKIP_FILES:
        return True
    return False


def load_documents(source_path):
    """Load all relevant files from the repo and guides directories."""
    docs = []
    file_count = {"Python": 0, "R": 0, "Documentation": 0, "Snakemake": 0, "Total": 0}

    # Code files
    for ext in CODE_EXTENSIONS:
        for path in glob.glob(os.path.join(source_path, "**", ext), recursive=True):
            if should_skip(path):
                continue
            try:
                # Special handling to label Snakemake files correctly
                filename = os.path.basename(path)
                loader = TextLoader(path, encoding="utf-8")
                loaded = loader.load()
                rel_path = os.path.relpath(path, source_path)
                # I use 3 types of code files: Python, R, and Snakemake
                
                # Determine file type based on extension/name
                if path.endswith(".smk") or filename.startswith("Snakefile"):
                    ftype = "Snakemake"
                elif path.endswith((".R", ".r")):
                    ftype = "R"
                elif path.endswith(".py"):
                    ftype = "Python"
                else:
                    ftype = "Other"

                for doc in loaded:
                    doc.metadata["source"] = rel_path
                    doc.metadata["type"] = ftype
                docs.extend(loaded)
                file_count[ftype] += 1
                file_count["Total"] += 1
            except Exception as e:
                print(f"  Skipping {path}: {e}", file=sys.stderr)

    # Documentation files
    for ext in DOC_EXTENSIONS:
        for path in glob.glob(os.path.join(source_path, "**", ext), recursive=True):
            if should_skip(path):
                continue
            try:
                loader = TextLoader(path, encoding="utf-8")
                loaded = loader.load()
                rel_path = os.path.relpath(path, source_path)
                for doc in loaded:
                    doc.metadata["source"] = rel_path
                    doc.metadata["type"] = "Documentation"
                docs.extend(loaded)
                file_count["Documentation"] += 1
            except Exception as e:
                print(f"  Skipping {path}: {e}", file=sys.stderr)

    print(f" Loaded files: {json.dumps(file_count, indent=2)}")
    return docs


def chunk_documents(docs):
    """Split documents into chunks with appropriate strategies for code vs docs."""
    code_splitter = RecursiveCharacterTextSplitter(
        chunk_size=CODE_CHUNK_SIZE,
        chunk_overlap=CODE_CHUNK_OVERLAP,
        separators=[
            # Python - classes, functions, decorators
            "\nclass ", "\ndef ", "\nasync def ",
            "\n\tdef ", "\n    def ",
            "\n\tasync def ", "\n    async def ",
            "\n@", "\n\t@", "\n    @",
            "\nif __name__",
            # Python - control flow / structure
            "\n\tif ", "\n    if ",
            "\n\tfor ", "\n    for ",
            "\n\twith ", "\n    with ",
            "\n\ttry:", "\n    try:",
            "\n\treturn ", "\n    return ",
            # Snakemake - rules and directives
            "\nrule ", "\ncheckpoint ", "\nmodule ",
            "\nonstart:", "\nonsuccess:", "\nonerror:",
            "\n    input:", "\n    output:", "\n    params:",
            "\n    log:", "\n    threads:", "\n    resources:",
            "\n    conda:", "\n    shell:", "\n    run:",
            "\n    benchmark:", "\n    wildcard_constraints:",
            "\n    message:", "\n    priority:",
            "\nconfigfile:", "\ninclude:", "\nworkdir:",
            "\nwildcard_constraints:", "\nruleorder:",
            # R - functions and assignment
            "\n<- function(", "\n<-function(",
            "\n<- \\(", "\n<-\\(",
            "\n= function(", "\n=function(",
            # R - control flow
            "\nif (", "\nif(",
            "\nfor (", "\nfor(",
            "\nwhile (", "\nwhile(",
            "\ntryCatch(", "\ntryCatch (",
            # R - tidyverse / ggplot
            "\n%>%\n", "\n|>\n",
            "\n+\n",
            # R - library and source
            "\nlibrary(", "\nrequire(",
            "\nsource(", "\nsuppressPackageStartupMessages(",
            # Shell - functions and structure
            "\nfunction ", "\n#!/",
            # Shell - control flow
            "\nif [", "\nif [[", "\nif (",
            "\nfor ", "\nwhile ",
            "\ncase ", "\nselect ",
            "\nthen\n", "\ndo\n",
            "\nfi\n", "\ndone\n", "\nesac\n",
            # Shell - common patterns
            "\nexport ", "\nreadonly ",
            "\nlocal ", "\ndeclare ",
            "\nsource ", "\n. ",
            "\ntrap ",
            # Comments as section markers (all languages)
            "\n# ",
            "\n# ---", "\n# ===", "\n# ***",
            "\n# TODO", "\n# FIXME", "\n# NOTE",
            "\n## ", "\n### ",
            "\n#---", "\n#===",
            # General structure (fallbacks)
            "\n\n\n", "\n\n", "\n", " ", "",
        ],
    )
    doc_splitter = RecursiveCharacterTextSplitter(
        chunk_size=DOC_CHUNK_SIZE,
        chunk_overlap=DOC_CHUNK_OVERLAP,
        separators=[
            # Markdown headings
            "\n# ", "\n## ", "\n### ", "\n#### ", "\n##### ", "\n###### ",
            # Markdown horizontal rules
            "\n---\n", "\n***\n", "\n___\n",
            # Markdown fenced code blocks
            "\n```\n", "\n~~~\n",
            # Markdown block quotes
            "\n> ", "\n>> ",
            # Markdown tables
            "\n| ",
            # Markdown lists - unordered
            "\n- ", "\n* ", "\n+ ",
            "\n  - ", "\n  * ", "\n  + ",
            "\n    - ", "\n    * ", "\n    + ",
            # Markdown lists - ordered
            "\n1. ", "\n2. ", "\n3. ",
            "\n   1. ", "\n   2. ",
            # Markdown definition lists / details
            "\n<details", "\n<summary",
            # Markdown admonitions (GitHub/MkDocs)
            "\n> [!", "\n> **Note", "\n> **Warning",
            "\n!!! ", "\n??? ",
            # Markdown HTML blocks
            "\n<div", "\n<table", "\n<pre",
            "\n<p>", "\n<br",
            # Markdown images and links (block level)
            "\n![", "\n[!",
            # Markdown footnotes
            "\n[^",
            # Whitespace fallbacks
            "\n\n\n", "\n\n", "\n", ". ", ", ", " ", "",
        ],
    )

    chunks = []
    for doc in docs:
        if doc.metadata.get("type") in ("Python", "R", "Snakemake", "Other"):
            chunks.extend(code_splitter.split_documents([doc]))
        else:
            chunks.extend(doc_splitter.split_documents([doc]))

    return chunks


def build_vectordb(chunks, db_dir, embed_model):
    """Create the ChromaDB vector store from document chunks."""
    print(f"\nCreating embeddings with {embed_model}...")
    embeddings = OllamaEmbeddings(model=embed_model)

    # Remove existing DB if present
    if os.path.exists(db_dir):
        # Show warning
        print(f"WARNING: Removing existing vector DB at {db_dir}")
        import shutil
        shutil.rmtree(db_dir)

    os.makedirs(db_dir, exist_ok=True)

    vectordb = Chroma.from_documents(
        documents=chunks,
        embedding=embeddings,
        persist_directory=db_dir,
    )
    return vectordb


def save_config(db_dir, repo_path,  embed_model):
    """Save configuration for the chatbot to use."""
    os.makedirs(db_dir, exist_ok=True)
    config = {
        "repo_path": os.path.abspath(repo_path),
        "embed_model": embed_model,
        "db_dir": db_dir,
    }
    config_path = os.path.join(db_dir, "config.json")
    with open(config_path, "w") as f:
        json.dump(config, f, indent=2)
    print(f"Configuration saved to {config_path}")


def run(args):
    """Run the ingest pipeline. Called from cli.py."""
    if not os.path.isdir(args.repo):
        print(f"ERROR: Repository path does not exist: {args.repo}")
        sys.exit(1)

    # Guides directory is always relative to the THRESHER_CHAT package root
    guides_dir = os.path.join(os.path.dirname(__file__), "guides")
    embed_model = args.embed_model or DEFAULT_EMBED_MODEL
    print(f"Indexing THRESHER repository: {args.repo}")
    print(f"Indexing guides: {guides_dir}")
    print(f"DataBase directory: {args.db_dir}")
    print(f"Embedding model: {embed_model}")
    print()

    # Load docs from repo
    print("Loading documents from repository...")
    docs = load_documents(args.repo)
    if not docs:
        print("ERROR: No documents found.")
        sys.exit(1)

    # Load docs from guides
    print("Loading documents from guides...")
    guide_docs = load_documents(guides_dir)
    docs.extend(guide_docs)

    chunks = chunk_documents(docs)
    print(f"\nCreated {len(chunks)} chunks total")

    # Build vector store
    build_vectordb(chunks, args.db_dir, embed_model)
    print(f"Vector DB stored at {args.db_dir}")

    # Save config
    save_config(args.db_dir, args.repo, embed_model)

    print("\nIndexing complete!")