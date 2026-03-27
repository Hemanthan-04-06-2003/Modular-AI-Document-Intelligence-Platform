const authScreen = document.getElementById("auth-screen");
const appShell = document.getElementById("app-shell");
const healthStatus = document.getElementById("health-status");
const refreshButton = document.getElementById("refresh-button");
const uploadForm = document.getElementById("upload-form");
const uploadFeedback = document.getElementById("upload-feedback");
const documentsList = document.getElementById("documents-list");
const featureList = document.getElementById("feature-list");
const chatForm = document.getElementById("chat-form");
const answerText = document.getElementById("answer-text");
const sourcesList = document.getElementById("sources-list");
const docSelect = document.getElementById("doc-select");
const signupForm = document.getElementById("signup-form");
const signinForm = document.getElementById("signin-form");
const authFeedback = document.getElementById("auth-feedback");
const authState = document.getElementById("auth-state");
const logoutButton = document.getElementById("logout-button");

const storageKey = "rag-auth-token";
const userKey = "rag-auth-user";

function getToken() {
  return localStorage.getItem(storageKey);
}

function getStoredUser() {
  const rawUser = localStorage.getItem(userKey);
  if (!rawUser) return null;
  try {
    return JSON.parse(rawUser);
  } catch (error) {
    return null;
  }
}

function updateViewState() {
  const user = getStoredUser();
  const signedIn = Boolean(getToken() && user);
  authScreen.style.display = signedIn ? "none" : "grid";
  appShell.classList.toggle("app-hidden", !signedIn);
  authState.textContent = signedIn ? `Signed in as ${user.name}` : "Signed out";
}

function setSession(token, user) {
  localStorage.setItem(storageKey, token);
  localStorage.setItem(userKey, JSON.stringify(user));
  authFeedback.textContent = "";
  updateViewState();
}

function clearSession(showMessage = true) {
  localStorage.removeItem(storageKey);
  localStorage.removeItem(userKey);
  uploadFeedback.textContent = "";
  answerText.textContent = "Your answer will appear here once the backend responds.";
  renderSources([]);
  renderDocuments([]);
  docSelect.innerHTML = '<option value="">All documents</option>';
  if (showMessage) authFeedback.textContent = "You have been logged out.";
  updateViewState();
}

function loadSession() {
  if (!getToken() || !getStoredUser()) {
    clearSession(false);
    return;
  }
  updateViewState();
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
    } catch (error) {
      // Keep fallback message.
    }
    if (response.status === 401) clearSession(false);
    throw new Error(message);
  }
  return response.json();
}

function renderDocuments(documents) {
  documentsList.innerHTML = "";
  docSelect.innerHTML = '<option value="">All documents</option>';

  if (!documents.length) {
    documentsList.innerHTML = '<div class="document-card"><strong>No indexed PDFs yet</strong><p>Upload a file after signing in.</p></div>';
    return;
  }

  documents.forEach((doc) => {
    const card = document.createElement("div");
    card.className = "document-card";
    card.innerHTML = `
      <strong>${doc.name}</strong>
      <p>${doc.chunk_count} chunks indexed</p>
    `;
    documentsList.appendChild(card);

    const option = document.createElement("option");
    option.value = doc.doc_id;
    option.textContent = doc.name;
    docSelect.appendChild(option);
  });
}

function renderFeatures(features) {
  featureList.innerHTML = "";
  features.forEach((feature) => {
    const card = document.createElement("div");
    card.className = "feature-card";
    card.innerHTML = `
      <strong>${feature.title}</strong>
      <p>${feature.description}</p>
      <p>Priority: ${feature.priority}</p>
    `;
    featureList.appendChild(card);
  });
}

function renderSources(sources) {
  sourcesList.innerHTML = "";
  if (!sources.length) {
    sourcesList.innerHTML = '<div class="source-chip"><strong>No sources yet</strong><p>Sources will appear after a successful response.</p></div>';
    return;
  }

  sources.forEach((source) => {
    const chip = document.createElement("div");
    chip.className = "source-chip";
    chip.innerHTML = `
      <strong>${source.document}</strong>
      <p>${source.excerpt}</p>
    `;
    sourcesList.appendChild(chip);
  });
}

async function loadDashboard() {
  try {
    const health = await requestJson("/api/health");
    healthStatus.textContent = `Backend ${health.status} · ${health.loaded_documents} docs`;
    const features = await requestJson("/api/feature-ideas");
    renderFeatures(features);

    if (getToken()) {
      const documents = await requestJson("/api/documents");
      renderDocuments(documents);
    } else {
      renderDocuments([]);
    }
  } catch (error) {
    healthStatus.textContent = "Backend unavailable";
    uploadFeedback.textContent = error.message;
  }
}

refreshButton.addEventListener("click", loadDashboard);
logoutButton.addEventListener("click", async () => {
  clearSession();
  await loadDashboard();
});

signupForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  authFeedback.textContent = "Creating account...";
  try {
    const result = await requestJson("/api/auth/signup", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        name: document.getElementById("signup-name").value,
        email: document.getElementById("signup-email").value,
        password: document.getElementById("signup-password").value,
      }),
    });
    setSession(result.access_token, result.user);
    authFeedback.textContent = "Account created successfully.";
    signupForm.reset();
    await loadDashboard();
  } catch (error) {
    authFeedback.textContent = error.message;
  }
});

signinForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  authFeedback.textContent = "Signing in...";
  try {
    const result = await requestJson("/api/auth/signin", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        email: document.getElementById("signin-email").value,
        password: document.getElementById("signin-password").value,
      }),
    });
    setSession(result.access_token, result.user);
    authFeedback.textContent = "Signed in successfully.";
    signinForm.reset();
    await loadDashboard();
  } catch (error) {
    authFeedback.textContent = error.message;
  }
});

uploadForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  uploadFeedback.textContent = "Uploading and indexing...";
  const formData = new FormData(uploadForm);

  try {
    const result = await requestJson("/api/documents/upload", {
      method: "POST",
      body: formData,
    });
    uploadFeedback.textContent = `${result.document.name} indexed successfully.`;
    uploadForm.reset();
    await loadDashboard();
  } catch (error) {
    uploadFeedback.textContent = error.message;
  }
});

chatForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  answerText.textContent = "Generating answer...";
  renderSources([]);

  const payload = {
    question: document.getElementById("question").value,
    doc_id: docSelect.value || null,
  };

  try {
    const result = await requestJson("/api/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    answerText.textContent = result.answer;
    renderSources(result.sources);
  } catch (error) {
    answerText.textContent = error.message;
  }
});

loadSession();
loadDashboard();
