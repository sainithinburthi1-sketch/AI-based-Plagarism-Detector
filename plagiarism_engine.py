import re
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

# SentenceTransformer lazy loading
_ST_MODEL = None
_ST_MODEL_FAILED = False

def get_sentence_transformer_model():
    """Lazy loader for SentenceTransformer to minimize startup time and provide smooth fallback."""
    global _ST_MODEL, _ST_MODEL_FAILED
    if _ST_MODEL is not None:
        return _ST_MODEL
    if _ST_MODEL_FAILED:
        return None
    
    try:
        from sentence_transformers import SentenceTransformer
        # Use lightweight & fast all-MiniLM-L6-v2
        _ST_MODEL = SentenceTransformer('all-MiniLM-L6-v2')
        print("[AI Engine] SentenceTransformer ('all-MiniLM-L6-v2') loaded successfully.")
        return _ST_MODEL
    except Exception as e:
        print(f"[AI Engine] Could not load SentenceTransformer: {str(e)}. Using TF-IDF Fallback Engine.")
        _ST_MODEL_FAILED = True
        return None

def split_into_sentences(text):
    """Splits body text into clean, non-empty sentences."""
    if not text:
        return []
    # Clean text
    clean = text.strip()
    # Regex split on sentence terminators while preserving sentence structure
    raw_sentences = re.split(r'(?<=[.!?])\s+|\n+', clean)
    sentences = []
    for s in raw_sentences:
        s_clean = s.strip()
        # Keep sentences with at least 2 words or 8 characters
        if len(s_clean.split()) >= 2 or len(s_clean) >= 8:
            sentences.append(s_clean)
    
    if not sentences and clean:
        sentences = [clean]
    return sentences

def compute_st_similarity(query_sentences, ref_sentences):
    """Computes similarity matrix using SentenceTransformer embeddings."""
    model = get_sentence_transformer_model()
    if model is None:
        return None
    try:
        q_embeds = model.encode(query_sentences, convert_to_numpy=True, normalize_embeddings=True)
        r_embeds = model.encode(ref_sentences, convert_to_numpy=True, normalize_embeddings=True)
        # Cosine similarity matrix shape (len(q), len(r))
        sim_matrix = np.dot(q_embeds, r_embeds.T)
        return np.clip(sim_matrix, 0.0, 1.0)
    except Exception as e:
        print(f"[AI Engine] Error in ST encoding: {e}")
        return None

def compute_tfidf_similarity(query_sentences, ref_sentences):
    """Computes similarity matrix using TF-IDF n-gram vectorizer."""
    if not query_sentences or not ref_sentences:
        return np.zeros((len(query_sentences), len(ref_sentences)))
    
    all_sentences = query_sentences + ref_sentences
    vectorizer = TfidfVectorizer(ngram_range=(1, 3), analyzer='word', lowercase=True)
    try:
        tfidf_matrix = vectorizer.fit_transform(all_sentences)
        q_matrix = tfidf_matrix[:len(query_sentences)]
        r_matrix = tfidf_matrix[len(query_sentences):]
        sim_matrix = cosine_similarity(q_matrix, r_matrix)
        return sim_matrix
    except Exception as e:
        print(f"[AI Engine] Error in TF-IDF matrix: {e}")
        return np.zeros((len(query_sentences), len(ref_sentences)))

def compute_sentence_similarity(query_sentences, ref_sentences):
    """
    Computes best cosine similarity matrix between query and reference sentences.
    Prefers SentenceTransformers; blends or falls back to TF-IDF.
    """
    st_matrix = compute_st_similarity(query_sentences, ref_sentences)
    tfidf_matrix = compute_tfidf_similarity(query_sentences, ref_sentences)
    
    if st_matrix is not None:
        # Ensemble: 70% SentenceTransformer + 30% TF-IDF for maximum precision
        blended = (0.75 * st_matrix) + (0.25 * tfidf_matrix)
        return blended
    else:
        return tfidf_matrix

def compare_documents(query_text, reference_docs, exact_threshold=0.88, paraphrase_threshold=0.68):
    """
    Compares a query text against a list of reference documents.
    
    :param query_text: Raw string or clean text of user input
    :param reference_docs: List of dicts: [{'id': str, 'name': str, 'text': str, 'type': 'local'|'web'}]
    :param exact_threshold: float 0-1 for exact match
    :param paraphrase_threshold: float 0-1 for paraphrase match
    :return: Comprehensive dict of results
    """
    query_sentences = split_into_sentences(query_text)
    if not query_sentences:
        return {
            'overall_score': 0,
            'plagiarized_percent': 0,
            'exact_match_percent': 0,
            'paraphrased_percent': 0,
            'unique_percent': 100,
            'total_sentences': 0,
            'sentence_results': [],
            'sources_summary': []
        }

    # Flatten reference sentences while keeping track of source document origin
    ref_sentences = []
    ref_map = [] # maps index in ref_sentences to doc metadata
    
    for doc in reference_docs:
        doc_text = doc.get('text', '')
        d_sentences = split_into_sentences(doc_text)
        for s in d_sentences:
            ref_sentences.append(s)
            ref_map.append({
                'doc_id': doc.get('id', 'unknown'),
                'doc_name': doc.get('name', 'Unknown Source'),
                'doc_type': doc.get('type', 'local'),
                'url': doc.get('url', ''),
                'sentence': s
            })

    if not ref_sentences:
        # No reference documents provided
        sentence_results = []
        for idx, s in enumerate(query_sentences):
            sentence_results.append({
                'index': idx,
                'text': s,
                'similarity': 0.0,
                'status': 'unique',
                'matched_sentence': '',
                'matched_source': '',
                'matched_source_type': '',
                'matched_url': ''
            })
        return {
            'overall_score': 0,
            'plagiarized_percent': 0,
            'exact_match_percent': 0,
            'paraphrased_percent': 0,
            'unique_percent': 100,
            'total_sentences': len(query_sentences),
            'sentence_results': sentence_results,
            'sources_summary': []
        }

    # Compute similarity matrix
    sim_matrix = compute_sentence_similarity(query_sentences, ref_sentences)

    sentence_results = []
    sources_stats = {} # doc_name -> {matches: int, highest_sim: float, doc_type: str, url: str}

    exact_count = 0
    paraphrase_count = 0
    unique_count = 0
    total_sim_sum = 0.0

    for idx, q_sent in enumerate(query_sentences):
        row_sims = sim_matrix[idx]
        best_ref_idx = int(np.argmax(row_sims))
        best_sim_score = float(row_sims[best_ref_idx])

        # Pre-pass check for exact normalized string matches across reference set
        clean_q = re.sub(r'[^\w\s]', '', q_sent.lower()).strip()
        if len(clean_q) > 8:
            for r_i, ref_info in enumerate(ref_map):
                clean_r = re.sub(r'[^\w\s]', '', ref_info['sentence'].lower()).strip()
                if clean_q == clean_r:
                    best_ref_idx = r_i
                    best_sim_score = 1.0
                    break

        best_ref_info = ref_map[best_ref_idx]
        sim_percentage = round(best_sim_score * 100, 1)

        if best_sim_score >= exact_threshold:
            status = 'exact'
            exact_count += 1
            total_sim_sum += best_sim_score
        elif best_sim_score >= paraphrase_threshold:
            status = 'paraphrased'
            paraphrase_count += 1
            total_sim_sum += best_sim_score
        else:
            status = 'unique'
            unique_count += 1

        matched_source = best_ref_info['doc_name']
        matched_url = best_ref_info.get('url', '')
        matched_type = best_ref_info['doc_type']

        if status != 'unique':
            if matched_source not in sources_stats:
                sources_stats[matched_source] = {
                    'name': matched_source,
                    'doc_type': matched_type,
                    'url': matched_url,
                    'match_count': 0,
                    'highest_sim': 0.0,
                    'total_sim': 0.0
                }
            sources_stats[matched_source]['match_count'] += 1
            sources_stats[matched_source]['highest_sim'] = max(sources_stats[matched_source]['highest_sim'], sim_percentage)
            sources_stats[matched_source]['total_sim'] += sim_percentage

        sentence_results.append({
            'index': idx,
            'text': q_sent,
            'similarity': sim_percentage,
            'status': status,
            'matched_sentence': best_ref_info['sentence'] if status != 'unique' else '',
            'matched_source': matched_source if status != 'unique' else '',
            'matched_source_type': matched_type if status != 'unique' else '',
            'matched_url': matched_url if status != 'unique' else ''
        })

    total_sents = len(query_sentences)
    plagiarized_count = exact_count + paraphrase_count
    
    exact_pct = round((exact_count / total_sents) * 100, 1)
    paraphrase_pct = round((paraphrase_count / total_sents) * 100, 1)
    unique_pct = round((unique_count / total_sents) * 100, 1)
    plagiarized_pct = round((plagiarized_count / total_sents) * 100, 1)

    # Calculate overall weighted similarity score
    if plagiarized_count > 0:
        overall_score = round((total_sim_sum / total_sents) * 100, 1)
    else:
        overall_score = 0.0

    # Format sources summary list
    sources_summary = []
    for s_name, stats in sources_stats.items():
        avg_sim = round(stats['total_sim'] / stats['match_count'], 1)
        sources_summary.append({
            'name': stats['name'],
            'doc_type': stats['doc_type'],
            'url': stats['url'],
            'match_count': stats['match_count'],
            'highest_sim': stats['highest_sim'],
            'avg_sim': avg_sim
        })
    # Sort sources by match_count desc, then highest_sim desc
    sources_summary.sort(key=lambda x: (x['match_count'], x['highest_sim']), reverse=True)

    return {
        'overall_score': overall_score,
        'plagiarized_percent': plagiarized_pct,
        'exact_match_percent': exact_pct,
        'paraphrased_percent': paraphrase_pct,
        'unique_percent': unique_pct,
        'total_sentences': total_sents,
        'exact_count': exact_count,
        'paraphrase_count': paraphrase_count,
        'unique_count': unique_count,
        'sentence_results': sentence_results,
        'sources_summary': sources_summary
    }
