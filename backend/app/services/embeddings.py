from functools import lru_cache

from sentence_transformers import SentenceTransformer

from app.config import get_settings


@lru_cache(maxsize=1)
def get_embedding_model() -> SentenceTransformer:
    return SentenceTransformer(get_settings().embedding_model)


def embed_descriptions(descriptions: list[str]) -> list[list[float]]:
    vectors = get_embedding_model().encode(
        descriptions,
        normalize_embeddings=True,
        show_progress_bar=False,
    )
    return [vector.tolist() for vector in vectors]

