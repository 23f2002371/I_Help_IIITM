import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'vectorstore'))
import pdf_parser
import web_scraper
import chunker
import embedder
import chroma_store
import registry
from config import UPLOAD_DIR

def _store_chunks(chunks):
    if not chunks:
        return 0
    texts = [c['text'] for c in chunks]
    embeddings = embedder.embed_texts(texts)
    return chroma_store.add_chunks(chunks, embeddings)

def ingest_pdf(file_path: str, source_name: str, topic: str='', forced_course_name: str=None):
    chroma_store.delete_by_source(source_name)
    pages = pdf_parser.extract_pages(file_path)
    chunks = chunker.process_document(pages=pages, source_name=source_name, source_type='pdf', source_url='', topic=topic, forced_course_name=forced_course_name)
    count = _store_chunks(chunks)
    registry.upsert(source_name, {'kind': 'pdf_upload', 'file_path': file_path, 'topic': topic, 'forced_course_name': forced_course_name})
    return {'source_name': source_name, 'chunks_indexed': count}

def ingest_link(url: str, source_name: str, source_type: str, topic: str='', forced_course_name: str=None):
    chroma_store.delete_by_source(source_name)
    if source_type == 'pdf':
        import requests
        import tempfile
        resp = requests.get(url, timeout=30)
        resp.raise_for_status()
        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp:
            tmp.write(resp.content)
            tmp_path = tmp.name
        try:
            pages = pdf_parser.extract_pages(tmp_path)
        finally:
            os.remove(tmp_path)
    else:
        text = web_scraper.fetch_and_clean(url)
        pages = [(None, text)]
    chunks = chunker.process_document(pages=pages, source_name=source_name, source_type=source_type, source_url=url, topic=topic, forced_course_name=forced_course_name)
    count = _store_chunks(chunks)
    registry.upsert(source_name, {'kind': 'link', 'url': url, 'source_type': source_type, 'topic': topic, 'forced_course_name': forced_course_name})
    return {'source_name': source_name, 'chunks_indexed': count}

def reindex_source(source_name: str):
    config = registry.get(source_name)
    if not config:
        raise ValueError(f"No stored config for source '{source_name}' — cannot re-index. Delete and re-add it instead.")
    if config['kind'] == 'pdf_upload':
        return ingest_pdf(file_path=config['file_path'], source_name=source_name, topic=config.get('topic', ''), forced_course_name=config.get('forced_course_name'))
    else:
        return ingest_link(url=config['url'], source_name=source_name, source_type=config['source_type'], topic=config.get('topic', ''), forced_course_name=config.get('forced_course_name'))

def delete_source(source_name: str):
    chroma_store.delete_by_source(source_name)
    config = registry.get(source_name)
    if config and config.get('kind') == 'pdf_upload':
        file_path = config.get('file_path')
        if file_path and os.path.exists(file_path):
            os.remove(file_path)
    registry.remove(source_name)
    return {'source_name': source_name, 'deleted': True}