/**
 * VeriTextAI - Plagiarism Detector Frontend Logic
 */

document.addEventListener('DOMContentLoaded', () => {
    // Global State
    let currentFile = null;
    let inputMode = 'file'; // 'file' | 'text'
    let currentResults = null;

    // Element References
    const themeToggleBtn = document.getElementById('theme-toggle');
    const navTabs = document.querySelectorAll('.nav-tab');
    const tabPanes = document.querySelectorAll('.tab-pane');
    const tabResultsBtn = document.getElementById('tab-results-btn');

    // Input elements
    const btnModeFile = document.getElementById('btn-mode-file');
    const btnModeText = document.getElementById('btn-mode-text');
    const dropzoneArea = document.getElementById('dropzone-area');
    const fileInput = document.getElementById('file-input');
    const filePreview = document.getElementById('file-preview');
    const previewFilename = document.getElementById('preview-filename');
    const previewFilesize = document.getElementById('preview-filesize');
    const btnRemoveFile = document.getElementById('btn-remove-file');
    const textAreaContainer = document.getElementById('text-area-container');
    const textInput = document.getElementById('text-input');
    const wordCountBadge = document.getElementById('word-count-badge');
    const charCountBadge = document.getElementById('char-count-badge');

    // Options & Controls
    const chkLocal = document.getElementById('chk-local');
    const chkWeb = document.getElementById('chk-web');
    const rangeParaphrase = document.getElementById('range-paraphrase');
    const paraphraseVal = document.getElementById('paraphrase-val');
    const rangeExact = document.getElementById('range-exact');
    const exactVal = document.getElementById('exact-val');
    const btnLoadSample = document.getElementById('btn-load-sample');
    const btnRunCheck = document.getElementById('btn-run-check');

    // Loading & Results elements
    const loadingOverlay = document.getElementById('loading-overlay');
    const resultsContent = document.getElementById('results-content');
    const resDocFilename = document.getElementById('res-doc-filename');
    const resDocTimestamp = document.getElementById('res-doc-timestamp');
    const resDocSpeed = document.getElementById('res-doc-speed');
    const resScoreOverall = document.getElementById('res-score-overall');
    const gaugeFill = document.getElementById('gauge-fill');
    const resExactPct = document.getElementById('res-exact-pct');
    const resExactCount = document.getElementById('res-exact-count');
    const resParaPct = document.getElementById('res-para-pct');
    const resParaCount = document.getElementById('res-para-count');
    const resUniquePct = document.getElementById('res-unique-pct');
    const resUniqueCount = document.getElementById('res-unique-count');
    const sentenceHighlightBox = document.getElementById('sentence-highlight-box');
    const sourcesList = document.getElementById('sources-list');
    const sourceCountNum = document.getElementById('source-count-num');
    const btnExportReport = document.getElementById('btn-export-report');
    const btnNewScan = document.getElementById('btn-new-scan');

    // Modal elements
    const inspectorModal = document.getElementById('inspector-modal');
    const btnCloseModal = document.getElementById('btn-close-modal');
    const modalQueryText = document.getElementById('modal-query-text');
    const modalSourceText = document.getElementById('modal-source-text');
    const modalMatchBadge = document.getElementById('modal-match-badge');
    const modalSourceName = document.getElementById('modal-source-name');
    const modalSourceUrl = document.getElementById('modal-source-url');

    // Repo & History elements
    const repoFileInput = document.getElementById('repo-file-input');
    const btnClearHistory = document.getElementById('btn-clear-history');

    /* ==========================================================================
       1. Theme Toggle & Navigation
       ========================================================================== */
    themeToggleBtn.addEventListener('click', () => {
        const currentTheme = document.documentElement.getAttribute('data-theme');
        const nextTheme = currentTheme === 'dark' ? 'light' : 'dark';
        document.documentElement.setAttribute('data-theme', nextTheme);
        themeToggleBtn.querySelector('i').className = nextTheme === 'dark' ? 'fa-solid fa-moon' : 'fa-solid fa-sun';
    });

    navTabs.forEach(tab => {
        tab.addEventListener('click', () => {
            if (tab.disabled) return;
            const targetPaneId = `${tab.getAttribute('data-tab')}-tab`;

            navTabs.forEach(t => t.classList.remove('active'));
            tabPanes.forEach(p => p.classList.remove('active'));

            tab.classList.add('active');
            const targetPane = document.getElementById(targetPaneId);
            if (targetPane) targetPane.classList.add('active');

            if (tab.getAttribute('data-tab') === 'repository') loadRepositoryData();
            if (tab.getAttribute('data-tab') === 'history') loadHistoryData();
        });
    });

    /* ==========================================================================
       2. Input Mode Switching & Drag-and-Drop
       ========================================================================== */
    btnModeFile.addEventListener('click', () => {
        inputMode = 'file';
        btnModeFile.classList.add('active');
        btnModeText.classList.remove('active');
        dropzoneArea.classList.remove('hidden');
        textAreaContainer.classList.add('hidden');
    });

    btnModeText.addEventListener('click', () => {
        inputMode = 'text';
        btnModeText.classList.add('active');
        btnModeFile.classList.remove('active');
        dropzoneArea.classList.add('hidden');
        textAreaContainer.classList.remove('hidden');
        textInput.focus();
    });

    // Drag and drop handlers
    ['dragenter', 'dragover'].forEach(eventName => {
        dropzoneArea.addEventListener(eventName, (e) => {
            e.preventDefault();
            e.stopPropagation();
            dropzoneArea.classList.add('dragover');
        });
    });

    ['dragleave', 'drop'].forEach(eventName => {
        dropzoneArea.addEventListener(eventName, (e) => {
            e.preventDefault();
            e.stopPropagation();
            dropzoneArea.classList.remove('dragover');
        });
    });

    dropzoneArea.addEventListener('drop', (e) => {
        const files = e.dataTransfer.files;
        if (files.length > 0) handleFileSelection(files[0]);
    });

    fileInput.addEventListener('change', (e) => {
        if (fileInput.files.length > 0) handleFileSelection(fileInput.files[0]);
    });

    btnRemoveFile.addEventListener('click', (e) => {
        e.stopPropagation();
        currentFile = null;
        fileInput.value = '';
        dropzoneArea.querySelector('.dropzone-content').classList.remove('hidden');
        filePreview.classList.add('hidden');
    });

    function handleFileSelection(file) {
        const allowedExts = ['txt', 'pdf', 'docx', 'doc'];
        const ext = file.name.split('.').pop().toLowerCase();
        if (!allowedExts.includes(ext)) {
            alert(`Unsupported file type (.${ext}). Please select a .TXT, .PDF, or .DOCX file.`);
            return;
        }

        currentFile = file;
        previewFilename.textContent = file.name;
        previewFilesize.textContent = formatBytes(file.size);
        dropzoneArea.querySelector('.dropzone-content').classList.add('hidden');
        filePreview.classList.remove('hidden');
    }

    // Textarea stats
    textInput.addEventListener('input', () => {
        const txt = textInput.value.trim();
        const words = txt ? txt.split(/\s+/).length : 0;
        wordCountBadge.innerHTML = `<i class="fa-solid fa-font"></i> ${words} words`;
        charCountBadge.innerHTML = `<i class="fa-solid fa-text-height"></i> ${txt.length} chars`;
    });

    // Threshold Sliders
    rangeParaphrase.addEventListener('input', (e) => {
        paraphraseVal.textContent = `${e.target.value}%`;
    });
    rangeExact.addEventListener('input', (e) => {
        exactVal.textContent = `${e.target.value}%`;
    });

    // Sample Text preset button
    btnLoadSample.addEventListener('click', () => {
        inputMode = 'text';
        btnModeText.click();
        textInput.value = `Artificial Intelligence (AI) is a multidisciplinary field of computer science focused on building smart machines capable of performing tasks that typically require human intelligence. Machine Learning (ML) is a subset of AI that provides systems the ability to automatically learn and improve from experience without being explicitly programmed. Deep Learning relies on artificial neural networks with multiple layers to model complex patterns in large datasets.

Academic integrity is the commitment to honest and responsible scholarship in scholarly research and writing. Plagiarism occurs when an author represents someone else's work, ideas, or expressions as their own without proper acknowledgement or citation.

Modern NLP architectures rely heavily on transformer models, such as BERT, GPT, and Sentence-Transformers, to compute high-dimensional semantic embeddings. By computing cosine similarity between sentence vectors, automated systems can instantly flag exact text matches and subtle paraphrasing across documents.`;
        textInput.dispatchEvent(new Event('input'));
    });

    /* ==========================================================================
       3. Running Plagiarism Check API
       ========================================================================== */
    btnRunCheck.addEventListener('click', async () => {
        if (inputMode === 'file' && !currentFile) {
            alert('Please upload a .TXT, .PDF, or .DOCX file first or switch to "Paste Text" mode.');
            return;
        }
        if (inputMode === 'text' && !textInput.value.trim()) {
            alert('Please paste some text into the textarea to analyze.');
            return;
        }

        // Show loading state and switch tab
        tabResultsBtn.disabled = false;
        tabResultsBtn.click();
        loadingOverlay.classList.remove('hidden');
        resultsContent.classList.add('hidden');

        try {
            const formData = new FormData();
            formData.append('check_local', chkLocal.checked);
            formData.append('check_web', chkWeb.checked);
            formData.append('exact_threshold', rangeExact.value);
            formData.append('paraphrase_threshold', rangeParaphrase.value);

            if (inputMode === 'file') {
                formData.append('file', currentFile);
            } else {
                formData.append('text', textInput.value.trim());
                formData.append('filename', 'Pasted Document');
            }

            const response = await fetch('/api/check', {
                method: 'POST',
                body: formData
            });

            if (!response.ok) {
                const errData = await response.json();
                throw new Error(errData.error || 'Server error during plagiarism check');
            }

            const data = await response.json();
            currentResults = data;
            renderResults(data);

        } catch (err) {
            alert(`Error: ${err.message}`);
            document.querySelector('[data-tab="checker"]').click();
        } finally {
            loadingOverlay.classList.add('hidden');
            resultsContent.classList.remove('hidden');
        }
    });

    /* ==========================================================================
       4. Render Results Dashboard
       ========================================================================== */
    function renderResults(data) {
        resDocFilename.innerHTML = `<i class="fa-solid fa-file-contract"></i> ${escapeHtml(data.filename)}`;
        resDocTimestamp.textContent = `Scanned ${data.timestamp}`;
        resDocSpeed.innerHTML = `<i class="fa-bolt"></i> ${data.processing_time_sec}s (${data.word_count} words)`;

        // Gauge SVG Calculation
        const overallScore = data.overall_score || 0;
        resScoreOverall.textContent = `${overallScore}%`;

        // Gauge fill animation
        // Radius = 65, circumference = 2 * PI * 65 ≈ 408.4
        const circumference = 408.4;
        const offset = circumference - (overallScore / 100) * circumference;
        gaugeFill.style.strokeDasharray = `${circumference}`;
        gaugeFill.style.strokeDashoffset = `${offset}`;

        if (overallScore >= 40) {
            gaugeFill.style.stroke = 'var(--danger-red)';
        } else if (overallScore >= 15) {
            gaugeFill.style.stroke = 'var(--warning-amber)';
        } else {
            gaugeFill.style.stroke = 'var(--success-green)';
        }

        // Metrics Card Values
        resExactPct.textContent = `${data.exact_match_percent}%`;
        resExactCount.textContent = `${data.exact_count} sentences`;

        resParaPct.textContent = `${data.paraphrased_percent}%`;
        resParaCount.textContent = `${data.paraphrase_count} sentences`;

        resUniquePct.textContent = `${data.unique_percent}%`;
        resUniqueCount.textContent = `${data.unique_count} sentences`;

        // Render Highlighted Sentences
        sentenceHighlightBox.innerHTML = '';
        data.sentence_results.forEach((s) => {
            const span = document.createElement('span');
            span.className = `sent-highlight ${s.status}`;
            span.textContent = s.text + ' ';

            if (s.status !== 'unique') {
                span.title = `Click to view match: ${s.similarity}% (${s.matched_source})`;
                span.addEventListener('click', () => openInspectorModal(s));
            }

            sentenceHighlightBox.appendChild(span);
        });

        // Render Sources List
        sourcesList.innerHTML = '';
        sourceCountNum.textContent = data.sources_summary.length;

        if (data.sources_summary.length === 0) {
            sourcesList.innerHTML = `
                <div class="source-card" style="text-align: center; color: var(--text-muted);">
                    <i class="fa-solid fa-circle-check" style="font-size: 28px; color: var(--success-green); margin-bottom: 8px;"></i>
                    <p>No matching plagiarism sources found. Document is 100% unique!</p>
                </div>
            `;
        } else {
            data.sources_summary.forEach((src) => {
                const card = document.createElement('div');
                card.className = 'source-card';
                card.innerHTML = `
                    <div class="source-card-header">
                        <span class="source-title">${escapeHtml(src.name)}</span>
                        <span class="badge-tag ${src.doc_type === 'web' ? 'badge-primary' : ''}">${src.doc_type.toUpperCase()}</span>
                    </div>
                    <div class="source-meta-row">
                        <span>Highest Match: <strong>${src.highest_sim}%</strong></span>
                        <span>Sentences: <strong>${src.match_count}</strong></span>
                    </div>
                    <div class="sim-bar-bg">
                        <div class="sim-bar-fill" style="width: ${src.highest_sim}%"></div>
                    </div>
                `;
                sourcesList.appendChild(card);
            });
        }
    }

    /* ==========================================================================
       5. Side-by-Side Modal Inspector
       ========================================================================== */
    function openInspectorModal(sentenceObj) {
        modalQueryText.textContent = sentenceObj.text;
        modalSourceText.textContent = sentenceObj.matched_sentence || 'N/A';
        modalMatchBadge.textContent = `${sentenceObj.status.toUpperCase()} MATCH (${sentenceObj.similarity}%)`;
        modalMatchBadge.className = `badge-tag ${sentenceObj.status === 'exact' ? 'badge-danger' : 'badge-warning'}`;
        modalSourceName.textContent = sentenceObj.matched_source;

        if (sentenceObj.matched_url) {
            modalSourceUrl.href = sentenceObj.matched_url;
            modalSourceUrl.classList.remove('hidden');
        } else {
            modalSourceUrl.classList.add('hidden');
        }

        inspectorModal.classList.remove('hidden');
    }

    btnCloseModal.addEventListener('click', () => {
        inspectorModal.classList.add('hidden');
    });

    inspectorModal.addEventListener('click', (e) => {
        if (e.target === inspectorModal) inspectorModal.classList.add('hidden');
    });

    btnNewScan.addEventListener('click', () => {
        document.querySelector('[data-tab="checker"]').click();
    });

    // Export HTML Report
    btnExportReport.addEventListener('click', async () => {
        if (!currentResults) return;
        try {
            const resp = await fetch('/api/export-report', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(currentResults)
            });

            const blob = await resp.blob();
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `Plagiarism_Report_${currentResults.filename || 'Analysis'}.html`;
            document.body.appendChild(a);
            a.click();
            a.remove();
        } catch (e) {
            alert('Failed to download report: ' + e.message);
        }
    });

    /* ==========================================================================
       6. Repository & History Handlers
       ========================================================================== */
    repoFileInput.addEventListener('change', async () => {
        if (repoFileInput.files.length === 0) return;
        const file = repoFileInput.files[0];
        const formData = new FormData();
        formData.append('file', file);

        try {
            const resp = await fetch('/api/repository/upload', {
                method: 'POST',
                body: formData
            });

            const data = await resp.json();
            if (!resp.ok) throw new Error(data.error || 'Failed to add reference document.');
            alert(data.message);
            loadRepositoryData();
        } catch (e) {
            alert(e.message);
        } finally {
            repoFileInput.value = '';
        }
    });

    async function loadRepositoryData() {
        try {
            const resp = await fetch('/api/repository');
            const data = await resp.json();

            document.getElementById('repo-total-files').textContent = data.stats.total_files;
            document.getElementById('repo-total-sentences').textContent = data.stats.total_sentences;
            document.getElementById('repo-total-size').textContent = `${data.stats.total_size_mb} MB`;

            const tbody = document.getElementById('repo-table-body');
            tbody.innerHTML = '';

            if (data.files.length === 0) {
                tbody.innerHTML = `<tr><td colspan="6" style="text-align: center; color: var(--text-muted); padding: 20px;">No reference documents found in library. Upload one above.</td></tr>`;
                return;
            }

            data.files.forEach(f => {
                const tr = document.createElement('tr');
                tr.innerHTML = `
                    <td><strong>${escapeHtml(f.filename)}</strong></td>
                    <td>${f.word_count}</td>
                    <td>${f.sentence_count}</td>
                    <td>${formatBytes(f.size_bytes)}</td>
                    <td>${new Date(f.added_at * 1000).toLocaleDateString()}</td>
                    <td>
                        <button class="btn btn-outline-danger btn-sm" onclick="deleteRepoDoc('${f.id}')">
                            <i class="fa-solid fa-trash"></i>
                        </button>
                    </td>
                `;
                tbody.appendChild(tr);
            });
        } catch (e) {
            console.error('Failed to load repository:', e);
        }
    }

    window.deleteRepoDoc = async function(docId) {
        if (!confirm('Are you sure you want to delete this document from the reference repository?')) return;
        try {
            const resp = await fetch(`/api/repository/${docId}`, { method: 'DELETE' });
            if (resp.ok) loadRepositoryData();
        } catch (e) {
            alert('Failed to delete document: ' + e.message);
        }
    };

    async function loadHistoryData() {
        try {
            const resp = await fetch('/api/history');
            const history = await resp.json();

            const tbody = document.getElementById('history-table-body');
            tbody.innerHTML = '';

            if (history.length === 0) {
                tbody.innerHTML = `<tr><td colspan="8" style="text-align: center; color: var(--text-muted); padding: 20px;">No past scan history.</td></tr>`;
                return;
            }

            history.forEach(item => {
                const tr = document.createElement('tr');
                tr.innerHTML = `
                    <td><code>${item.scan_id}</code></td>
                    <td><strong>${escapeHtml(item.filename)}</strong></td>
                    <td><span class="badge-tag ${item.overall_score >= 30 ? 'badge-danger' : ''}">${item.overall_score}%</span></td>
                    <td>${item.exact_match_percent}%</td>
                    <td>${item.paraphrased_percent}%</td>
                    <td>${item.unique_percent}%</td>
                    <td>${escapeHtml(item.top_source)}</td>
                    <td>${item.timestamp}</td>
                `;
                tbody.appendChild(tr);
            });
        } catch (e) {
            console.error('Failed to load history:', e);
        }
    }

    btnClearHistory.addEventListener('click', async () => {
        if (!confirm('Are you sure you want to clear all scan history?')) return;
        try {
            await fetch('/api/history', { method: 'DELETE' });
            loadHistoryData();
        } catch (e) {
            alert('Error clearing history: ' + e.message);
        }
    });

    // Helper Utilities
    function formatBytes(bytes, decimals = 1) {
        if (bytes === 0) return '0 Bytes';
        const k = 1024;
        const dm = decimals < 0 ? 0 : decimals;
        const sizes = ['Bytes', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(dm)) + ' ' + sizes[i];
    }

    function escapeHtml(str) {
        if (!str) return '';
        return str.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
    }
});
