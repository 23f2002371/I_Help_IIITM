import re
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from config import CHUNK_SIZE_WORDS, CHUNK_OVERLAP_WORDS
COURSE_HEADER_REGEX = re.compile("^\\s*\\d{1,2}\\.\\s+[A-Z][A-Za-z0-9&/,'\\-\\s]{2,80}?(\\(.*\\))?\\s*$", re.MULTILINE)

def split_by_course(text: str):
    matches = list(COURSE_HEADER_REGEX.finditer(text))
    if not matches:
        return [(None, text)]
    segments = []
    if matches[0].start() > 0:
        preamble = text[:matches[0].start()].strip()
        if preamble:
            segments.append((None, preamble))
    for i, m in enumerate(matches):
        header = m.group().strip()
        start = m.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        body = text[start:end].strip()
        segments.append((header, f'{header}\n{body}'))
    return segments

def chunk_words(text: str, chunk_size=CHUNK_SIZE_WORDS, overlap=CHUNK_OVERLAP_WORDS):
    words = text.split()
    if not words:
        return []
    chunks = []
    step = max(chunk_size - overlap, 1)
    for start in range(0, len(words), step):
        chunk = ' '.join(words[start:start + chunk_size])
        if chunk.strip():
            chunks.append(chunk)
        if start + chunk_size >= len(words):
            break
    return chunks

def process_page(text: str, source_name: str, source_type: str, source_url: str, page_number, topic: str, forced_course_name: str=None, carry_course_name: str=None):
    chunk_dicts = []
    if forced_course_name:
        segments = [(forced_course_name, text)]
    else:
        segments = split_by_course(text)
    last_course_name = carry_course_name
    for course_header, segment_text in segments:
        course_name = course_header or carry_course_name or 'Unspecified'
        if course_header:
            last_course_name = course_header
        for piece in chunk_words(segment_text):
            chunk_dicts.append({'text': piece, 'metadata': {'source_name': source_name, 'source_type': source_type, 'source_url': source_url or '', 'course_name': course_name, 'section': course_name, 'page_number': page_number if page_number is not None else -1, 'topic': topic or ''}})
    return (chunk_dicts, last_course_name)

def process_document(pages, source_name: str, source_type: str, source_url: str='', topic: str='', forced_course_name: str=None):
    all_chunks = []
    carry_course_name = None
    for page_number, text in pages:
        chunks, carry_course_name = process_page(text=text, source_name=source_name, source_type=source_type, source_url=source_url, page_number=page_number, topic=topic, forced_course_name=forced_course_name, carry_course_name=carry_course_name)
        all_chunks.extend(chunks)
    return all_chunks