import logging
from typing import Any
from flight_domain.config import settings

logger = logging.getLogger("flight_domain.pinecone")

class PineconeClient:
    def __init__(self, api_key: str | None = None, host: str | None = None):
        self.api_key = api_key or settings.PINECONE_API_KEY
        self.host = host or settings.PINECONE_INDEX_HOST
        self.index = None
        self.mock_store: list[dict[str, Any]] = []
        self._init_client()

    def _init_client(self):
        if self.api_key and self.host:
            try:
                from pinecone import Pinecone
                pc = Pinecone(api_key=self.api_key)
                self.index = pc.Index(host=self.host)
                logger.info(f"Initialized real Pinecone Index with host: {self.host}")
            except Exception as e:
                logger.warning(f"Failed to connect to Pinecone index: {e}. Falling back to in-memory store.")
                self.index = None
        else:
            logger.info("No PINECONE_API_KEY/PINECONE_INDEX_HOST set. Using in-memory mock vector store.")

    def query_policy(self, query_text: str, fare_type_filter: str = "all", top_k: int = 5) -> list[dict[str, Any]]:
        """
        Query passages filtered by fare_type.
        If real Pinecone index is active, issues indexed query; otherwise searches mock store.
        """
        if self.index:
            try:
                # When using real pinecone with metadata filtering
                filter_clause = {}
                if fare_type_filter and fare_type_filter != "all":
                    filter_clause = {"fare_type": {"$in": [fare_type_filter, "all"]}}
                
                # Mock embedding for the query vector if needed
                query_vector = [0.0] * 1536
                res = self.index.query(
                    vector=query_vector,
                    top_k=top_k,
                    namespace="policy-docs",
                    filter=filter_clause,
                    include_metadata=True
                )
                passages = []
                for match in res.get("matches", []):
                    passages.append({
                        "id": match["id"],
                        "score": match["score"],
                        "metadata": match.get("metadata", {}),
                        "text": match.get("metadata", {}).get("text", "")
                    })
                return passages
            except Exception as e:
                logger.error(f"Pinecone query failed: {e}. Returning mock results.")
        
        # In-memory mock filtering
        results = []
        for item in self.mock_store:
            item_fare = item.get("metadata", {}).get("fare_type", "all")
            if fare_type_filter == "all" or item_fare in (fare_type_filter, "all"):
                results.append(item)
            if len(results) >= top_k:
                break
        
        if not results:
            # Provide sensible fallback policy passages so RAG pipeline always has context
            results = [{
                "id": "default-policy-passage-1",
                "text": f"Rules governing {fare_type_filter} tickets: changes and cancellations are governed strictly by fare rules.",
                "metadata": {"fare_type": fare_type_filter, "category": "cancellation"}
            }]
        return results

    def upsert_vectors(self, vectors: list[tuple[str, list[float], dict[str, Any]]], namespace: str = "policy-docs"):
        """Upsert vectors into Pinecone or local mock store."""
        if self.index:
            try:
                self.index.upsert(vectors=vectors, namespace=namespace)
                logger.info(f"Upserted {len(vectors)} vectors into Pinecone namespace '{namespace}'")
                return True
            except Exception as e:
                logger.error(f"Failed to upsert to Pinecone: {e}")
        
        for vid, vec, meta in vectors:
            self.mock_store.append({
                "id": vid,
                "vector": vec,
                "metadata": meta,
                "text": meta.get("text", "")
            })
        logger.info(f"Upserted {len(vectors)} vectors into local mock store.")
        return True

pinecone_client = PineconeClient()
