import router
import specialist

def handle_question(question: str, top_k: int=4):
    intent = router.classify_intent(question)
    if intent == 'greeting':
        return {'answer': specialist.GREETING_RESPONSE, 'citations': [], 'used_fallback': False, 'source_type': 'greeting', 'intent': intent, 'detected_course': None}
    course = router.detect_course(question)
    result = specialist.answer_question(question, course_filter=course, top_k=top_k)
    result['intent'] = intent
    result['detected_course'] = course
    return result