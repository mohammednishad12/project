/**
 * Authentication utilities for Crime Data System
 * Handles JWT token storage and API authentication
 */

const AUTH_TOKEN_KEY = 'access_token';
const REFRESH_TOKEN_KEY = 'refresh_token';

/**
 * Store JWT access token in localStorage
 * @param {string} token - JWT access token
 */
function setAccessToken(token) {
    localStorage.setItem(AUTH_TOKEN_KEY, token);
}

/**
 * Get JWT access token from localStorage
 * @returns {string|null} JWT access token or null
 */
function getAccessToken() {
    return localStorage.getItem(AUTH_TOKEN_KEY);
}

/**
 * Store refresh token in localStorage
 * @param {string} token - Refresh token
 */
function setRefreshToken(token) {
    localStorage.setItem(REFRESH_TOKEN_KEY, token);
}

/**
 * Get refresh token from localStorage
 * @returns {string|null} Refresh token or null
 */
function getRefreshToken() {
    return localStorage.getItem(REFRESH_TOKEN_KEY);
}

/**
 * Get Authorization headers with JWT token
 * @returns {Object} Headers object with Authorization header
 */
function getAuthHeaders() {
    const token = getAccessToken();
    const headers = {
        'Content-Type': 'application/json'
    };
    if (token) {
        headers['Authorization'] = 'Bearer ' + token;
    }
    return headers;
}

/**
 * Check if user is logged in (has valid access token)
 * @returns {boolean} True if logged in
 */
function isLoggedIn() {
    const token = getAccessToken();
    if (!token) return false;

    // Check token expiration if available
    try {
        const payload = JSON.parse(atob(token.split('.')[1]));
        if (payload.exp) {
            const currentTime = Math.floor(Date.now() / 1000);
            return payload.exp > currentTime;
        }
    } catch (e) {
        // If we can't parse token, assume it's valid
        // Server will validate on API call
    }

    return true;
}

/**
 * Clear all authentication data and log out
 */
function logout() {
    localStorage.removeItem(AUTH_TOKEN_KEY);
    localStorage.removeItem(REFRESH_TOKEN_KEY);
    window.location.href = '/auth/logout';
}

/**
 * Fetch with authentication - wraps fetch with auth header and token refresh
 * @param {string} url - URL to fetch
 * @param {Object} options - Fetch options
 * @returns {Promise<Response>} Fetch response
 */
async function fetchWithAuth(url, options = {}) {
    // Add auth headers
    const headers = getAuthHeaders();
    options.headers = { ...options.headers, ...headers };

    let response = await fetch(url, options);

    // If unauthorized (401), try to refresh token
    if (response.status === 401) {
        const refreshToken = getRefreshToken();

        if (refreshToken) {
            try {
                // Attempt to refresh the access token
                const refreshResponse = await fetch('/auth/refresh', {
                    method: 'POST',
                    headers: {
                        'Authorization': 'Bearer ' + refreshToken
                    }
                });

                if (refreshResponse.ok) {
                    const data = await refreshResponse.json();

                    // Store new access token
                    setAccessToken(data.access_token);

                    // Retry original request with new token
                    options.headers['Authorization'] = 'Bearer ' + data.access_token;
                    response = await fetch(url, options);
                } else {
                    // Refresh failed, clear tokens and redirect to login
                    logout();
                    throw new Error('Session expired');
                }
            } catch (error) {
                logout();
                throw error;
            }
        } else {
            // No refresh token, redirect to login
            window.location.href = '/auth/login?redirect=' + encodeURIComponent(window.location.pathname);
            throw new Error('Not authenticated');
        }
    }

    return response;
}

/**
 * Login user with username and password
 * @param {string} username - Username
 * @param {string} password - Password
 * @returns {Promise<Object>} Response data with tokens and user
 */
async function login(username, password) {
    const response = await fetch('/auth/login', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({ username, password })
    });

    const data = await response.json();

    if (response.ok && data.access_token) {
        setAccessToken(data.access_token);
        if (data.refresh_token) {
            setRefreshToken(data.refresh_token);
        }
    }

    return { ok: response.ok, status: response.status, data };
}

/**
 * Register a new user
 * @param {Object} userData - User registration data
 * @returns {Promise<Object>} Response data
 */
async function register(userData) {
    const response = await fetch('/auth/register', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify(userData)
    });

    const data = await response.json();
    return { ok: response.ok, status: response.status, data };
}

/**
 * Get current user info
 * @returns {Promise<Object>} User data
 */
async function getCurrentUser() {
    try {
        const response = await fetchWithAuth('/auth/me');
        const data = await response.json();
        return { ok: response.ok, status: response.status, data };
    } catch (error) {
        return { ok: false, status: 0, data: { error: error.message } };
    }
}

/**
 * Verify if token is valid
 * @returns {Promise<Object>} Verification result
 */
async function verifyToken() {
    try {
        const response = await fetchWithAuth('/auth/verify');
        const data = await response.json();
        return { ok: response.ok, status: response.status, data };
    } catch (error) {
        return { ok: false, status: 0, data: { error: error.message } };
    }
}

/**
 * Check if current user has admin role
 * @returns {Promise<boolean>} True if admin
 */
async function isAdmin() {
    const result = await verifyToken();
    return result.ok && result.data && result.data.role === 'admin';
}

/**
 * Redirect to login if not authenticated (for use in HTML)
 */
function requireAuth() {
    if (!isLoggedIn()) {
        window.location.href = '/auth/login?redirect=' + encodeURIComponent(window.location.pathname);
        return false;
    }
    return true;
}

/**
 * Redirect to dashboard if already logged in (for login/register pages)
 */
function redirectIfLoggedIn() {
    if (isLoggedIn()) {
        window.location.href = '/dashboard';
        return true;
    }
    return false;
}

// Export for module usage
if (typeof module !== 'undefined' && module.exports) {
    module.exports = {
        setAccessToken,
        getAccessToken,
        setRefreshToken,
        getRefreshToken,
        getAuthHeaders,
        isLoggedIn,
        logout,
        fetchWithAuth,
        login,
        register,
        getCurrentUser,
        verifyToken,
        isAdmin,
        requireAuth,
        redirectIfLoggedIn
    };
}