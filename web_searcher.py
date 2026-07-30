import re
import urllib.parse
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed
from plagiarism_engine import split_into_sentences

# Headers for HTTP requests to mimic browser
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.5'
}

def extract_search_queries(text, max_queries=5):
    """
    Extracts the most distinctive sentences/phrases from input text to search on the web.
    """
    sentences = split_into_sentences(text)
    if not sentences:
        return []
    
    # Filter for long, unique sentences (> 6 words)
    long_sents = [s for s in sentences if len(s.split()) >= 6]
    if not long_sents:
        long_sents = sentences
        
    # Select distinct sentences spread across the document
    if len(long_sents) <= max_queries:
        selected = long_sents
    else:
        step = len(long_sents) / max_queries
        selected = [long_sents[int(i * step)] for i in range(max_queries)]
        
    # Clean quotes for search queries
    queries = []
    for s in selected:
        # Take a clean sub-phrase of 7-12 words
        words = re.sub(r'[^\w\s]', '', s).split()
        if len(words) >= 6:
            query = '"' + " ".join(words[:12]) + '"'
            queries.append(query)
        elif len(words) >= 3:
            query = " ".join(words)
            queries.append(query)
    return list(dict.fromkeys(queries)) # unique queries

def search_duckduckgo(query, max_results=3):
    """Executes search via duckduckgo_search or HTML fallback."""
    results = []
    try:
        from duckduckgo_search import DDGS
        with DDGS() as ddgs:
            ddg_results = list(ddgs.text(query, max_results=max_results))
            for item in ddg_results:
                url = item.get('href') or item.get('link')
                title = item.get('title', 'Web Page')
                snippet = item.get('body') or item.get('snippet', '')
                if url:
                    results.append({'url': url, 'title': title, 'snippet': snippet})
    except Exception as e:
        print(f"[WebSearch] DDGS library search note: {e}. Trying HTML search fallback.")
        # Fallback to DuckDuckGo HTML scraping
        try:
            from bs4 import BeautifulSoup
            search_url = f"https://html.duckduckgo.com/html/?q={urllib.parse.quote(query)}"
            resp = requests.get(search_url, headers=HEADERS, timeout=5)
            if resp.status_code == 200:
                soup = BeautifulSoup(resp.text, 'html.parser')
                links = soup.find_all('a', class_='result__url', limit=max_results)
                snippets = soup.find_all('a', class_='result__snippet', limit=max_results)
                titles = soup.find_all('a', class_='result__a', limit=max_results)
                for i in range(len(links)):
                    raw_url = links[i].get('href', '')
                    title = titles[i].get_text(strip=True) if i < len(titles) else 'Web Page'
                    snippet = snippets[i].get_text(strip=True) if i < len(snippets) else ''
                    if raw_url:
                        results.append({'url': raw_url, 'title': title, 'snippet': snippet})
        except Exception as e2:
            print(f"[WebSearch] HTML Search fallback note: {e2}")
    return results

def fetch_webpage_content(url):
    """Scrapes clean text content from a web page URL."""
    try:
        resp = requests.get(url, headers=HEADERS, timeout=5)
        if resp.status_code == 200:
            try:
                from bs4 import BeautifulSoup
                soup = BeautifulSoup(resp.text, 'html.parser')
                for element in soup(["script", "style", "nav", "header", "footer", "aside"]):
                    element.extract()
                text = soup.get_text(separator=' ')
            except Exception:
                # Basic regex fallback if bs4 not loaded yet
                text = re.sub(r'<[^>]+>', ' ', resp.text)

            clean = re.sub(r'\s+', ' ', text).strip()
            return clean[:8000] # limit to 8k chars for performance
    except Exception as e:
        print(f"[WebSearch] Failed to fetch URL {url}: {e}")
    return ""

def search_online_sources(query_text, max_queries=4, max_pages=6):
    """
    Main function to perform online plagiarism search for a query document text.
    Returns list of reference doc dicts: [{'id': str, 'name': str, 'text': str, 'type': 'web', 'url': str}]
    """
    queries = extract_search_queries(query_text, max_queries=max_queries)
    if not queries:
        return []

    print(f"[WebSearch] Executing {len(queries)} search queries for online plagiarism check...")
    found_urls = {} # url -> {title: str, snippet: str}

    for q in queries:
        items = search_duckduckgo(q, max_results=3)
        for item in items:
            url = item['url']
            if url not in found_urls and not url.endswith(('.pdf', '.docx', '.zip')):
                found_urls[url] = item
            if len(found_urls) >= max_pages:
                break
        if len(found_urls) >= max_pages:
            break

    if not found_urls:
        print("[WebSearch] No online URLs returned from search.")
        return []

    # Fetch webpage text in parallel threads
    web_docs = []
    with ThreadPoolExecutor(max_workers=5) as executor:
        future_to_url = {executor.submit(fetch_webpage_content, url): meta for url, meta in found_urls.items()}
        for future in as_completed(future_to_url):
            meta = future_to_url[future]
            content = future.result()
            if content and len(content.split()) >= 20:
                domain = urllib.parse.urlparse(meta['url']).netloc or meta['title']
                web_docs.append({
                    'id': meta['url'],
                    'name': f"{meta['title']} ({domain})",
                    'text': content,
                    'type': 'web',
                    'url': meta['url']
                })
            elif meta['snippet']:
                domain = urllib.parse.urlparse(meta['url']).netloc or meta['title']
                web_docs.append({
                    'id': meta['url'],
                    'name': f"{meta['title']} ({domain})",
                    'text': meta['snippet'],
                    'type': 'web',
                    'url': meta['url']
                })

    print(f"[WebSearch] Successfully retrieved {len(web_docs)} web reference pages.")
    return web_docs
