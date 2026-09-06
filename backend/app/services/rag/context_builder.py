from collections.abc import Sequence

from app.services.rag.retrieval_service import RetrievedChunk


def build_rag_context(results: Sequence[RetrievedChunk]) -> str:
    blocks: list[str] = []
    for index, item in enumerate(results, start=1):
        citation = f"[source_id={item.source_id} document_id={item.document_id} chunk_id={item.chunk_id}]"
        if item.source_url:
            citation += f" URL: {item.source_url}"
        blocks.append(f"SOURCE {index}: {item.title}\n{citation}\nContent:\n{item.content}")
    return "\n\n".join(blocks)
