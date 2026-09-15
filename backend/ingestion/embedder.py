import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from config import EMBEDDING_MODEL
_model = None

def _get_model():
    global _model
    if _model is None:
        from sentence_transformers import SentenceTransformer
        _model = SentenceTransformer(EMBEDDING_MODEL)
    return _model

def embed_texts(texts):
    model = _get_model()
    embeddings = model.encode(texts, show_progress_bar=False, normalize_embeddings=True)
    return embeddings.tolist()

def embed_query(text: str):
    return embed_texts([text])[0]