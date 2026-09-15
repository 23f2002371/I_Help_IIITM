import sys
import os
import time
import requests as _requests
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'vectorstore'))
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'ingestion'))
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
import chroma_store
import embedder
from config import GEMINI_API_KEY, GEMINI_MODEL, GEMINI_MAX_RETRIES, GEMINI_RETRY_DELAY, GOOGLE_SEARCH_API_KEY, GOOGLE_CSE_ID, DEFAULT_TOP_K, MIN_RELEVANCE_SCORE
import google.generativeai as genai
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)
SYSTEM_PROMPT = 'You are CourseGenie 🎓, a friendly and precise academic assistant for IIT Madras BS degree students.\n\nYour personality:\n- Warm, helpful, and encouraging — like a knowledgeable senior student\n- Direct and precise — give concrete answers with exact numbers/dates\n- Never vague or wishy-washy\n\nWhen answering from documents:\n1. Use ONLY information from the provided CONTEXT\n2. Quote exact numbers, thresholds, percentages VERBATIM (e.g. "the document states ≥ 40/100")\n3. Always name the specific course your answer applies to\n4. If multiple courses have different rules — state each separately, clearly\n5. Format your answer neatly using markdown: **bold** for key numbers, bullet lists for multiple items\n6. If the context doesn\'t contain the answer → say clearly: "I don\'t have this in the indexed documents" and suggest they check with the course coordinator\n\nWhen answering from web search:\n1. Clearly state: "I found this via web search (not from your uploaded documents):"\n2. Summarize the key information concisely\n3. Always include the source URL\n\nKeep answers concise and scannable. Use bullet points for lists. Bold important numbers.'
GREETING_RESPONSE = "Hey there! 👋 I'm **CourseGenie**, your academic assistant for the **IIT Madras BS degree program**.\n\nI can help you with:\n- 📊 **Grading & marks** — passing criteria, thresholds, score breakdowns\n- 📅 **Deadlines** — submission dates, schedules\n- 📚 **Course info** — syllabi, policies, project rules\n- 🔍 **Any course question** — just ask!\n\nWhat would you like to know?"

def _call_gemini(prompt: str, system: str=SYSTEM_PROMPT) -> str | None:
    if not GEMINI_API_KEY:
        return None
    model = genai.GenerativeModel(model_name=GEMINI_MODEL, system_instruction=system)
    delay = GEMINI_RETRY_DELAY
    for attempt in range(GEMINI_MAX_RETRIES):
        try:
            response = model.generate_content(prompt, generation_config={'temperature': 0.2, 'max_output_tokens': 1024})
            text = response.text.strip() if response.text else None
            return text
        except Exception as e:
            err_str = str(e).lower()
            print('GEMINI ERROR:', err_str)
            if '429' in err_str or 'quota' in err_str or 'rate' in err_str:
                if attempt < GEMINI_MAX_RETRIES - 1:
                    time.sleep(delay)
                    delay *= 2
                    continue
            return None
    return None

def _web_search(query: str, num_results: int=3) -> list[dict]:
    if not GOOGLE_SEARCH_API_KEY or not GOOGLE_CSE_ID:
        return []
    full_query = f'IIT Madras BS degree {query}'
    try:
        resp = _requests.get('https://www.googleapis.com/customsearch/v1', params={'key': GOOGLE_SEARCH_API_KEY, 'cx': GOOGLE_CSE_ID, 'q': full_query, 'num': num_results}, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        items = data.get('items', [])
        return [{'title': item.get('title', ''), 'link': item.get('link', ''), 'snippet': item.get('snippet', '')} for item in items]
    except Exception:
        return []

def _format_rag_context(chunks: list) -> str:
    parts = []
    for i, c in enumerate(chunks, start=1):
        md = c['metadata']
        header = f'[Chunk {i}] Source: {md.get('source_name', 'unknown')}'
        if md.get('course_name') and md['course_name'] != 'Unspecified':
            header += f' | Course: {md['course_name']}'
        if md.get('page_number', -1) != -1:
            header += f' | Page {md['page_number']}'
        parts.append(f'{header}\n{c['text']}')
    return '\n\n---\n\n'.join(parts)

def _format_web_context(results: list) -> str:
    parts = []
    for r in results:
        parts.append(f'**{r['title']}**\nURL: {r['link']}\n{r['snippet']}')
    return '\n\n'.join(parts)

def answer_question(question: str, course_filter: str=None, top_k: int=DEFAULT_TOP_K):
    query_embedding = embedder.embed_query(question)
    raw_results = chroma_store.query(query_embedding, top_k=top_k, course_filter=course_filter)
    if not raw_results and course_filter:
        raw_results = chroma_store.query(query_embedding, top_k=top_k, course_filter=None)
    relevant = []
    for r in raw_results:
        relevance = max(0.0, 1 - r['distance'] / 2)
        r['relevance'] = relevance
        if relevance >= MIN_RELEVANCE_SCORE:
            relevant.append(r)
    if relevant:
        context_text = _format_rag_context(relevant)
        prompt = f'CONTEXT FROM OFFICIAL DOCUMENTS:\n\n{context_text}\n\n---\n\nSTUDENT QUESTION: {question}\n\nPlease answer based on the context above. Be specific and cite exact numbers.'
        answer = _call_gemini(prompt)
        if not answer:
            top = relevant[0]
            md = top['metadata']
            course = md.get('course_name', 'the relevant course')
            answer = f'> ⚠️ AI model temporarily unavailable — showing the most relevant excerpt directly:\n\n**For {course}:**\n\n{top['text']}'
        citations = [{'source_name': r['metadata'].get('source_name'), 'course_name': r['metadata'].get('course_name'), 'page_number': r['metadata'].get('page_number'), 'source_url': r['metadata'].get('source_url'), 'relevance': round(r['relevance'], 3), 'excerpt': r['text'][:300]} for r in relevant]
        return {'answer': answer, 'citations': citations, 'used_fallback': False, 'source_type': 'documents'}
    web_results = _web_search(question)
    if web_results:
        context_text = _format_web_context(web_results)
        prompt = f'WEB SEARCH RESULTS for: "{question}"\n\n{context_text}\n\n---\n\nBased on these web search results, provide a concise helpful answer for an IIT Madras BS degree student. Clearly note this is from web search, not from uploaded course documents, and include the most relevant URL.'
        answer = _call_gemini(prompt)
        if not answer:
            snippets = '\n\n'.join((f'**{r['title']}**\n{r['snippet']}\n🔗 {r['link']}' for r in web_results))
            answer = f'*Found via web search (AI unavailable):*\n\n{snippets}'
        web_citations = [{'source_name': r['title'], 'course_name': None, 'page_number': None, 'source_url': r['link'], 'relevance': 1.0, 'excerpt': r['snippet']} for r in web_results]
        return {'answer': answer, 'citations': web_citations, 'used_fallback': True, 'source_type': 'web'}
    general_prompt = f'The indexed course documents and web search did not provide a useful answer to this question: {question}\n\nAnswer using your general knowledge. Be concise and helpful. Do not present your answer as an official IITM course policy, deadline, grading rule, or fact from the uploaded documents. If the question needs current or official information, tell the student to verify it from an official source.'
    general_answer = _call_gemini(general_prompt)
    if general_answer:
        return {'answer': general_answer, 'citations': [], 'used_fallback': True, 'source_type': 'external_llm'}
    return {'answer': 'I couldn\'t find this information in the indexed documents, and my web search didn\'t return useful results either.\n\n**Suggestions:**\n- Try rephrasing your question with the course name (e.g. *"BDM passing criteria"*)\n- Ask your course coordinator or check the IITM Student Portal\n- Ask an admin to upload the relevant document', 'citations': [], 'used_fallback': False, 'source_type': 'none'}