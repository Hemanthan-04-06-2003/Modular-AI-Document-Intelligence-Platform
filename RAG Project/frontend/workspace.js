const healthStatus = document.getElementById("health-status");
const refreshButton = document.getElementById("refresh-button");
const uploadForm = document.getElementById("upload-form");
const uploadFeedback = document.getElementById("upload-feedback");
const documentsList = document.getElementById("documents-list");
const featureList = document.getElementById("feature-list");
const chatForm = document.getElementById("chat-form");
const answerText = document.getElementById("answer-text");
const answerStatus = document.getElementById("answer-status");
const answerModeLabel = document.getElementById("answer-mode-label");
const selectedDocLabel = document.getElementById("selected-doc-label");
const sourceCount = document.getElementById("source-count");
const sourcesList = document.getElementById("sources-list");
const docSelect = document.getElementById("doc-select");
const authState = document.getElementById("auth-state");
const logoutButton = document.getElementById("logout-button");

const storageKey = "rag-auth-token";
const userKey = "rag-auth-user";
const tempStorageKey = "rag-session-token";
const tempUserKey = "rag-session-user";

let latestDocuments = [];

function getToken() {
  return localStorage.getItem(storageKey) || sessionStorage.getItem(tempStorageKey);
}

function getStoredUser() {
  const rawUser = localStorage.getItem(userKey) || sessionStorage.getItem(tempUserKey);
  if (!rawUser) return null;
  try {
    return JSON.parse(rawUser);
  } catch (error) {
    return null;
  }
}

function redirectToLogin() {
  window.location.replace('/login');
}

function clearSession() {
  localStorage.removeItem(storageKey);
  localStorage.removeItem(userKey);
  sessionStorage.removeItem(tempStorageKey);
  sessionStorage.removeItem(tempUserKey);
  redirectToLogin();
}

async function requestJson(url, options = {}) {
  const headers = new Headers(options.headers || {});
  const token = getToken();
  if (token) headers.set("Authorization", `Bearer ${token}`);

  const response = await fetch(url, { ...options, headers });
  if (!response.ok) {
    let message = `Request failed with status ${response.status}`;
    try {
      const payload = await response.json();
      message = payload.detail || message;
    } catch (error) {}
    if (response.status === 401) clearSession();
    throw new Error(message);
  }
  return response.json();
}

function updateSelectedDocSummary() {
  const selectedId = docSelect.value;
  if (!selectedId) {
    selectedDocLabel.textContent = 'All documents';
    return;
  }
  const selected = latestDocuments.find((doc) => doc.doc_id === selectedId);
  selectedDocLabel.textContent = selected ? selected.name : 'Selected document';
}

function resetAnswerState() {
  answerText.textContent = 'Your answer will appear here once the backend responds.';
  answerStatus.textContent = 'Ready';
  answerModeLabel.textContent = 'Waiting';
  sourceCount.textContent = '0 sources';
  renderSources([]);
}

function renderDocuments(documents) {
  latestDocuments = documents;
  documentsList.innerHTML = '';
  docSelect.innerHTML = '<option value="">All documents</option>';

  if (!documents.length) {
    documentsList.innerHTML = '<div class="document-card empty-card"><strong>No indexed PDFs yet</strong><p>Upload your first file to start your private workspace.</p></div>';
    updateSelectedDocSummary();
    return;
  }

  documents.forEach((doc) => {
    const card = document.createElement('div');
    card.className = 'document-card document-row';
    card.innerHTML = `
      <div class="document-meta">
        <strong>${doc.name}</strong>
        <p>${doc.chunk_count} chunks indexed</p>
      </div>
      <div class="document-actions">
        <button type="button" class="ghost-button mini-button select-doc" data-doc-id="${doc.doc_id}">Use</button>
        <button type="button" class="danger-button mini-button delete-doc" data-doc-id="${doc.doc_id}">Remove</button>
      </div>
    `;
    documentsList.appendChild(card);

    const option = document.createElement('option');
    option.value = doc.doc_id;
    option.textContent = doc.name;
    docSelect.appendChild(option);
  });

  updateSelectedDocSummary();
}

function renderFeatures(features) {
  featureList.innerHTML = '';
  features.forEach((feature) => {
    const card = document.createElement('div');
    card.className = 'feature-card';
    card.innerHTML = `<strong>${feature.title}</strong><p>${feature.description}</p><p>Priority: ${feature.priority}</p>`;
    featureList.appendChild(card);
  });
}

function renderSources(sources) {
  sourcesList.innerHTML = '';
  if (!sources.length) {
    sourcesList.innerHTML = '<div class="source-chip"><strong>No sources yet</strong><p>Sources will appear after a successful response.</p></div>';
    return;
  }
  sources.forEach((source) => {
    const chip = document.createElement('div');
    chip.className = 'source-chip';
    chip.innerHTML = `<strong>${source.document}</strong><p>${source.excerpt}</p>`;
    sourcesList.appendChild(chip);
  });
}

async function loadDashboard() {
  try {
    const health = await requestJson('/api/health');
    healthStatus.textContent = `Backend ${health.status} · ${health.loaded_documents} docs`;
    const features = await requestJson('/api/feature-ideas');
    renderFeatures(features);
    const documents = await requestJson('/api/documents');
    renderDocuments(documents);
  } catch (error) {
    healthStatus.textContent = 'Backend unavailable';
    uploadFeedback.textContent = error.message;
  }
}

async function deleteDocument(docId) {
  answerStatus.textContent = 'Updating';
  try {
    const result = await requestJson(`/api/documents/${docId}`, { method: 'DELETE' });
    uploadFeedback.textContent = result.message;
    if (docSelect.value === docId) {
      docSelect.value = '';
      resetAnswerState();
    }
    await loadDashboard();
    answerStatus.textContent = 'Ready';
  } catch (error) {
    uploadFeedback.textContent = error.message;
    answerStatus.textContent = 'Ready';
  }
}

const currentUser = getStoredUser();
if (!getToken() || !currentUser) {
  redirectToLogin();
} else {
  authState.textContent = `Signed in as ${currentUser.name}`;
}

refreshButton.addEventListener('click', loadDashboard);
logoutButton.addEventListener('click', clearSession);
docSelect.addEventListener('change', updateSelectedDocSummary);

documentsList.addEventListener('click', async (event) => {
  const selectButton = event.target.closest('.select-doc');
  const deleteButton = event.target.closest('.delete-doc');
  if (selectButton) {
    docSelect.value = selectButton.dataset.docId;
    updateSelectedDocSummary();
    return;
  }
  if (deleteButton) {
    await deleteDocument(deleteButton.dataset.docId);
  }
});

uploadForm.addEventListener('submit', async (event) => {
  event.preventDefault();
  uploadFeedback.textContent = 'Uploading and indexing...';
  answerStatus.textContent = 'Indexing';
  const formData = new FormData(uploadForm);
  try {
    const result = await requestJson('/api/documents/upload', { method: 'POST', body: formData });
    uploadFeedback.textContent = `${result.document.name} indexed successfully.`;
    uploadForm.reset();
    resetAnswerState();
    await loadDashboard();
    docSelect.value = result.document.doc_id;
    updateSelectedDocSummary();
    answerStatus.textContent = 'Ready';
  } catch (error) {
    uploadFeedback.textContent = error.message;
    answerStatus.textContent = 'Ready';
  }
});

chatForm.addEventListener('submit', async (event) => {
  event.preventDefault();
  answerText.textContent = 'Generating answer...';
  answerStatus.textContent = 'Generating';
  renderSources([]);
  sourceCount.textContent = 'Searching';
  const payload = { question: document.getElementById('question').value, doc_id: docSelect.value || null };
  try {
    const result = await requestJson('/api/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
    answerText.textContent = result.answer;
    answerStatus.textContent = 'Done';
    answerModeLabel.textContent = result.mode;
    sourceCount.textContent = `${result.sources.length} sources`;
    renderSources(result.sources);
  } catch (error) {
    answerText.textContent = error.message;
    answerStatus.textContent = 'Ready';
    answerModeLabel.textContent = 'Error';
    sourceCount.textContent = '0 sources';
  }
});

loadDashboard();
resetAnswerState();
