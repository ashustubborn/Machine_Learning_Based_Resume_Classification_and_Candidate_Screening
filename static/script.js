const MAX_FILES = 25;
const ALLOWED_EXT = ['pdf', 'docx', 'txt'];

const dropzone = document.getElementById('dropzone');
const fileInput = document.getElementById('resumeFile');
const folderInput = document.getElementById('folderInput');
const folderBtn = document.getElementById('folderBtn');
const clearFilesBtn = document.getElementById('clearFilesBtn');
const fileCount = document.getElementById('fileCount');
const fileList = document.getElementById('fileList');
const form = document.getElementById('analyzeForm');
const analyzeBtn = document.getElementById('analyzeBtn');
const errorMsg = document.getElementById('errorMsg');

const emptyState = document.getElementById('emptyState');
const loadingState = document.getElementById('loadingState');
const resultContent = document.getElementById('resultContent');
const batchSummary = document.getElementById('batchSummary');
const failedList = document.getElementById('failedList');
const candidateList = document.getElementById('candidateList');

/* ---------------- Selected files (cumulative) ---------------- */
let selectedFiles = [];

function fileKey(f) { return `${f.name}|${f.size}|${f.lastModified}`; }
function extOf(name) { return name.includes('.') ? name.split('.').pop().toLowerCase() : ''; }

function addFiles(incoming) {
  const notes = [];
  let skippedType = 0, skippedDup = 0, skippedLimit = 0;
  const known = new Set(selectedFiles.map(fileKey));

  Array.from(incoming).forEach(f => {
    if (!ALLOWED_EXT.includes(extOf(f.name))) { skippedType++; return; }
    if (known.has(fileKey(f))) { skippedDup++; return; }
    if (selectedFiles.length >= MAX_FILES) { skippedLimit++; return; }
    selectedFiles.push(f);
    known.add(fileKey(f));
  });

  if (skippedLimit) notes.push(`${skippedLimit} not added (limit is ${MAX_FILES})`);
  if (skippedType) notes.push(`${skippedType} skipped (only .pdf, .docx, .txt)`);
  if (skippedDup) notes.push(`${skippedDup} already in the list`);
  renderFileList(notes.join(' · '), skippedLimit > 0);
}

function renderFileList(note, isWarning) {
  fileList.innerHTML = '';
  selectedFiles.forEach((f, i) => {
    const li = document.createElement('li');
    li.innerHTML = '<span class="fname"></span><button type="button" class="fremove" title="Remove">&times;</button>';
    li.querySelector('.fname').textContent = f.name;
    li.querySelector('.fremove').addEventListener('click', () => {
      selectedFiles.splice(i, 1);
      renderFileList('');
    });
    fileList.appendChild(li);
  });

  const n = selectedFiles.length;
  fileCount.textContent = n ? `${n} of ${MAX_FILES} resumes selected` + (note ? ` — ${note}` : '') : (note || '');
  fileCount.classList.toggle('warn', !!isWarning);
  clearFilesBtn.classList.toggle('hidden', n === 0);
  analyzeBtn.textContent = n > 1 ? `Screen ${n} resumes` : 'Screen this resume';
}

fileInput.addEventListener('change', () => {
  addFiles(fileInput.files);
  fileInput.value = '';          // lets the same file be picked again later
});

folderBtn.addEventListener('click', () => folderInput.click());
folderInput.addEventListener('change', () => {
  addFiles(folderInput.files);   // non-resume files in the folder are skipped automatically
  folderInput.value = '';
});

clearFilesBtn.addEventListener('click', () => { selectedFiles = []; renderFileList(''); });

['dragover', 'dragleave', 'drop'].forEach(evt => {
  dropzone.addEventListener(evt, (e) => {
    e.preventDefault();
    if (evt === 'dragover') dropzone.classList.add('dragover');
    if (evt === 'dragleave') dropzone.classList.remove('dragover');
    if (evt === 'drop') {
      dropzone.classList.remove('dragover');
      if (e.dataTransfer.files.length) addFiles(e.dataTransfer.files);
    }
  });
});

form.addEventListener('submit', async (e) => {
  e.preventDefault();
  errorMsg.textContent = '';

  if (!selectedFiles.length) {
    errorMsg.textContent = 'Please choose at least one resume file first.';
    return;
  }

  const formData = new FormData();
  selectedFiles.forEach(f => formData.append('resumes', f));
  formData.append('job_description', document.getElementById('jobDescription').value);

  analyzeBtn.disabled = true;
  analyzeBtn.textContent = selectedFiles.length > 1 ? 'Screening resumes…' : 'Screening…';
  emptyState.classList.add('hidden');
  resultContent.classList.add('hidden');
  loadingState.classList.remove('hidden');

  try {
    const res = await fetch('/analyze', { method: 'POST', body: formData });
    let data = {};
    try { data = await res.json(); } catch (_) { /* non-JSON error page */ }

    if (!res.ok) {
      throw new Error(data.error || (res.status === 413
        ? 'Files are too large (limit 40 MB per batch). Try fewer resumes.'
        : `Server error (${res.status}). Check the terminal for details.`));
    }

    switchTab('resultsTab');
    renderBatchResults(data);
    loadingState.classList.add('hidden');
    resultContent.classList.remove('hidden');
    loadHistory();
  } catch (err) {
    loadingState.classList.add('hidden');
    emptyState.classList.remove('hidden');
    errorMsg.textContent = err.message;
  } finally {
    analyzeBtn.disabled = false;
    renderFileList(fileCount.dataset.keep || '');
  }
});

function renderBatchResults(data) {
  const { results, failed, total_uploaded, ranked_by, batch_mode } = data;

  // --- summary line ---
  batchSummary.innerHTML = '';
  if (batch_mode) {
    const rankNote = ranked_by === 'match'
      ? 'ranked by job-description match'
      : 'ranked by classifier confidence (add a job description to rank by fit instead)';
    batchSummary.innerHTML = `
      <h2>${results.length} of ${total_uploaded} resumes screened</h2>
      <p>${rankNote}.</p>
    `;
  } else if (results.length === 1) {
    batchSummary.innerHTML = `<h2>1 resume screened</h2>`;
  }
  if (data.created_at) {
    batchSummary.innerHTML += `<p class="history-meta">Screened on ${formatDate(data.created_at)}</p>`;
  }

  // --- failed files ---
  failedList.innerHTML = '';
  if (failed && failed.length) {
    failedList.classList.remove('hidden');
    failed.forEach(f => {
      const row = document.createElement('div');
      row.className = 'failed-row';
      row.innerHTML = `<strong>${escapeHtml(f.filename)}</strong> — ${escapeHtml(f.error)}`;
      failedList.appendChild(row);
    });
  } else {
    failedList.classList.add('hidden');
  }

  // --- candidate cards ---
  candidateList.innerHTML = '';
  results.forEach((r, idx) => {
    candidateList.appendChild(buildCandidateCard(r, idx === 0));
  });
}

function buildCandidateCard(r, expandDefault) {
  const card = document.createElement('div');
  card.className = 'candidate-card' + (expandDefault ? ' expanded' : '');

  const scoreBadge = (r.match && r.match.match_percent !== null)
    ? `<span class="score-badge match">${r.match.match_percent}% fit</span>`
    : `<span class="score-badge conf">${r.confidence}% conf.</span>`;

  card.innerHTML = `
    <button type="button" class="candidate-header">
      <span class="rank-badge">#${r.rank}</span>
      <span class="candidate-name">${escapeHtml(r.filename)}</span>
      <span class="candidate-category">${escapeHtml(r.predicted_category)}</span>
      ${scoreBadge}
      <span class="chevron">▾</span>
    </button>
    <div class="candidate-body"></div>
  `;

  card.querySelector('.candidate-header').addEventListener('click', () => {
    card.classList.toggle('expanded');
  });

  const body = card.querySelector('.candidate-body');
  body.appendChild(buildCandidateDetail(r));

  return card;
}

function buildCandidateDetail(r) {
  const wrap = document.createElement('div');

  // confidence bar
  const verdict = document.createElement('div');
  verdict.className = 'verdict-block';
  verdict.innerHTML = `
    <span class="verdict-label">Predicted category</span>
    <h3 class="verdict-category">${escapeHtml(r.predicted_category)}</h3>
    <div class="confidence-row">
      <div class="confidence-bar"><div class="confidence-fill" style="width:${r.confidence}%"></div></div>
      <span class="confidence-num">${r.confidence}%</span>
    </div>
  `;
  wrap.appendChild(verdict);

  // top5
  const top5Section = document.createElement('div');
  top5Section.className = 'subsection';
  const top5List = document.createElement('div');
  top5List.className = 'top5-list';
  r.top5.forEach((item, i) => {
    const row = document.createElement('div');
    row.className = 'top5-row' + (i === 0 ? ' leader' : '');
    row.innerHTML = `
      <span class="top5-name">${escapeHtml(item.category)}</span>
      <div class="top5-bar-track"><div class="top5-bar-fill" style="width:${item.confidence}%"></div></div>
      <span class="top5-pct">${item.confidence}%</span>
    `;
    top5List.appendChild(row);
  });
  top5Section.innerHTML = '<h3>Category confidence — top 5</h3>';
  top5Section.appendChild(top5List);
  wrap.appendChild(top5Section);

  // skills
  const skillsSection = document.createElement('div');
  skillsSection.className = 'subsection';
  skillsSection.innerHTML = `<h3>Skills detected <span class="count">(${r.skills_found.length} found)</span></h3>`;
  const skillsRow = document.createElement('div');
  skillsRow.className = 'chip-row skills';
  if (r.skills_found.length === 0) {
    skillsRow.innerHTML = '<span class="chip">No known skills detected</span>';
  } else {
    r.skills_found.forEach(s => {
      const chip = document.createElement('span');
      chip.className = 'chip';
      chip.textContent = s;
      skillsRow.appendChild(chip);
    });
  }
  skillsSection.appendChild(skillsRow);
  wrap.appendChild(skillsSection);

  // match section
  if (r.match && r.match.match_percent !== null) {
    const matchSection = document.createElement('div');
    matchSection.className = 'subsection match-section';
    matchSection.innerHTML = `
      <h3>Fit against the job description</h3>
      <div class="match-score-row">
        <div class="match-score-circle"><span>${r.match.match_percent}%</span></div>
        <p class="match-explain">Share of the job description's required skills that this resume already covers.</p>
      </div>
      <div class="match-columns">
        <div>
          <span class="field-label good">Matched</span>
          <div class="chip-row skills matched" id="matched-${cssSafe(r.filename)}"></div>
        </div>
        <div>
          <span class="field-label missing">Missing</span>
          <div class="chip-row skills missing" id="missing-${cssSafe(r.filename)}"></div>
        </div>
      </div>
    `;
    wrap.appendChild(matchSection);

    const matchedEl = matchSection.querySelector(`#matched-${cssSafe(r.filename)}`);
    const missingEl = matchSection.querySelector(`#missing-${cssSafe(r.filename)}`);
    fillChips(matchedEl, r.match.matched_skills);
    fillChips(missingEl, r.match.missing_skills);
  }

  // preview
  const previewSection = document.createElement('div');
  previewSection.className = 'subsection';
  previewSection.innerHTML = `<h3>Extracted text preview <span class="count">(${r.word_count} words extracted)</span></h3>`;
  const pre = document.createElement('p');
  pre.className = 'preview-text';
  pre.textContent = r.resume_preview + (r.resume_preview.length >= 800 ? '…' : '');
  previewSection.appendChild(pre);
  wrap.appendChild(previewSection);

  return wrap;
}

function fillChips(container, items) {
  if (!items || items.length === 0) {
    container.innerHTML = '<span class="chip">None</span>';
    return;
  }
  items.forEach(s => {
    const chip = document.createElement('span');
    chip.className = 'chip';
    chip.textContent = s;
    container.appendChild(chip);
  });
}

function cssSafe(str) {
  return str.replace(/[^a-zA-Z0-9]/g, '_');
}

function escapeHtml(str) {
  const div = document.createElement('div');
  div.textContent = str;
  return div.innerHTML;
}


/* ---------------- Tabs ---------------- */
function switchTab(tabId) {
  document.querySelectorAll('.tab').forEach(t => t.classList.toggle('active', t.dataset.tab === tabId));
  document.querySelectorAll('.tab-pane').forEach(p => p.classList.toggle('hidden', p.id !== tabId));
}
document.querySelectorAll('.tab').forEach(t => {
  t.addEventListener('click', () => {
    switchTab(t.dataset.tab);
    if (t.dataset.tab === 'historyTab') loadHistory();
  });
});

/* ---------------- History ---------------- */
const historyList = document.getElementById('historyList');
const historyCount = document.getElementById('historyCount');
const clearHistoryBtn = document.getElementById('clearHistoryBtn');

function formatDate(iso) {
  const d = new Date(iso);
  return isNaN(d) ? iso : d.toLocaleString();
}

async function loadHistory() {
  try {
    const res = await fetch('/history');
    const data = await res.json();
    renderHistory(data.items || []);
  } catch (err) {
    historyList.innerHTML = '<p class="history-empty">Could not load history.</p>';
  }
}

function renderHistory(items) {
  historyList.innerHTML = '';
  historyCount.textContent = items.length ? `(${items.length})` : '';
  clearHistoryBtn.classList.toggle('hidden', items.length === 0);

  if (!items.length) {
    historyList.innerHTML = '<p class="history-empty">No screenings yet. Screen some resumes and they will show up here.</p>';
    return;
  }

  items.forEach(item => {
    const row = document.createElement('div');
    row.className = 'history-item';

    const countLabel = item.total_uploaded === 1 ? '1 resume' : `${item.total_uploaded} resumes`;
    const top = item.top_name
      ? `Top: ${escapeHtml(item.top_name)} — ${escapeHtml(item.top_category)} (${escapeHtml(item.top_score)})`
      : 'No readable resumes';
    const jd = item.jd_preview
      ? `<p class="history-jd">JD: ${escapeHtml(item.jd_preview)}</p>`
      : '';

    row.innerHTML = `
      <div class="history-main">
        <p class="history-title">${countLabel} · ${formatDate(item.created_at)}</p>
        <p class="history-meta">${top}</p>
        ${jd}
      </div>
      <div class="history-actions">
        <button type="button" class="btn-link view">View</button>
        <button type="button" class="btn-link danger">Delete</button>
      </div>
    `;

    row.querySelector('.view').addEventListener('click', () => openHistoryItem(item.id));
    row.querySelector('.danger').addEventListener('click', async () => {
      await fetch(`/history/${item.id}`, { method: 'DELETE' });
      loadHistory();
    });
    historyList.appendChild(row);
  });
}

async function openHistoryItem(id) {
  try {
    const res = await fetch(`/history/${id}`);
    const data = await res.json();
    if (!res.ok) throw new Error(data.error || 'Could not load screening.');
    emptyState.classList.add('hidden');
    loadingState.classList.add('hidden');
    renderBatchResults(data);
    resultContent.classList.remove('hidden');
    switchTab('resultsTab');
  } catch (err) {
    alert(err.message);
  }
}

clearHistoryBtn.addEventListener('click', async () => {
  if (!confirm('Delete all saved screenings? This cannot be undone.')) return;
  await fetch('/history', { method: 'DELETE' });
  loadHistory();
});

loadHistory();
