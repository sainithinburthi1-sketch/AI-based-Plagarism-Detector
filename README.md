# 🛡️ VeriTextAI — AI-Powered Plagiarism Detection System

An intelligent plagiarism detection web application built with **Python Flask**, leveraging **Sentence-Transformers** for deep semantic similarity analysis. Supports `.txt`, `.pdf`, and `.docx` file uploads or direct text pasting, with both local repository comparison and real-time online web search checking.

---

## ✨ Features

- **AI Semantic Similarity** — Uses `Sentence-Transformers` (`all-MiniLM-L6-v2`) to generate dense vector embeddings for paraphrase-aware detection, with an automatic TF-IDF + Cosine Similarity fallback.
- **Multi-Format File Support** — Upload `.txt`, `.pdf`, or `.docx` documents (up to 16 MB).
- **Dual Search Engine:**
  - 📁 **Local Reference Library** — Compare against your own saved reference documents.
  - 🌐 **Online Web Search** — Real-time DuckDuckGo search + web page scraping for live internet matching.
- **Sentence-Level Breakdown** — Color-coded highlighting of every sentence:
  - 🔴 **Exact Match** (≥ 88% similarity)
  - 🟡 **Paraphrased** (68–87% similarity)
  - 🟢 **Unique** (< 68% similarity)
- **Side-by-Side Inspector Modal** — Click any flagged sentence to compare it directly against its matched source.
- **Interactive Dashboard** — SVG gauge, KPI metrics, source cards with similarity bars, and scan history log.
- **Reference Library Manager** — Upload, view, and delete reference documents via the UI.
- **Scan History** — Tracks all past scans with scores and top matched sources.
- **HTML Report Export** — Download a full formatted HTML report of any scan result.
- **Light/Dark Theme Toggle** — Premium dark-mode UI with glassmorphism design.

---

## 📁 Project Structure

```
AI-Based Plagiarism Detector/
│
├── app.py                      # Flask application & REST API endpoints
├── plagiarism_engine.py        # AI similarity engine (SentenceTransformers + TF-IDF)
├── document_parser.py          # Multi-format text extractor (.txt, .pdf, .docx)
├── web_searcher.py             # Online DuckDuckGo search & web scraping module
├── repository_manager.py       # Local reference document library manager
├── requirements.txt            # Python dependencies
│
├── templates/
│   └── index.html              # Single-page web application HTML
│
├── static/
│   ├── css/
│   │   └── styles.css          # Premium dark/light theme styles
│   └── js/
│       └── main.js             # Frontend interactive logic
│
├── sample_documents/           # Pre-loaded sample reference papers
│   ├── Artificial_Intelligence_Overview.txt
│   └── Plagiarism_Ethics_Research.txt
│
└── data/                       # Auto-generated runtime data (gitignored)
    ├── repository/             # Stored reference document files + metadata.json
    └── history.json            # Scan history log
```

---

## 🚀 Getting Started

### Prerequisites

- Python **3.10+**
- `pip` package manager

### 1. Clone the Repository

```bash
git clone https://github.com/your-username/AI-Based-Plagiarism-Detector.git
cd "AI-Based-Plagiarism-Detector"
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

> **Note:** The first run will automatically download the `all-MiniLM-L6-v2` model (~85 MB) from Hugging Face. Subsequent runs will use the cached model.

### 3. Run the Application

```bash
python app.py
```

The server starts at **http://127.0.0.1:5000**

---

## 🔧 REST API Reference

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/` | Serves the web application |
| `POST` | `/api/check` | Perform plagiarism check (file upload or text) |
| `GET` | `/api/repository` | List all reference library documents |
| `POST` | `/api/repository/upload` | Add a document to the reference library |
| `DELETE` | `/api/repository/<id>` | Remove a document from the reference library |
| `GET` | `/api/history` | Get scan history |
| `DELETE` | `/api/history` | Clear scan history |
| `POST` | `/api/export-report` | Download HTML plagiarism report |

### `/api/check` — Form Data Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `file` | File | — | Uploaded `.txt`, `.pdf`, or `.docx` file |
| `text` | String | — | Raw text input (used if no file uploaded) |
| `check_local` | Boolean | `true` | Compare against local reference library |
| `check_web` | Boolean | `true` | Perform online web search comparison |
| `exact_threshold` | Integer (0–100) | `88` | Similarity threshold for exact match classification |
| `paraphrase_threshold` | Integer (0–100) | `68` | Similarity threshold for paraphrase classification |

---

## 🧠 How It Works

```
Input Document
      │
      ▼
Sentence Segmentation
      │
      ├──▶ Sentence-Transformers Embeddings (semantic vectors)
      │            │
      │            └──▶ Cosine Similarity Matrix
      │
      └──▶ TF-IDF N-gram Vectorizer (fallback / ensemble blend)
      │
      ▼
Compare Against:
  ├── Local Reference Library (indexed .txt / .pdf / .docx files)
  └── Web Search Results (DuckDuckGo → scrape page content)
      │
      ▼
Classify each sentence:
  - Exact Match  (similarity ≥ 88%)
  - Paraphrased  (similarity 68–87%)
  - Unique       (similarity < 68%)
      │
      ▼
Generate Report:
  - Overall Score, Sentence Breakdown, Source Summary
```

---

## 📦 Dependencies

| Package | Purpose |
|---------|---------|
| `Flask` | Web framework & REST API |
| `sentence-transformers` | AI semantic embedding model |
| `torch` | Deep learning backend for Sentence-Transformers |
| `scikit-learn` | TF-IDF vectorizer (fallback similarity engine) |
| `numpy` | Numerical matrix operations |
| `pypdf` | PDF text extraction |
| `python-docx` | DOCX text extraction |
| `beautifulsoup4` | Web page HTML parsing |
| `duckduckgo_search` | Online search API |
| `requests` | HTTP client for web scraping |

---

## 📸 Screenshots

> Launch the app and navigate to **http://127.0.0.1:5000** to see the live UI.

- **Plagiarism Checker Tab** — Drag-and-drop upload zone, text input, and AI settings panel.
- **Analysis Report Tab** — SVG gauge score, color-coded sentence highlights, and source match cards.
- **Reference Library Tab** — Manage your local reference document database.
- **Scan History Tab** — Past scan logs with scores and timestamps.

---

## ⚙️ Configuration Notes

- **Model Download**: `all-MiniLM-L6-v2` is downloaded automatically on first run to `~/.cache/huggingface/`. Internet access is needed only for this initial download.
- **TF-IDF Fallback**: If `sentence-transformers` fails to load (e.g., first-run model download), the system automatically switches to the TF-IDF engine and continues working.
- **Web Search Limits**: Online search fetches up to 6 web pages per scan. Adjust `max_pages` in `web_searcher.py` if needed.
- **File Size Limit**: Default 16 MB upload limit. Configurable via `MAX_CONTENT_LENGTH` in `app.py`.

---

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/new-feature`)
3. Commit your changes (`git commit -m 'Add new feature'`)
4. Push to the branch (`git push origin feature/new-feature`)
5. Open a Pull Request

---

## 📄 License

This project is licensed under the **MIT License** — see the [LICENSE](LICENSE) file for details.

---

## 👨‍💻 Author

Built with ❤️ using Python Flask & Sentence-Transformers AI.
