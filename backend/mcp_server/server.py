import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'vectorstore'))
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'ingestion'))
import chroma_store
import embedder
from mcp.server.fastmcp import FastMCP
mcp = FastMCP('coursegenie-retrieval')

@mcp.tool()
def search_documents(query: str, top_k: int=5, course_filter: str=None) -> list:
    query_embedding = embedder.embed_query(query)
    results = chroma_store.query(query_embedding, top_k=top_k, course_filter=course_filter)
    return [{'text': r['text'], 'source_name': r['metadata'].get('source_name'), 'course_name': r['metadata'].get('course_name'), 'page_number': r['metadata'].get('page_number'), 'source_url': r['metadata'].get('source_url')} for r in results]

@mcp.tool()
def get_document_by_topic(topic: str, top_k: int=5) -> list:
    query_embedding = embedder.embed_query(topic)
    results = chroma_store.query(query_embedding, top_k=top_k)
    filtered = [r for r in results if r['metadata'].get('topic') == topic]
    return [{'text': r['text'], 'source_name': r['metadata'].get('source_name'), 'course_name': r['metadata'].get('course_name')} for r in filtered]

@mcp.tool()
def list_available_sources() -> list:
    return chroma_store.list_sources()
if __name__ == '__main__':
    mcp.run()