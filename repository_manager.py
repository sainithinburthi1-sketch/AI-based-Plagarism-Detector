import os
import uuid
import json
import shutil
from document_parser import extract_text_from_file
from plagiarism_engine import split_into_sentences

REPO_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data', 'repository')
META_FILE = os.path.join(REPO_DIR, 'metadata.json')

def init_repository():
    """Ensures repository directory exists."""
    os.makedirs(REPO_DIR, exist_ok=True)
    if not os.path.exists(META_FILE):
        with open(META_FILE, 'w', encoding='utf-8') as f:
            json.dump([], f, indent=2)

def get_metadata():
    """Loads metadata list of reference files."""
    init_repository()
    try:
        with open(META_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return []

def save_metadata(meta_list):
    """Saves metadata list."""
    init_repository()
    with open(META_FILE, 'w', encoding='utf-8') as f:
        json.dump(meta_list, f, indent=2)

def add_document_to_repo(file_obj_or_path, filename):
    """
    Saves a file into the local repository and indexes its content.
    """
    init_repository()
    doc_id = str(uuid.uuid4())[:8]
    clean_fname = re.sub(r'[^\w\.-]', '_', os.path.basename(filename or 'document'))
    ext = os.path.splitext(clean_fname)[1].lower() or '.txt'
    saved_filename = f"{doc_id}_{clean_fname}"
    saved_filepath = os.path.join(REPO_DIR, saved_filename)

    if isinstance(file_obj_or_path, str):
        shutil.copy(file_obj_or_path, saved_filepath)
        text_content = extract_text_from_file(saved_filepath, filename=clean_fname)
    else:
        if hasattr(file_obj_or_path, 'seek'):
            file_obj_or_path.seek(0)
        file_obj_or_path.save(saved_filepath)
        text_content = extract_text_from_file(saved_filepath, filename=clean_fname)

    sentences = split_into_sentences(text_content)
    word_count = len(text_content.split())
    file_size = os.path.getsize(saved_filepath)

    meta = get_metadata()
    doc_entry = {
        'id': doc_id,
        'filename': filename,
        'saved_filename': saved_filename,
        'size_bytes': file_size,
        'word_count': word_count,
        'sentence_count': len(sentences),
        'added_at': os.path.getmtime(saved_filepath)
    }
    meta.append(doc_entry)
    save_metadata(meta)
    return doc_entry

def get_all_repository_documents():
    """
    Reads and extracts text from all repository files.
    Returns list of dicts: [{'id': str, 'name': str, 'text': str, 'type': 'local'}]
    """
    init_repository()
    meta = get_metadata()
    docs = []
    for entry in meta:
        filepath = os.path.join(REPO_DIR, entry['saved_filename'])
        if os.path.exists(filepath):
            try:
                text = extract_text_from_file(filepath, filename=entry['filename'])
                if text:
                    docs.append({
                        'id': entry['id'],
                        'name': entry['filename'],
                        'text': text,
                        'type': 'local',
                        'url': ''
                    })
            except Exception as e:
                print(f"[RepoManager] Error reading repo doc {entry['filename']}: {e}")
    return docs

def delete_document_from_repo(doc_id):
    """Deletes a document from the repository by ID."""
    init_repository()
    meta = get_metadata()
    new_meta = []
    deleted = False

    for entry in meta:
        if entry['id'] == doc_id:
            filepath = os.path.join(REPO_DIR, entry['saved_filename'])
            if os.path.exists(filepath):
                try:
                    os.remove(filepath)
                except Exception:
                    pass
            deleted = True
        else:
            new_meta.append(entry)

    save_metadata(new_meta)
    return deleted

def get_repository_stats():
    """Returns total files, total sentences, and size."""
    meta = get_metadata()
    total_files = len(meta)
    total_words = sum(e.get('word_count', 0) for e in meta)
    total_sentences = sum(e.get('sentence_count', 0) for e in meta)
    total_bytes = sum(e.get('size_bytes', 0) for e in meta)
    
    return {
        'total_files': total_files,
        'total_words': total_words,
        'total_sentences': total_sentences,
        'total_size_mb': round(total_bytes / (1024 * 1024), 2)
    }
