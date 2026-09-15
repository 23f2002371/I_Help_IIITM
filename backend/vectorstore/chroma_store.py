import sys
import os
import uuid
import datetime
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from config import CHROMA_PATH, CHROMA_COLLECTION
import chromadb
_client = None
_collection = None

def _get_collection():
    global _client, _collection
    if _collection is None:
        _client = chromadb.PersistentClient(path=CHROMA_PATH)
        _collection = _client.get_or_create_collection(name=CHROMA_COLLECTION)
    return _collection

def add_chunks(chunks, embeddings):
    collection = _get_collection()
    ids = [str(uuid.uuid4()) for _ in chunks]
    documents = [c['text'] for c in chunks]
    now = datetime.datetime.utcnow().isoformat()
    metadatas = []
    for c in chunks:
        md = dict(c['metadata'])
        md['last_indexed'] = now
        metadatas.append(md)
    collection.add(ids=ids, documents=documents, metadatas=metadatas, embeddings=embeddings)
    return len(ids)

def delete_by_source(source_name: str):
    collection = _get_collection()
    try:
        collection.delete(where={'source_name': {'$eq': source_name}})
    except Exception:
        collection.delete(where={'source_name': source_name})

def query(query_embedding, top_k=5, course_filter=None, topic_filter=None):
    collection = _get_collection()
    filters = []
    if course_filter:
        filters.append({'course_name': {'$eq': course_filter}})
    if topic_filter:
        filters.append({'topic': {'$eq': topic_filter}})
    if len(filters) == 0:
        where = None
    elif len(filters) == 1:
        where = filters[0]
    else:
        where = {'$and': filters}
    try:
        result = collection.query(query_embeddings=[query_embedding], n_results=min(top_k, collection.count() or 1), where=where, include=['documents', 'metadatas', 'distances'])
    except Exception:
        return []
    out = []
    docs = result.get('documents', [[]])[0]
    metas = result.get('metadatas', [[]])[0]
    dists = result.get('distances', [[]])[0]
    for doc, meta, dist in zip(docs, metas, dists):
        out.append({'text': doc, 'metadata': meta or {}, 'distance': dist})
    return out

def list_sources():
    collection = _get_collection()
    if collection.count() == 0:
        return []
    all_data = collection.get(include=['metadatas'])
    metas = all_data.get('metadatas', []) or []
    sources = {}
    for md in metas:
        name = md.get('source_name', 'unknown')
        if name not in sources:
            sources[name] = {'source_name': name, 'source_type': md.get('source_type', ''), 'source_url': md.get('source_url', ''), 'topic': md.get('topic', ''), 'course_names': set(), 'last_indexed': md.get('last_indexed', ''), 'chunk_count': 0}
        sources[name]['course_names'].add(md.get('course_name', 'Unspecified'))
        sources[name]['chunk_count'] += 1
        if md.get('last_indexed', '') > sources[name]['last_indexed']:
            sources[name]['last_indexed'] = md.get('last_indexed', '')
    result = []
    for s in sources.values():
        s['course_names'] = sorted(s['course_names'])
        result.append(s)
    return sorted(result, key=lambda s: s['source_name'])

def list_course_names():
    collection = _get_collection()
    if collection.count() == 0:
        return []
    all_data = collection.get(include=['metadatas'])
    metas = all_data.get('metadatas', []) or []
    names = {md.get('course_name') for md in metas if md.get('course_name')}
    names.discard('Unspecified')
    return sorted(names)