import os
from dotenv import load_dotenv
from pinecone import Pinecone
from pinecone.exceptions import PineconeApiException

load_dotenv()

PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")
INDEX_NAME = os.getenv("PINECONE_INDEX_NAME")

if not PINECONE_API_KEY or not INDEX_NAME:
    raise SystemExit("Missing PINECONE_API_KEY or PINECONE_INDEX_NAME in .env")

pc = Pinecone(api_key=PINECONE_API_KEY)
index = pc.Index(INDEX_NAME)

# ----------------------------
# 1) Print namespaces
# ----------------------------
stats = index.describe_index_stats()
namespaces = stats.get("namespaces", {}) or {}

if not namespaces:
    print("No namespaces found (index may be empty).")
    raise SystemExit(0)

print("\n=== Available Namespaces ===")
for ns, meta in namespaces.items():
    print(f"- {ns!r} (vector_count={meta.get('vector_count')})")

# ----------------------------
# 2) Ask user for namespace + print top 5 IDs
# ----------------------------
def top_vector_ids(namespace: str, top_n: int = 5):
    # Pinecone list_paginated limit must be < 100
    limit = min(max(top_n, 1), 99)

    resp = index.list_paginated(namespace=namespace, limit=limit)

    vectors = getattr(resp, "vectors", None) or (resp.get("vectors", []) if isinstance(resp, dict) else [])
    ids = []

    for v in vectors:
        if isinstance(v, dict) and "id" in v:
            ids.append(v["id"])
        else:
            vid = getattr(v, "id", None)
            if vid:
                ids.append(vid)

    return ids[:top_n]

ns_input = input("\nEnter namespace to print top 5 vector IDs: ").strip()
if not ns_input:
    raise SystemExit("No namespace entered. Exiting.")

try:
    ids = top_vector_ids(ns_input, top_n=5)

    print(f"\n=== Top 5 Vector IDs in Namespace {ns_input!r} ===")
    if not ids:
        print("No vectors found in this namespace (or namespace doesn't exist).")
    else:
        for i, vid in enumerate(ids, start=1):
            print(f"{i}. {vid}")

except PineconeApiException as e:
    print(f"[ERROR] Pinecone API error: {e}")
except Exception as e:
    print(f"[ERROR] Failed: {e}")
