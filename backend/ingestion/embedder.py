import sys
import os
import google.generativeai as genai
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from config import GEMINI_API_KEY, GEMINI_EMBEDDING_MODEL

if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)

def embed_texts(texts):
    if not GEMINI_API_KEY:
        raise RuntimeError('GEMINI_API_KEY is required for document embeddings.')
    result = genai.embed_content(
        model=GEMINI_EMBEDDING_MODEL,
        content=texts,
        task_type='retrieval_document',
    )
    return result['embedding']

def embed_query(text: str):
    if not GEMINI_API_KEY:
        raise RuntimeError('GEMINI_API_KEY is required for query embeddings.')
    result = genai.embed_content(
        model=GEMINI_EMBEDDING_MODEL,
        content=text,
        task_type='retrieval_query',
    )
    return result['embedding']