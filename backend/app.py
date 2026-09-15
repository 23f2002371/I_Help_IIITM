import os
import sys
sys.stdout.reconfigure(encoding='utf-8')
import uuid
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
sys.path.append(os.path.join(os.path.dirname(__file__), 'agents'))
sys.path.append(os.path.join(os.path.dirname(__file__), 'ingestion'))
sys.path.append(os.path.join(os.path.dirname(__file__), 'vectorstore'))
import orchestrator
import service as ingestion_service
import chroma_store
from config import ADMIN_PASSWORD, UPLOAD_DIR
FRONTEND_DIR = os.path.join(os.path.dirname(__file__), '..', 'frontend')
app = Flask(__name__, static_folder=FRONTEND_DIR, static_url_path='')
CORS(app)

@app.route('/')
def serve_index():
    return send_from_directory(FRONTEND_DIR, 'index.html')

@app.route('/admin')
def serve_admin():
    return send_from_directory(FRONTEND_DIR, 'admin.html')

@app.route('/<path:path>')
def serve_static(path):
    return send_from_directory(FRONTEND_DIR, path)

@app.route('/api/health')
def health():
    from config import GEMINI_API_KEY, GOOGLE_SEARCH_API_KEY
    return jsonify({'status': 'ok', 'gemini_configured': bool(GEMINI_API_KEY), 'web_search_configured': bool(GOOGLE_SEARCH_API_KEY), 'sources_count': len(chroma_store.list_sources())})

def _check_admin_auth():
    password = request.headers.get('X-Admin-Password', '')
    return password == ADMIN_PASSWORD

def _require_admin():
    if not _check_admin_auth():
        return (jsonify({'error': 'Unauthorized. Invalid admin password.'}), 401)
    return None

@app.route('/api/chat', methods=['POST'])
def chat():
    data = request.get_json(force=True)
    question = (data.get('question') or '').strip()
    top_k = int(data.get('top_k', 4))
    if not question:
        return (jsonify({'error': 'question is required'}), 400)
    try:
        result = orchestrator.handle_question(question, top_k=top_k)
        return jsonify(result)
    except Exception as e:
        return (jsonify({'error': f'Internal error: {e}'}), 500)

@app.route('/api/admin/login', methods=['POST'])
def admin_login():
    data = request.get_json(force=True)
    password = data.get('password', '')
    if password == ADMIN_PASSWORD:
        return jsonify({'ok': True})
    return (jsonify({'ok': False, 'error': 'Incorrect password'}), 401)

@app.route('/api/admin/sources', methods=['GET'])
def list_sources():
    unauthorized = _require_admin()
    if unauthorized:
        return unauthorized
    return jsonify(chroma_store.list_sources())

@app.route('/api/admin/upload-pdf', methods=['POST'])
def upload_pdf():
    unauthorized = _require_admin()
    if unauthorized:
        return unauthorized
    if 'file' not in request.files:
        return (jsonify({'error': 'No file uploaded'}), 400)
    file = request.files['file']
    source_name = request.form.get('source_name') or file.filename
    topic = request.form.get('topic', '')
    forced_course_name = request.form.get('forced_course_name') or None
    safe_filename = f'{uuid.uuid4().hex}_{file.filename}'
    save_path = os.path.join(UPLOAD_DIR, safe_filename)
    file.save(save_path)
    try:
        result = ingestion_service.ingest_pdf(file_path=save_path, source_name=source_name, topic=topic, forced_course_name=forced_course_name)
        return jsonify(result)
    except Exception as e:
        return (jsonify({'error': str(e)}), 500)

@app.route('/api/admin/add-link', methods=['POST'])
def add_link():
    unauthorized = _require_admin()
    if unauthorized:
        return unauthorized
    data = request.get_json(force=True)
    url = data.get('url', '').strip()
    source_type = data.get('source_type', 'webpage')
    source_name = data.get('source_name') or url
    topic = data.get('topic', '')
    forced_course_name = data.get('forced_course_name') or None
    if not url:
        return (jsonify({'error': 'url is required'}), 400)
    try:
        result = ingestion_service.ingest_link(url=url, source_name=source_name, source_type=source_type, topic=topic, forced_course_name=forced_course_name)
        return jsonify(result)
    except Exception as e:
        return (jsonify({'error': str(e)}), 500)

@app.route('/api/admin/reindex/<path:source_name>', methods=['POST'])
def reindex(source_name):
    unauthorized = _require_admin()
    if unauthorized:
        return unauthorized
    try:
        result = ingestion_service.reindex_source(source_name)
        return jsonify(result)
    except Exception as e:
        return (jsonify({'error': str(e)}), 500)

@app.route('/api/admin/sources/<path:source_name>', methods=['DELETE'])
def delete_source(source_name):
    unauthorized = _require_admin()
    if unauthorized:
        return unauthorized
    try:
        result = ingestion_service.delete_source(source_name)
        return jsonify(result)
    except Exception as e:
        return (jsonify({'error': str(e)}), 500)
if __name__ == '__main__':
    print('\n🎓 CourseGenie starting...')
    print('   Chat: http://localhost:5000')
    print('   Admin: http://localhost:5000/admin\n')
    app.run(debug=False, port=5000)