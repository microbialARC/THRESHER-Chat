#!/usr/bin/env python3
"""THRESHER-Chat: Local offline chatbot for the THRESHER phylogenomics toolkit."""

import json
import os
import sys

from langchain_chroma import Chroma
from langchain_core.messages import AIMessage, HumanMessage
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.runnables import RunnablePassthrough
from langchain_ollama import ChatOllama, OllamaEmbeddings
import random

from thresher_chat.config import (
    DEFAULT_DB_DIR,
    DEFAULT_EMBED_MODEL,
    DEFAULT_MODEL,
    MEMORY_WINDOW,
    RETRIEVER_K,
    SYSTEM_PROMPT,
)

# Debug mode — set via --debug flag in CLI or toggled programmatically
DEBUG_MODE = False


def debug_log(msg):
    """Print debug message only when DEBUG_MODE is enabled."""
    if DEBUG_MODE:
        print(f"[DEBUG] {msg}")


def load_config(db_dir):
    """Load saved configuration from the vector DB directory."""
    config_path = os.path.join(db_dir, "config.json")
    if os.path.exists(config_path):
        with open(config_path) as f:
            return json.load(f)
    return {}

def format_docs(docs):
    """Format retrieved documents with origin tags for the LLM.
    
    Fenced code blocks are wrapped with protection markers to instruct
    the model to reproduce them exactly as written.
    """
    import re
    parts = []
    for doc in docs:
        source = os.path.basename(doc.metadata.get("source", "unknown"))
        content = doc.page_content
        # Wrap fenced code blocks with protection markers
        content = re.sub(
            r"(```\w*\n)(.*?)(```)",
            r"EXACT COPY REQUIRED — do not modify anything below:\n\1\2\3\nEND EXACT COPY",
            content,
            flags=re.DOTALL,
        )
        parts.append(f"[{source}]\n{content}")
    return "\n\n".join(parts)


def check_doc_passthrough(source_docs):
    """Check if the top retrieved result is documentation that should be
    passed through directly without LLM processing.

    Returns the combined markdown content from all matching doc chunks
    of the same source file, or None if passthrough doesn't apply.
    """
    if not source_docs:
        return None

    top_doc = source_docs[0]
    top_type = top_doc.metadata.get("type", "")
    top_source = top_doc.metadata.get("source", "")

    # Only passthrough for Documentation files under docs/
    if top_type != "Documentation" or not top_source.startswith("docs/"):
        return None

    # Gather all retrieved chunks from the same source file
    # to reconstruct the full document section
    parts = []
    for doc in source_docs:
        if doc.metadata.get("source") == top_source:
            parts.append(doc.page_content)

    if not parts:
        return None

    filename = os.path.basename(top_source)
    content = "\n\n".join(parts)
    return f"From **{filename}**:\n\n{content}"


def build_chain(model, embed_model, db_dir):
    """Build the RAG chain"""
    embeddings = OllamaEmbeddings(model=embed_model)
    vectordb = Chroma(
        persist_directory=db_dir,
        embedding_function=embeddings,
    )
    retriever = vectordb.as_retriever(
        search_type="similarity",
        search_kwargs={"k": RETRIEVER_K},
    )

    # Set the temperature for the LLM to 0.0 for deterministic responses to reduce delusions
    llm = ChatOllama(model=model, temperature=0.0)

    prompt = ChatPromptTemplate.from_messages([
        ("system", SYSTEM_PROMPT),
        MessagesPlaceholder(variable_name="chat_history"),
        ("human", "{question}"),
    ])

    def get_context(x):
        rag_context = format_docs(retriever.invoke(x["question"]))
        if DEBUG_MODE:
            print("=" * 60)
            print("[DEBUG] CONTEXT SENT TO LLM:")
            print(rag_context[:5000])
            if len(rag_context) > 5000:
                print(f"... ({len(rag_context)} chars total, truncated)")
            print("=" * 60)
        return rag_context

    chain = (
        RunnablePassthrough.assign(context=get_context)
        | prompt
        | llm
        | StrOutputParser()
    )
    return chain, retriever


def format_sources(source_docs):
    """Format source documents for display."""
    sources = {}
    for doc in source_docs:
        src = doc.metadata.get("source", "unknown")
        origin = doc.metadata.get("origin", "repo")
        ftype = doc.metadata.get("type", "unknown")
        sources[src] = (origin, ftype)
    return sources


def run(args):
    """Run the interactive CLI chatbot. Called from cli.py."""
    global DEBUG_MODE
    DEBUG_MODE = getattr(args, "debug", False)

    db_dir = args.db_dir or DEFAULT_DB_DIR
    # Check vector DB exists
    if not os.path.exists(db_dir):
        print("ERROR: Vector database not found.")
        print("Please index the THRESHER repository first:")
        print("thresher-chat ingest --repo /path/to/thresher_repo")
        sys.exit(1)
    # Load config and apply overrides
    config = load_config(db_dir)
    model = args.model or config.get("model", DEFAULT_MODEL)
    embed_model = args.embed_model or config.get("embed_model", DEFAULT_EMBED_MODEL)
    

    print("Loading THRESHER knowledge base...")
    print(f"  Model: {model}")
    print(f"  Embedding: {embed_model}")
    if DEBUG_MODE:
        print(f"  Debug mode: ON")
        print(f"  RETRIEVER_K: {RETRIEVER_K}")
    print()

    try:
        chain, retriever = build_chain(model, embed_model, db_dir)
    except Exception as e:
        print(f"ERROR: Failed to initialize chatbot: {e}")
        print("\nTroubleshooting:")
        print("  - Is Ollama running? (ollama serve)")
        print(f"  - Is the model pulled? (ollama pull {model})")
        print(f"  - Is the embedding model pulled? (ollama pull {embed_model})")
        sys.exit(1)

    print("=" * 60)
    print("THRESHER-Chat ready!")
    print("Ask questions about THRESHER's algorithms, code, or results.")
    print("Type 'quit' or 'exit' to leave. Type 'clear' to reset history.")
    if DEBUG_MODE:
        print("Debug mode ON — context and retrieval info will be printed.")
    print("=" * 60)
    print()

    chat_history = []

    goodbye_messages = [
        "Thanks for using THRESHER-Chat!",
        "Happy phylogenomics!",
        "See you next time!",
        "Keep exploring THRESHER!",
        "Goodbye and good luck with your analysis!",
        "Thanks for the great questions!",
        "Until next time, happy sequencing!",
        "Catch you later!",
        "May your clusters be well-resolved!",
        "Thanks for chatting with THRESHER-Chat!",
    ]
    
    while True:
        try:
            question = input("You: ").strip()
        except (KeyboardInterrupt, EOFError):
            print(f"\n{random.choice(goodbye_messages)}")
            break

        if not question:
            continue
        if question.lower() in ("quit", "exit", "q"):
            print(f"\n{random.choice(goodbye_messages)}")
            break
        if question.lower() == "clear":
            chat_history.clear()
            print("Conversation history cleared.\n")
            continue

        try:
            # Retrieve source docs for citation
            source_docs = retriever.invoke(question)

            if DEBUG_MODE:
                print("-" * 60)
                print("[DEBUG] RETRIEVED SOURCES:")
                for i, doc in enumerate(source_docs, 1):
                    src = doc.metadata.get("source", "?")
                    dtype = doc.metadata.get("type", "?")
                    preview = doc.page_content[:100].replace("\n", " ")
                    print(f"  #{i} [{dtype}] {src}")
                    print(f"      {preview}...")
                print("-" * 60)

            # Check if top result is documentation — passthrough without LLM
            passthrough = check_doc_passthrough(source_docs)

            if passthrough:
                answer = passthrough
                if DEBUG_MODE:
                    print("[DEBUG] DOC PASSTHROUGH — skipping LLM, returning docs directly")
            else:
                # Run chain with history
                answer = chain.invoke({
                    "question": question,
                    "chat_history": chat_history,
                })

            print(f"\nAssistant: {answer}")

            # Show sources
            if not args.no_sources and source_docs:
                sources = format_sources(source_docs)
                if sources:
                    source_list = ", ".join(
                        f"{src} [{origin}]" for src, (origin, ftype) in sources.items()
                    )
                    print(f"\n  Sources: {source_list}")
            print()

            # Update history (keep last N turns)
            chat_history.append(HumanMessage(content=question))
            chat_history.append(AIMessage(content=answer))
            if len(chat_history) > MEMORY_WINDOW * 2:
                chat_history = chat_history[-(MEMORY_WINDOW * 2):]

        except Exception as e:
            print(f"\nError generating response: {e}")
            print("The model may have timed out. Try a shorter question.\n")