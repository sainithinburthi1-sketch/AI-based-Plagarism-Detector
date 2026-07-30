import os
import re
import html
import json
import time
import uuid
from flask import Flask, render_template, request, jsonify, make_response
from document_parser import extract_text_from_file
from plagiarism_engine import compare_documents
from web_searcher import search_online_sources
from repository_manager import (
    init_repository,
    add_document_to_repo,
    get_all_repository_documents,
    get_metadata as get_repo_metadata,
    delete_document_from_repo,
    get_repository_stats
)

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16 MB max upload size

# In-memory / JSON file scan history
HISTORY_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data', 'history.json')

def init_history():
    os.makedirs(os.path.dirname(HISTORY_FILE), exist_ok=True)
    if not os.path.exists(HISTORY_FILE):
        with open(HISTORY_FILE, 'w', encoding='utf-8') as f:
            json.dump([], f, indent=2)

def load_history():
    init_history()
    try:
        with open(HISTORY_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return []

def save_history_entry(entry):
    init_history()
    history = load_history()
    history.insert(0, entry) # latest first
    # keep last 50 entries
    history = history[:50]
    with open(HISTORY_FILE, 'w', encoding='utf-8') as f:
        json.dump(history, f, indent=2)

def populate_default_repository():
    """Populates repository with sample documents if empty."""
    meta = get_repo_metadata()
    if not meta:
        sample_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'sample_documents')
        if os.path.exists(sample_dir):
            for fname in os.listdir(sample_dir):
                fpath = os.path.join(sample_dir, fname)
                if os.path.isfile(fpath) and fname.endswith(('.txt', '.docx', '.pdf')):
                    try:
                        add_document_to_repo(fpath, fname)
                        print(f"[AppInit] Added sample document to repo: {fname}")
                    except Exception as e:
                        print(f"[AppInit] Error adding sample document {fname}: {e}")

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/check', methods=['POST'])
def check_plagiarism():
    try:
        query_text = ""
        filename = "Pasted Text"
        
        # Check if request has file upload
        if 'file' in request.files and request.files['file'].filename != '':
            file = request.files['file']
            filename = file.filename
            query_text = extract_text_from_file(file, filename=filename)
        else:
            # Json or form text input
            if request.is_json:
                data = request.get_json() or {}
                query_text = data.get('text', '')
                filename = data.get('filename', 'Pasted Text')
            else:
                query_text = request.form.get('text', '')
                filename = request.form.get('filename', 'Pasted Text')

        query_text = query_text.strip()
        if not query_text:
            return jsonify({'error': 'No text or valid file provided for analysis.'}), 400

        # Parse parameters
        try:
            if request.is_json:
                data = request.get_json() or {}
                check_local = bool(data.get('check_local', True))
                check_web = bool(data.get('check_web', True))
                exact_thresh = float(data.get('exact_threshold', 88)) / 100.0
                paraphrase_thresh = float(data.get('paraphrase_threshold', 68)) / 100.0
            else:
                check_local = request.form.get('check_local', 'true').lower() == 'true'
                check_web = request.form.get('check_web', 'true').lower() == 'true'
                exact_thresh = float(request.form.get('exact_threshold', 88)) / 100.0
                paraphrase_thresh = float(request.form.get('paraphrase_threshold', 68)) / 100.0
        except (ValueError, TypeError):
            exact_thresh = 0.88
            paraphrase_thresh = 0.68

        reference_docs = []

        # 1. Local Repository Documents
        if check_local:
            local_docs = get_all_repository_documents()
            reference_docs.extend(local_docs)

        # 2. Online Web Search Documents
        if check_web:
            try:
                web_docs = search_online_sources(query_text, max_queries=4, max_pages=6)
                reference_docs.extend(web_docs)
            except Exception as e:
                print(f"[API Check] Web search warning: {e}")

        # 3. Perform AI Plagiarism Comparison
        start_time = time.time()
        results = compare_documents(
            query_text=query_text,
            reference_docs=reference_docs,
            exact_threshold=exact_thresh,
            paraphrase_threshold=paraphrase_thresh
        )
        elapsed_time = round(time.time() - start_time, 2)

        scan_id = str(uuid.uuid4())[:8]
        results['scan_id'] = scan_id
        results['filename'] = filename
        results['word_count'] = len(query_text.split())
        results['char_count'] = len(query_text)
        results['processing_time_sec'] = elapsed_time
        results['timestamp'] = time.strftime('%Y-%m-%d %H:%M:%S')

        # Save to history
        history_entry = {
            'scan_id': scan_id,
            'filename': filename,
            'overall_score': results['overall_score'],
            'plagiarized_percent': results['plagiarized_percent'],
            'exact_match_percent': results['exact_match_percent'],
            'paraphrased_percent': results['paraphrased_percent'],
            'unique_percent': results['unique_percent'],
            'word_count': results['word_count'],
            'total_sentences': results['total_sentences'],
            'top_source': results['sources_summary'][0]['name'] if results['sources_summary'] else 'None',
            'timestamp': results['timestamp']
        }
        save_history_entry(history_entry)

        return jsonify(results)

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'error': f"An error occurred during plagiarism check: {str(e)}"}), 500

@app.route('/api/repository', methods=['GET'])
def get_repository():
    meta = get_repo_metadata()
    stats = get_repository_stats()
    return jsonify({'files': meta, 'stats': stats})

@app.route('/api/repository/upload', methods=['POST'])
def upload_to_repository():
    if 'file' not in request.files:
        return jsonify({'error': 'No file uploaded.'}), 400
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'Empty filename.'}), 400
    
    allowed_exts = ['.txt', '.pdf', '.docx', '.doc']
    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in allowed_exts:
        return jsonify({'error': f'Unsupported file type: {ext}. Allowed: .txt, .pdf, .docx'}), 400

    try:
        doc_entry = add_document_to_repo(file, file.filename)
        return jsonify({'message': f"Document '{file.filename}' added to reference repository.", 'document': doc_entry})
    except Exception as e:
        return jsonify({'error': f"Failed to add document: {str(e)}"}), 500

@app.route('/api/repository/<doc_id>', methods=['DELETE'])
def delete_repository_doc(doc_id):
    deleted = delete_document_from_repo(doc_id)
    if deleted:
        return jsonify({'message': 'Document deleted successfully.'})
    else:
        return jsonify({'error': 'Document ID not found.'}), 404

@app.route('/api/history', methods=['GET', 'DELETE'])
def manage_history():
    if request.method == 'DELETE':
        save_history_entry([])
        with open(HISTORY_FILE, 'w', encoding='utf-8') as f:
            json.dump([], f)
        return jsonify({'message': 'Scan history cleared.'})
    return jsonify(load_history())

import html

@app.route('/api/export-report', methods=['POST'])
def export_report():
    try:
        data = request.get_json() or {}
        raw_filename = data.get('filename', 'Plagiarism_Report')
        filename = html.escape(raw_filename)
        safe_filename = re.sub(r'[^\w\.-]', '_', raw_filename)
        overall_score = data.get('overall_score', 0)
        exact_pct = data.get('exact_match_percent', 0)
        para_pct = data.get('paraphrased_percent', 0)
        unique_pct = data.get('unique_percent', 0)
        total_sents = data.get('total_sentences', 0)
        sentences = data.get('sentence_results', [])
        sources = data.get('sources_summary', [])
        timestamp = html.escape(str(data.get('timestamp', time.strftime('%Y-%m-%d %H:%M:%S'))))

        # Generate HTML report
        sents_html = ""
        for s in sentences:
            s_text = html.escape(str(s.get('text', '')))
            s_status = html.escape(str(s.get('status', 'unique')))
            s_sim = s.get('similarity', 0)
            s_source = html.escape(str(s.get('matched_source', '')))
            s_matched_sent = html.escape(str(s.get('matched_sentence', '')))

            bg_color = '#fee2e2' if s_status == 'exact' else ('#fef3c7' if s_status == 'paraphrased' else '#dcfce7')
            border_color = '#ef4444' if s_status == 'exact' else ('#f59e0b' if s_status == 'paraphrased' else '#22c55e')
            
            sents_html += f"""
            <div style="margin-bottom: 12px; padding: 12px 16px; background-color: {bg_color}; border-left: 4px solid {border_color}; border-radius: 6px;">
                <p style="margin: 0 0 6px 0; font-size: 14px; font-weight: 500; color: #1e293b;">{s_text}</p>
                <div style="font-size: 12px; color: #64748b; display: flex; gap: 16px;">
                    <span>Status: <strong style="text-transform: capitalize;">{s_status}</strong></span>
                    <span>Similarity: <strong>{s_sim}%</strong></span>
                    {f"<span>Matched Source: <strong>{s_source}</strong></span>" if s_source else ""}
                </div>
                {f'<p style="margin: 6px 0 0 0; font-size: 12px; color: #475569; font-style: italic;">Matched sentence: "{s_matched_sent}"</p>' if s_matched_sent else ''}
            </div>
            """

        sources_html = ""
        for src in sources:
            src_name = html.escape(str(src.get('name', '')))
            src_type = html.escape(str(src.get('doc_type', '')))
            src_count = src.get('match_count', 0)
            src_sim = src.get('highest_sim', 0)
            sources_html += f"""
            <tr>
                <td style="padding: 10px; border-bottom: 1px solid #e2e8f0; font-size: 13px;">{src_name}</td>
                <td style="padding: 10px; border-bottom: 1px solid #e2e8f0; font-size: 13px; text-transform: uppercase;">{src_type}</td>
                <td style="padding: 10px; border-bottom: 1px solid #e2e8f0; font-size: 13px;">{src_count}</td>
                <td style="padding: 10px; border-bottom: 1px solid #e2e8f0; font-size: 13px; font-weight: bold;">{src_sim}%</td>
            </tr>
            """

        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <title>Plagiarism Analysis Report - {filename}</title>
            <style>
                body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; margin: 40px; color: #0f172a; background: #f8fafc; }}
                .container {{ max-width: 900px; margin: 0 auto; background: #ffffff; padding: 40px; border-radius: 12px; box-shadow: 0 4px 20px rgba(0,0,0,0.08); }}
                .header {{ border-bottom: 2px solid #e2e8f0; padding-bottom: 20px; margin-bottom: 30px; display: flex; justify-content: space-between; align-items: center; }}
                .title {{ font-size: 24px; font-weight: 700; color: #1e1b4b; margin: 0; }}
                .meta {{ font-size: 13px; color: #64748b; margin-top: 4px; }}
                .metrics {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 16px; margin-bottom: 30px; }}
                .metric-card {{ background: #f1f5f9; padding: 16px; border-radius: 8px; text-align: center; }}
                .metric-val {{ font-size: 24px; font-weight: 800; color: #312e81; }}
                .metric-lbl {{ font-size: 12px; color: #64748b; text-transform: uppercase; margin-top: 4px; }}
                h2 {{ font-size: 18px; margin-top: 30px; margin-bottom: 16px; color: #1e1b4b; border-bottom: 1px solid #e2e8f0; padding-bottom: 8px; }}
                table {{ width: 100%; border-collapse: collapse; margin-bottom: 30px; }}
                th {{ text-align: left; padding: 10px; background: #f1f5f9; font-size: 12px; text-transform: uppercase; color: #475569; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <div>
                        <h1 class="title">Plagiarism Analysis Report</h1>
                        <div class="meta">Document: <strong>{filename}</strong> | Generated: {timestamp}</div>
                    </div>
                </div>

                <div class="metrics">
                    <div class="metric-card">
                        <div class="metric-val" style="color: {'#dc2626' if overall_score >= 30 else '#16a34a'};">{overall_score}%</div>
                        <div class="metric-lbl">Overall Plagiarism</div>
                    </div>
                    <div class="metric-card">
                        <div class="metric-val" style="color: #dc2626;">{exact_pct}%</div>
                        <div class="metric-lbl">Exact Matches</div>
                    </div>
                    <div class="metric-card">
                        <div class="metric-val" style="color: #d97706;">{para_pct}%</div>
                        <div class="metric-lbl">Paraphrased</div>
                    </div>
                    <div class="metric-card">
                        <div class="metric-val" style="color: #16a34a;">{unique_pct}%</div>
                        <div class="metric-lbl">Unique Content</div>
                    </div>
                </div>

                <h2>Top Matching Sources</h2>
                <table>
                    <thead>
                        <tr>
                            <th>Source Name</th>
                            <th>Type</th>
                            <th>Matched Sentences</th>
                            <th>Highest Similarity</th>
                        </tr>
                    </thead>
                    <tbody>
                        {sources_html if sources_html else '<tr><td colspan="4" style="padding: 15px; text-align: center; color: #94a3b8;">No plagiarism matching sources found. Document is unique.</td></tr>'}
                    </tbody>
                </table>

                <h2>Sentence-by-Sentence Breakdown ({total_sents} sentences analyzed)</h2>
                {sents_html}
            </div>
        </body>
        </html>
        """

        response = make_response(html_content)
        response.headers["Content-Type"] = "text/html"
        response.headers["Content-Disposition"] = f"attachment; filename=Plagiarism_Report_{safe_filename}.html"
        return response

    except Exception as e:
        return jsonify({'error': f"Failed to generate report: {str(e)}"}), 500

if __name__ == '__main__':
    init_repository()
    populate_default_repository()
    print("\n========================================================")
    print("  AI-Powered Plagiarism Detection System (Flask App)  ")
    print("  Running at http://127.0.0.1:5000                   ")
    print("========================================================\n")
    app.run(host='0.0.0.0', port=5000, debug=True)
