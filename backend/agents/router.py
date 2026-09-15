import difflib
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'vectorstore'))
import chroma_store
GREETING_WORDS = {'hi', 'hello', 'hey', 'hiya', 'howdy', 'sup', 'yo', 'greetings', 'good morning', 'good afternoon', 'good evening', 'good night', "what's up", 'whats up', 'how are you', 'how r u'}
INTENT_KEYWORDS = {'grading': ['pass', 'passing', 'grade', 'grading', 'score', 'marks', 'mark', 'criteria', 'eligib', 'eligibility', 'cutoff', 'threshold', 'minimum', 'fail', 'failing', 'percentage', 'gpa', 'cgpa', 'assignment', 'quiz', 'exam', 'final', 'internal', 'external'], 'deadlines': ['deadline', 'due date', 'submission date', 'when is', 'last date', 'release date', 'schedule', 'date for', 'by when', 'how long', 'time limit'], 'project_submission': ['project', 'submit', 'submission format', 'report format', 'viva', 'presentation', 'format', 'how to submit'], 'course_info': ['course', 'subject', 'syllabus', 'curriculum', 'content', 'module', 'unit', 'chapter', 'topic', 'about', 'what is', 'who teaches', 'instructor', 'professor']}

def classify_intent(question: str) -> str:
    q = question.lower().strip()
    if q in GREETING_WORDS:
        return 'greeting'
    for gw in GREETING_WORDS:
        if q.startswith(gw) and len(q) <= len(gw) + 10:
            return 'greeting'
    best_intent = 'general'
    best_score = 0
    for intent, keywords in INTENT_KEYWORDS.items():
        score = sum((1 for kw in keywords if kw in q))
        if score > best_score:
            best_score = score
            best_intent = intent
    return best_intent

def detect_course(question: str):
    known_courses = chroma_store.list_course_names()
    if not known_courses:
        return None
    q = question.lower()
    for course in known_courses:
        clean = course.split('.', 1)[-1].split('(')[0].strip().lower()
        if clean and clean in q:
            return course
    cleaned_map = {c.split('.', 1)[-1].split('(')[0].strip().lower(): c for c in known_courses}
    matches = difflib.get_close_matches(q, cleaned_map.keys(), n=1, cutoff=0.4)
    if matches:
        return cleaned_map[matches[0]]
    return None