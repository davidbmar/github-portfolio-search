/**
 * Authentication module for GitHub Portfolio Search.
 * Supports Google Identity Services (GIS) with fallback to password gate.
 *
 * When googleClientId is configured in config.json, uses Google Sign-In.
 * When empty, falls back to the classic password gate ("guild").
 */
const Auth = (() => {
  const STORAGE_KEY = "ghps_auth_state";
  const PASSWORD_KEY = "ghps_auth";
  const EXPECTED_PASSWORD = "guild";

  let _config = { googleClientId: "", apiUrl: "" };
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
      token: response.credential,
      email: payload.email || "",
      name: payload.name || "",
      picture: payload.picture || "",
      expiry: (payload.exp || 0) * 1000, // convert to ms
    };

    localStorage.setItem(STORAGE_KEY, JSON.stringify(authState));

    if (_onAuthChange) _onAuthChange();
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
    };
  }

  /**
   * Initiate Google Sign-In.
   * Renders the Google Sign-In button into the given container element.
   */
  function renderSignInButton(containerEl) {
    if (!isOAuthEnabled()) return;

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

    // Try immediately, then retry until GIS script loads (up to 5s)
    if (!_render()) {
      containerEl.textContent = "Loading Google Sign-In...";
      let attempts = 0;
      const interval = setInterval(() => {
        attempts++;
        if (_render()) {
          clearInterval(interval);
        } else if (attempts > 25) {
          clearInterval(interval);
          containerEl.textContent = "Google Sign-In unavailable. Try refreshing.";
        }
      }, 200);
    }
  }

  /**
   * Sign the user out. Clears auth state from localStorage.
   */
  function signOut() {
    if (isOAuthEnabled()) {
      localStorage.removeItem(STORAGE_KEY);
      if (typeof google !== "undefined" && google.accounts && google.accounts.id) {
        google.accounts.id.disableAutoSelect();
      }
    } else {
      sessionStorage.removeItem(PASSWORD_KEY);
    }
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
