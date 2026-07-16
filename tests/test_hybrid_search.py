from pathlib import Path

from app.config import ChunkingSettings, EmbeddingSettings, ProjectSettings, RetrievalLimits, RetrievalSettings, Settings
from app.llm.embeddings import EmbeddingBatch
from app.retrieval.hybrid_search import hybrid_search
from app.retrieval.semantic_search import semantic_search
from app.storage.embedding_index import build_embeddings
from app.storage.indexer import build_index


class KeywordVectorProvider:
    def embed(self, texts: list[str]) -> EmbeddingBatch:
        vectors = []
        for text in texts:
            vectors.append([1.0, 0.0] if "자존감" in text or "평가" in text else [0.0, 1.0])
        return EmbeddingBatch(vectors, len(texts))


def test_semantic_and_hybrid_search_expose_scores_and_diversity(tmp_path: Path) -> None:
    library = tmp_path / "library"
    library.mkdir()
    (library / "심리.md").write_text("# 자존감\n타인의 시선을 의식한다.\n\n## 비교\n평가가 불안을 만든다.", encoding="utf-8")
    (library / "기술.md").write_text("# 기술\n인공지능과 제품 설계", encoding="utf-8")
    settings = Settings(
        project=ProjectSettings(library_path=library, database_path=tmp_path / "db.sqlite"),
        chunking=ChunkingSettings(min_chars=1, target_chars=30, max_chars=80, overlap_chars=0),
        embedding=EmbeddingSettings(model="fake", dimensions=2, batch_size=10, max_retries=0),
    )
    provider = KeywordVectorProvider()
    build_index(settings)
    build_embeddings(settings, provider)
    semantic = semantic_search(settings, "타인의 평가", 2, provider)
    assert semantic[0].source_file == Path("심리.md")
    retrieval = RetrievalSettings(limits=RetrievalLimits(candidate_pool=10, max_chunks_per_book=1))
    hybrid = hybrid_search(settings, "타인의 평가", 10, retrieval=retrieval, provider=provider)
    assert hybrid[0].semantic_score > 0
    assert hybrid[0].diversity_score == 1.0
    assert len({result.book_id for result in hybrid}) == len(hybrid)
