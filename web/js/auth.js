/**
 * Authentication module for GitHub Portfolio Search.
 * Supports Google Identity Services (GIS), GitHub OAuth, and password gate.
 *
 * When googleClientId is configured in config.json, shows Google Sign-In.
 * When githubClientId is configured, shows "Sign in with GitHub".
 * When neither is configured, falls back to the classic password gate ("guild").
 */
const Auth = (() => {
  const STORAGE_KEY = "ghps_auth_state";
  const PASSWORD_KEY = "ghps_auth";
  const EXPECTED_PASSWORD = "guild";

  let _config = { googleClientId: "", githubClientId: "", githubTokenUrl: "", apiUrl: "" };
  let _onAuthChange = null;

  /**
   * Load config.json to determine auth mode.
   */
  async function loadConfig() {
    try {
      const res = await fetch("config.json");
      if (res.ok) {
        _config = await res.json();
      }
    } catch {
      // config.json missing or invalid — use defaults (password gate)
    }

    // Check for GitHub OAuth callback (code in URL params)
    if (_config.githubClientId && window.location.search.includes("code=")) {
      await handleGitHubCallback();
    }

    return _config;
  }

  /**
   * Check if Google OAuth is configured.
   */
  function isOAuthEnabled() {
    return Boolean(_config.googleClientId);
  }

  /**
   * Decode a JWT payload without external libraries.
   * Only used for reading Google's ID token claims (email, name, picture).
   */
  function decodeJwtPayload(token) {
    try {
      const base64 = token.split(".")[1];
      const json = atob(base64.replace(/-/g, "+").replace(/_/g, "/"));
      return JSON.parse(json);
    } catch {
      return null;
    }
  }

  /**
   * Handle the Google Sign-In callback.
   * Called by google.accounts.id.initialize's callback.
   */
  function handleGoogleCallback(response) {
    const payload = decodeJwtPayload(response.credential);
    if (!payload) return;

    const authState = {
      provider: "google",
      token: response.credential,
      email: payload.email || "",
      name: payload.name || "",
      picture: payload.picture || "",
      githubUsername: "",
      expiry: (payload.exp || 0) * 1000, // convert to ms
    };

    localStorage.setItem(STORAGE_KEY, JSON.stringify(authState));
    _logSignIn(authState);

    if (_onAuthChange) _onAuthChange();
  }

  // --- GitHub OAuth ---

  function isGitHubOAuthEnabled() {
    return Boolean(_config.githubClientId);
  }

  function startGitHubOAuth() {
    if (!_config.githubClientId) return;
    const redirectUri = window.location.origin + window.location.pathname;
    const state = Math.random().toString(36).substring(2);
    sessionStorage.setItem("ghps_github_oauth_state", state);
    const url = "https://github.com/login/oauth/authorize" +
      "?client_id=" + encodeURIComponent(_config.githubClientId) +
      "&redirect_uri=" + encodeURIComponent(redirectUri) +
      "&scope=read:user user:email" +
      "&state=" + encodeURIComponent(state);
    window.location.href = url;
  }

  async function handleGitHubCallback() {
    const params = new URLSearchParams(window.location.search);
    const code = params.get("code");
    const state = params.get("state");
    if (!code) return false;

    const savedState = sessionStorage.getItem("ghps_github_oauth_state");
    if (state && savedState && state !== savedState) {
      console.error("[Auth] GitHub OAuth state mismatch");
      return false;
    }
    sessionStorage.removeItem("ghps_github_oauth_state");

    // Clean the URL (remove code/state params)
    const cleanUrl = window.location.origin + window.location.pathname + window.location.hash;
    window.history.replaceState({}, "", cleanUrl);

    // Exchange code for token via Lambda proxy
    if (!_config.githubTokenUrl) {
      console.error("[Auth] githubTokenUrl not configured");
      return false;
    }

    try {
      const resp = await fetch(_config.githubTokenUrl, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ code: code }),
      });
      if (!resp.ok) throw new Error("Token exchange failed: " + resp.status);
      const data = await resp.json();

      // Fetch GitHub user profile
      const userResp = await fetch("https://api.github.com/user", {
        headers: { Authorization: "Bearer " + data.access_token },
      });
      if (!userResp.ok) throw new Error("GitHub user fetch failed");
      const ghUser = await userResp.json();

      // Fetch email if not public
      let email = ghUser.email || "";
      if (!email) {
        try {
          const emailResp = await fetch("https://api.github.com/user/emails", {
            headers: { Authorization: "Bearer " + data.access_token },
          });
          if (emailResp.ok) {
            const emails = await emailResp.json();
            const primary = emails.find((e) => e.primary) || emails[0];
            if (primary) email = primary.email;
          }
        } catch { /* email optional */ }
      }

      const authState = {
        provider: "github",
        token: data.access_token,
        email: email,
        name: ghUser.name || ghUser.login,
        picture: ghUser.avatar_url || "",
        githubUsername: ghUser.login,
        expiry: Date.now() + 8 * 60 * 60 * 1000, // 8 hours
      };

      localStorage.setItem(STORAGE_KEY, JSON.stringify(authState));
      _logSignIn(authState);
      if (_onAuthChange) _onAuthChange();
      return true;
    } catch (err) {
      console.error("[Auth] GitHub OAuth error:", err);
      return false;
    }
  }

  /**
   * Check if the user is currently authenticated.
   * For OAuth: checks localStorage for a valid, non-expired token.
   * For password gate: checks sessionStorage.
   */
  function isAuthenticated() {
    if (isOAuthEnabled()) {
      const state = _getAuthState();
      if (!state) return false;
      // Check expiry
      if (state.expiry && Date.now() > state.expiry) {
        localStorage.removeItem(STORAGE_KEY);
        return false;
      }
      return true;
    }
    // Password gate fallback
    return sessionStorage.getItem(PASSWORD_KEY) === "1";
  }

  /**
   * Get the current user's profile info.
   * Returns { email, name, picture } or null if not authenticated.
   */
  function getUser() {
    if (!isOAuthEnabled()) return null;
    const state = _getAuthState();
    if (!state) return null;
    return {
      email: state.email,
      name: state.name,
      picture: state.picture,
      githubUsername: state.githubUsername || "",
      provider: state.provider || "google",
    };
  }

  /**
   * Render sign-in buttons into the given container.
   * Shows Google and/or GitHub buttons depending on config.
   */
  function renderSignInButton(containerEl) {
    // Google Sign-In
    if (isOAuthEnabled()) {
      function _render() {
        if (typeof google === "undefined" || !google.accounts || !google.accounts.id) return false;
        google.accounts.id.initialize({
          client_id: _config.googleClientId,
          callback: handleGoogleCallback,
        });
        google.accounts.id.renderButton(containerEl, {
          theme: "outline",
          size: "large",
          text: "signin_with",
          shape: "rectangular",
        });
        return true;
      }

      if (!_render()) {
        const loadingMsg = document.createElement("span");
        loadingMsg.textContent = "Loading Google Sign-In...";
        containerEl.appendChild(loadingMsg);
        let attempts = 0;
        const interval = setInterval(() => {
          attempts++;
          if (_render()) {
            loadingMsg.remove();
            clearInterval(interval);
          } else if (attempts > 25) {
            clearInterval(interval);
            loadingMsg.textContent = "Google Sign-In unavailable.";
          }
        }, 200);
      }
    }

    // GitHub Sign-In — button uses static SVG (safe, no user data)
    if (isGitHubOAuthEnabled()) {
      const ghBtn = document.createElement("button");
      ghBtn.className = "github-signin-btn";
      const icon = document.createElementNS("http://www.w3.org/2000/svg", "svg");
      icon.setAttribute("width", "18");
      icon.setAttribute("height", "18");
      icon.setAttribute("viewBox", "0 0 16 16");
      icon.setAttribute("fill", "currentColor");
      const path = document.createElementNS("http://www.w3.org/2000/svg", "path");
      path.setAttribute("fill-rule", "evenodd");
      path.setAttribute("d", "M8 0C3.58 0 0 3.58 0 8c0 3.54 2.29 6.53 5.47 7.59.4.07.55-.17.55-.38 0-.19-.01-.82-.01-1.49-2.01.37-2.53-.49-2.69-.94-.09-.23-.48-.94-.82-1.13-.28-.15-.68-.52-.01-.53.63-.01 1.08.58 1.23.82.72 1.21 1.87.87 2.33.66.07-.52.28-.87.51-1.07-1.78-.2-3.64-.89-3.64-3.95 0-.87.31-1.59.82-2.15-.08-.2-.36-1.02.08-2.12 0 0 .67-.21 2.2.82.64-.18 1.32-.27 2-.27.68 0 1.36.09 2 .27 1.53-1.04 2.2-.82 2.2-.82.44 1.1.16 1.92.08 2.12.51.56.82 1.27.82 2.15 0 3.07-1.87 3.75-3.65 3.95.29.25.54.73.54 1.48 0 1.07-.01 1.93-.01 2.2 0 .21.15.46.55.38A8.013 8.013 0 0016 8c0-4.42-3.58-8-8-8z");
      icon.appendChild(path);
      ghBtn.appendChild(icon);
      ghBtn.appendChild(document.createTextNode(" Sign in with GitHub"));
      ghBtn.addEventListener("click", startGitHubOAuth);
      containerEl.appendChild(ghBtn);
    }
  }

  /**
   * Sign the user out. Clears auth state from localStorage.
   */
  function signOut() {
    localStorage.removeItem(STORAGE_KEY);
    if (typeof google !== "undefined" && google.accounts && google.accounts.id) {
      google.accounts.id.disableAutoSelect();
    }
    sessionStorage.removeItem(PASSWORD_KEY);
    if (_onAuthChange) _onAuthChange();
  }

  /**
   * Attempt password-gate login.
   * Returns true if the password is correct.
   */
  function tryPasswordLogin(password) {
    if (password === EXPECTED_PASSWORD) {
      sessionStorage.setItem(PASSWORD_KEY, "1");
      return true;
    }
    return false;
  }

  /**
   * Set a callback for auth state changes (sign-in, sign-out).
   */
  function onAuthChange(callback) {
    _onAuthChange = callback;
  }

  /**
   * Get the API URL from config.
   */
  function getApiUrl() {
    return _config.apiUrl || "";
  }

  // --- Private helpers ---

  /**
   * Log a sign-in event to the remote logging endpoint (fire-and-forget).
   */
  function _logSignIn(authState) {
    const url = _config.signinLogUrl;
    if (!url) return;
    fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        email: authState.email || "",
        name: authState.name || "",
        provider: authState.provider || "",
        githubUsername: authState.githubUsername || "",
      }),
    }).catch(() => { /* fire-and-forget */ });
  }

  function _getAuthState() {
    try {
      const raw = localStorage.getItem(STORAGE_KEY);
      if (!raw) return null;
      return JSON.parse(raw);
    } catch {
      return null;
    }
  }

  /**
   * Check if the authenticated user is the admin.
   */
  function isAdmin() {
    const user = getUser();
    if (!user || !user.email) return false;
    const adminEmail = (_config.adminEmail || "").toLowerCase();
    return adminEmail && user.email.toLowerCase() === adminEmail;
  }

  /**
   * Check if the authenticated user is approved for gated features.
   * Admin is always approved. Others check the local approved list.
   */
  function isApproved() {
    if (isAdmin()) return true;
    const user = getUser();
    if (!user || !user.email) return false;
    const approved = _getApprovedList();
    return approved.includes(user.email.toLowerCase());
  }

  // --- Access request management (localStorage-based for static site) ---
  const ACCESS_STORAGE_KEY = "ghps_access_requests";
  const APPROVED_STORAGE_KEY = "ghps_approved_emails";

  function _getApprovedList() {
    try {
      return JSON.parse(localStorage.getItem(APPROVED_STORAGE_KEY) || "[]");
    } catch { return []; }
  }

  function _getAccessRequests() {
    try {
      return JSON.parse(localStorage.getItem(ACCESS_STORAGE_KEY) || "[]");
    } catch { return []; }
  }

  function submitAccessRequest(name, email, reason) {
    const requests = _getAccessRequests();
    const emailLower = email.toLowerCase();
    if (requests.some((r) => r.email === emailLower)) return false;
    requests.push({ name, email: emailLower, reason, date: new Date().toISOString() });
    localStorage.setItem(ACCESS_STORAGE_KEY, JSON.stringify(requests));
    return true;
  }

  function getPendingRequests() {
    const approved = _getApprovedList();
    return _getAccessRequests().filter((r) => !approved.includes(r.email));
  }

  function approveAccess(email) {
    const approved = _getApprovedList();
    const emailLower = email.toLowerCase();
    if (!approved.includes(emailLower)) {
      approved.push(emailLower);
      localStorage.setItem(APPROVED_STORAGE_KEY, JSON.stringify(approved));
    }
  }

  function denyAccess(email) {
    const requests = _getAccessRequests().filter((r) => r.email !== email.toLowerCase());
    localStorage.setItem(ACCESS_STORAGE_KEY, JSON.stringify(requests));
  }

  return {
    loadConfig,
    isOAuthEnabled,
    isAuthenticated,
    isApproved,
    isAdmin,
    getUser,
    renderSignInButton,
    signOut,
    tryPasswordLogin,
    onAuthChange,
    getApiUrl,
    submitAccessRequest,
    getPendingRequests,
    approveAccess,
    denyAccess,
  };
})();
