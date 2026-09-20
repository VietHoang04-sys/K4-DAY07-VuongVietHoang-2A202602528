"""Benchmark chunking and retrieval strategies on the local Markdown corpus.

Run from the repository root:

    python bench.py
    python bench.py --data-dir data --chunk-size 500 --baseline

To compare another strategy, change only the CHUNKER line below.
"""

from __future__ import annotations

import argparse
import ast
import os
import re
from dataclasses import dataclass
from pathlib import Path

from src.chunking import ChunkingStrategyComparator, HeadingChunker
from src.embeddings import (
    EMBEDDING_PROVIDER_ENV,
    GEMINI_EMBEDDING_MODEL,
    LOCAL_EMBEDDING_MODEL,
    OPENAI_EMBEDDING_MODEL,
    GeminiEmbedder,
    LocalEmbedder,
    OpenAIEmbedder,
    _mock_embed,
)
from src.models import Document
from src.store import EmbeddingStore


# Change only this line when comparing a different strategy.
CHUNKER = HeadingChunker(chunk_size=500)


@dataclass(frozen=True)
class BenchmarkQuery:
    question: str
    metadata_filter: dict[str, str] | None
    gold_answer: str


QUERIES = [
    BenchmarkQuery(
        "Người mua có thời hạn bao nhiêu ngày để gửi yêu cầu Trả hàng/Hoàn tiền "
        "đối với hàng thông thường và thực phẩm?",
        {"audience": "buyer"},
        "Chưa có đoạn trích tương ứng trong corpus hiện tại; cần bổ sung tài liệu "
        "chính sách có thời hạn cho hàng thông thường và thực phẩm.",
    ),
    BenchmarkQuery(
        "Các bước gửi yêu cầu Trả hàng/Hoàn tiền trực tiếp từ trang đơn hàng "
        "trên ứng dụng Shopee?",
        {"audience": "buyer"},
        "Mở Shopee, vào Tôi, chọn Chờ giao hàng hoặc Đã giao, chọn Trả hàng/Hoàn "
        "tiền, chọn tình huống/sản phẩm/lý do, điền thông tin và nhấn Gửi yêu cầu.",
    ),
    BenchmarkQuery(
        "Video mở kiện hàng của Người mua cần đáp ứng tiêu chuẩn kỹ thuật và "
        "dung lượng nào?",
        {"audience": "buyer"},
        "Video cần quay liên tục, rõ nét, đủ sáng, không cắt ghép; tối đa "
        "100 MB/video và dài không quá 1 phút.",
    ),
    BenchmarkQuery(
        "Người mua có phải trả phí vận chuyển khi gửi hàng hoàn trả về cho "
        "Người bán không?",
        {"audience": "buyer"},
        "Cần đối chiếu section chính sách phí vận chuyển trong corpus; không suy "
        "đoán khi tài liệu hiện tại chưa nêu rõ mức phí.",
    ),
    BenchmarkQuery(
        "Thời gian xử lý yêu cầu Trả hàng / Hoàn tiền là bao lâu?",
        {"audience": "buyer"},
        "Yêu cầu thường được Shopee xử lý trong khoảng 3 - 5 ngày làm việc; "
        "nếu được chấp nhận, tiền hoàn trong khoảng 1 - 14 ngày làm việc.",
    ),
]


def _parse_scalar(value: str) -> object:
    value = value.split("#", 1)[0].strip()
    if not value:
        return ""
    try:
        return ast.literal_eval(value)
    except (SyntaxError, ValueError):
        return value


def read_markdown(path: Path) -> tuple[dict[str, object], str]:
    """Read YAML-like frontmatter without requiring PyYAML."""
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---"):
        return {}, text

    end_match = re.search(r"(?m)^---[ \t]*$", text[3:])
    if not end_match:
        return {}, text

    end = end_match.start() + 3
    frontmatter: dict[str, object] = {}
    for line in text[3:end].splitlines():
        if not line.strip() or line.lstrip().startswith("#") or ":" not in line:
            continue
        key, value = line.split(":", 1)
        frontmatter[key.strip()] = _parse_scalar(value)
    return frontmatter, text[end + 3 :].lstrip()


def load_chunked_documents(data_dir: Path) -> list[Document]:
    documents: list[Document] = []
    for path in sorted(data_dir.rglob("*.md")):
        metadata, content = read_markdown(path)
        if not content.strip():
            continue
        metadata = dict(metadata)
        metadata["doc_id"] = path.stem
        metadata["source"] = str(path)
        for index, chunk in enumerate(CHUNKER.chunk(content)):
            documents.append(
                Document(
                    id=f"{path.stem}#{index}",
                    content=chunk,
                    metadata=metadata.copy(),
                )
            )
    return documents


def select_embedder():
    provider = os.getenv(EMBEDDING_PROVIDER_ENV, "mock").strip().lower()
    try:
        if provider == "local":
            return LocalEmbedder(os.getenv("LOCAL_EMBEDDING_MODEL", LOCAL_EMBEDDING_MODEL))
        if provider == "openai":
            return OpenAIEmbedder(os.getenv("OPENAI_EMBEDDING_MODEL", OPENAI_EMBEDDING_MODEL))
        if provider == "gemini":
            return GeminiEmbedder(os.getenv("GEMINI_EMBEDDING_MODEL", GEMINI_EMBEDDING_MODEL))
    except Exception as exc:
        print(f"Embedding provider '{provider}' unavailable ({exc}); using mock embeddings.")
    return _mock_embed


def print_baseline(data_dir: Path, chunk_size: int) -> None:
    print("\n=== Baseline: fixed/sentence/recursive/heading ===")
    comparator = ChunkingStrategyComparator()
    for path in sorted(data_dir.rglob("*.md")):
        _, content = read_markdown(path)
        if not content.strip():
            continue
        result = comparator.compare(content, chunk_size=chunk_size)
        print(f"\n{path.stem}:")
        for strategy, stats in result.items():
            print(
                f"  {strategy}: count={stats['count']} "
                f"avg_length={stats['avg_length']:.1f}"
            )


def run(data_dir: Path, chunk_size: int, show_baseline: bool) -> int:
    documents = load_chunked_documents(data_dir)
    if not documents:
        print(f"No Markdown documents found under {data_dir}")
        return 1

    embedder = select_embedder()
    store = EmbeddingStore("heading_benchmark", embedding_fn=embedder)
    store.add_documents(documents)
    print(f"Chunker: {CHUNKER.__class__.__name__}")
    print(f"Embedding backend: {getattr(embedder, '_backend_name', 'custom')}")
    print(f"Loaded {len(documents)} chunks from {len({d.metadata['doc_id'] for d in documents})} files")

    if show_baseline:
        print_baseline(data_dir, chunk_size)

    print("\n=== Retrieval benchmark (top-3) ===")
    for index, query in enumerate(QUERIES, start=1):
        results = store.search_with_filter(
            query.question, top_k=3, metadata_filter=query.metadata_filter
        )
        print(f"\n[{index}] {query.question}")
        print(f"filter={query.metadata_filter}")
        print(f"gold={query.gold_answer}")
        if not results:
            print("  No results")
            continue
        for rank, result in enumerate(results, start=1):
            print(
                f"  {rank}. score={result['score']:.4f} "
                f"doc_id={result['metadata'].get('doc_id')} "
                f"chunk_id={result['id']}"
            )
            preview = " ".join(result["content"].split())
            print(f"     {preview[:240]}{'...' if len(preview) > 240 else ''}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, default=Path("data"))
    parser.add_argument("--chunk-size", type=int, default=500)
    parser.add_argument("--baseline", action="store_true")
    args = parser.parse_args()
    if args.chunk_size != CHUNKER.chunk_size:
        print("Note: CHUNKER is configured with 500; --chunk-size is used for baseline only.")
    return run(args.data_dir, args.chunk_size, args.baseline)


if __name__ == "__main__":
    raise SystemExit(main())
