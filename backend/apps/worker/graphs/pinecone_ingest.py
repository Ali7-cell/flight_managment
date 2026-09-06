import hashlib
from typing import TypedDict, Any
from langgraph.graph import StateGraph, START, END
from flight_domain.db import SessionLocal
from flight_domain.domain.policy import (
    policy_docs_changed_since_last_ingest,
    record_chunk_ingestion,
)
from flight_domain.clients.pinecone import pinecone_client

try:
    from apps.worker.checkpointer import checkpointer
except ImportError:
    from checkpointer import checkpointer  # type: ignore

class PineconeIngestState(TypedDict):
    docs: list[dict[str, Any]]
    chunks_ingested: int

def find_changed_docs(state: PineconeIngestState) -> dict:
    with SessionLocal() as session:
        docs = policy_docs_changed_since_last_ingest(session)
    return {"docs": docs, "chunks_ingested": 0}

def chunk_text(text: str, chunk_size: int = 300, overlap: int = 50) -> list[str]:
    words = text.split()
    chunks = []
    i = 0
    while i < len(words):
        chunk = " ".join(words[i : i + chunk_size])
        chunks.append(chunk)
        i += max(1, chunk_size - overlap)
    return chunks or [text]

def chunk_and_embed(state: PineconeIngestState) -> dict:
    total_chunks = 0
    with SessionLocal() as session:
        for doc in state.get("docs", []):
            chunks = chunk_text(doc.get("policy_text", ""))
            vectors = []
            chunk_records = []
            for idx, c in enumerate(chunks):
                vid = f"{doc['id']}-{idx}"
                # 1536-dimensional mock embedding vector
                vec = [0.01] * 1536
                vectors.append((
                    vid,
                    vec,
                    {
                        "text": c,
                        "fare_type": doc.get("fare_type_scope", "all"),
                        "category": doc.get("category", "general"),
                    },
                ))
                chunk_records.append({
                    "chunk_index": idx,
                    "content": c,
                    "pinecone_vector_id": vid,
                })
                total_chunks += 1

            pinecone_client.upsert_vectors(vectors=vectors, namespace="policy-docs")
            record_chunk_ingestion(session, policy_doc_id=doc["id"], chunks=chunk_records)
        session.commit()

    return {"chunks_ingested": total_chunks}

builder = StateGraph(PineconeIngestState)
builder.add_node("find_changed_docs", find_changed_docs)
builder.add_node("chunk_and_embed", chunk_and_embed)
builder.add_edge(START, "find_changed_docs")
builder.add_edge("find_changed_docs", "chunk_and_embed")
builder.add_edge("chunk_and_embed", END)

pinecone_ingest_graph = builder.compile(checkpointer=checkpointer)
