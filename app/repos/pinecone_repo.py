from pinecone import Pinecone
import os
from dotenv import load_dotenv
from typing import List, Dict, Optional

load_dotenv()


class PineconeRepo:
    """
    Pinecone repository
    - Stores embeddings + metadata
    - Namespace is STRICTLY userId
    - NO conversation-level tracking
    """

    def __init__(self):
        api_key = os.environ.get("PINECONE_API_KEY")
        host = os.environ.get("PINECONE_HOST")

        if not api_key or not host:
            raise RuntimeError("PINECONE_API_KEY or PINECONE_HOST not set")

        self.pc = Pinecone(api_key=api_key)
        self.index = self.pc.Index(host=host)

    # --------------------------------------------------
    # Upsert (USER namespace only)
    # --------------------------------------------------
    def upsert(
        self,
        *,
        userId: str,
        vectors: List[Dict],
        batch_size: int = 100,
    ):
        """
        Upserts vectors into a USER-scoped namespace.
        Namespace = userId ONLY.
        """

        if not vectors:
            return

        for i in range(0, len(vectors), batch_size):
            batch = vectors[i:i + batch_size]
            self.index.upsert(
                vectors=batch,
                namespace=userId,
            )

    # --------------------------------------------------
    # Query (USER namespace only)
    # --------------------------------------------------
    def query(
        self,
        *,
        userId: str,
        vector: List[float],
        top_k: int = 6,
        metadata_filter: Optional[Dict] = None,
    ):
        """
        Queries vectors within USER namespace.
        """

        return self.index.query(
            vector=vector,
            top_k=top_k,
            namespace=userId,
            filter=metadata_filter,
            include_metadata=True,
        )

    # --------------------------------------------------
    # Delete ALL data for a user
    # --------------------------------------------------
    def delete_user(self, *, userId: str):
        """
        Deletes all vectors for a user.
        """

        self.index.delete(
            delete_all=True,
            namespace=userId,
        )

    # --------------------------------------------------
    # Health check
    # --------------------------------------------------
    def health(self) -> bool:
        try:
            self.index.describe_index_stats()
            return True
        except Exception:
            return False
