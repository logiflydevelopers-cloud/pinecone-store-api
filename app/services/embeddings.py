# app/repos/embeddings.py

from langchain_openai import OpenAIEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter
from app.repos.pinecone_repo import PineconeRepo
from typing import List, Optional
import uuid


# -------------------------
# Embedding model
# -------------------------
emb = OpenAIEmbeddings(model="text-embedding-3-small")


def build_embeddings(
    *,
    userId: str,
    convId: str,
    texts: List[str],
    sourceType: str,
    pages: Optional[List[int]] = None,   # PDF only
    url: Optional[str] = None,            # WEB only
    chunkId: Optional[str] = None,        # Optional prefix (WEB per-page)
):
    """
    Build and upsert embeddings for:
    - PDF
    - Website

    Storage model (NEW):
    - Pinecone ONLY
    - Vector + FULL TEXT + metadata stored together
    """

    # -------------------------
    # Text chunking
    # -------------------------
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=1600,
        chunk_overlap=200,
        separators=["\n\n", "\n", " ", ""],
    )

    full_text = "\n".join(texts)
    chunks = splitter.split_text(full_text)

    if not chunks:
        return

    embeddings = emb.embed_documents(chunks)

    pinecone = PineconeRepo()

    # Namespace = user isolation + conversation isolation
    namespace = f"{userId}:{convId}"

    vectors = []

    # -------------------------
    # Build vectors
    # -------------------------
    for i, (chunk, vector) in enumerate(zip(chunks, embeddings)):

        # Deterministic chunkId when provided (WEB per-page)
        chunk_id = (
            f"{chunkId}_{i}" if chunkId
            else f"chunk_{uuid.uuid4().hex}"
        )

        # -------------------------
        # Metadata (TEXT INCLUDED)
        # -------------------------
        metadata = {
            "userId": userId,
            "convId": convId,
            "chunkId": chunk_id,
            "sourceType": sourceType,
            "text": chunk,   # TEXT STORED IN PINECONE
        }

        if sourceType == "pdf" and pages and i < len(pages):
            metadata["page"] = pages[i]

        if sourceType == "web" and url:
            metadata["url"] = url

        vectors.append({
            "id": chunk_id,
            "values": vector,
            "metadata": metadata,
        })

    # -------------------------
    # Upsert to Pinecone
    # -------------------------
    pinecone.upsert(
        vectors=vectors,
        namespace=namespace,
    )
