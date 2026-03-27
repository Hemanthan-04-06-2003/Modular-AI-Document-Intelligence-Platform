const storageKey = "rag-auth-token";
const userKey = "rag-auth-user";
const tempStorageKey = "rag-session-token";
const tempUserKey = "rag-session-user";
const signupForm = document.getElementById("signup-form");
const signinForm = document.getElementById("signin-form");
const resetForm = document.getElementById("reset-form");
const authFeedback = document.getElementById("auth-feedback");
const rememberMe = document.getElementById("remember-me");
const forgotToggle = document.getElementById("forgot-toggle");
const resetPanel = document.getElementById("reset-panel");
const resetClose = document.getElementById("reset-close");
const toggles = document.querySelectorAll(".password-toggle");
const showSigninButton = document.getElementById("show-signin");
const showSignupButton = document.getElementById("show-signup");

function saveSession(token, user, persistent) {
  localStorage.removeItem(storageKey);
  localStorage.removeItem(userKey);
  sessionStorage.removeItem(tempStorageKey);
  sessionStorage.removeItem(tempUserKey);

  if (persistent) {
    localStorage.setItem(storageKey, token);
    localStorage.setItem(userKey, JSON.stringify(user));
  } else {
    sessionStorage.setItem(tempStorageKey, token);
    sessionStorage.setItem(tempUserKey, JSON.stringify(user));
  }
}

function getToken() {
  return localStorage.getItem(storageKey) || sessionStorage.getItem(tempStorageKey);
}

async function requestJson(url, options = {}) {
  const response = await fetch(url, options);
  if (!response.ok) {
    let message = `Request failed with status ${response.status}`;
    try {
      const payload = await response.json();
      message = payload.detail || message;
    } catch (error) {}
    throw new Error(message);
  }
  return response.json();
}

function toggleResetPanel(forceOpen) {
  const shouldOpen = typeof forceOpen === "boolean" ? forceOpen : resetPanel.classList.contains("reset-hidden");
  resetPanel.classList.toggle("reset-hidden", !shouldOpen);
}

function showAuthMode(mode) {
  const signinActive = mode === "signin";
  signinForm.classList.toggle("auth-hidden", !signinActive);
  signupForm.classList.toggle("auth-hidden", signinActive);
  showSigninButton.classList.toggle("auth-switch-active", signinActive);
  showSignupButton.classList.toggle("auth-switch-active", !signinActive);
  authFeedback.textContent = "";
}

if (getToken()) {
  window.location.replace('/app');
}

toggles.forEach((button) => {
  button.addEventListener("click", () => {
    const input = document.getElementById(button.dataset.target);
    const isPassword = input.type === "password";
    input.type = isPassword ? "text" : "password";
    button.textContent = isPassword ? "Hide" : "Show";
  });
});

showSigninButton.addEventListener("click", () => showAuthMode("signin"));
showSignupButton.addEventListener("click", () => showAuthMode("signup"));
forgotToggle.addEventListener("click", () => toggleResetPanel(true));
resetClose.addEventListener("click", () => toggleResetPanel(false));

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
    saveSession(result.access_token, result.user, true);
    window.location.replace('/app');
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
    saveSession(result.access_token, result.user, rememberMe.checked);
    window.location.replace('/app');
  } catch (error) {
    authFeedback.textContent = error.message;
  }
});

resetForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  authFeedback.textContent = "Updating password...";
  try {
    const result = await requestJson("/api/auth/reset-password", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        email: document.getElementById("reset-email").value,
        new_password: document.getElementById("reset-password").value,
      }),
    });
    authFeedback.textContent = result.message;
    resetForm.reset();
    toggleResetPanel(false);
    showAuthMode("signin");
  } catch (error) {
    authFeedback.textContent = error.message;
  }
});

showAuthMode("signin");
