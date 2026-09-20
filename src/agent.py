from typing import Callable

from .store import EmbeddingStore


class KnowledgeBaseAgent:
    """
    An agent that answers questions using a vector knowledge base.

    Retrieval-augmented generation (RAG) pattern:
        1. Retrieve top-k relevant chunks from the store.
        2. Build a prompt with the chunks as context.
        3. Call the LLM to generate an answer.
    """

    def __init__(self, store: EmbeddingStore, llm_fn: Callable[[str], str]) -> None:
        self.store = store
        self.llm_fn = llm_fn

    def answer(self, question: str, top_k: int = 3) -> str:
        results = self.store.search(question, top_k=top_k)
        if not results:
            return "No relevant information was found in the knowledge base."

        context = []
        for index, result in enumerate(results, start=1):
            metadata = result.get("metadata", {})
            source = metadata.get("source") or metadata.get("doc_id") or result.get("id", "unknown")
            context.append(f"[{index}] Source: {source}\n{result.get('content', '')}")

        context_text = "\n\n".join(context)
        prompt = (
            "Answer the question using only the context below. "
            "If the answer is not in the context, say it was not found. "
            "Cite relevant context numbers such as [1] or [2].\n\n"
            f"Context:\n\n{context_text}\n\n"
            f"Question: {question}\nAnswer:"
        )
        return self.llm_fn(prompt)
