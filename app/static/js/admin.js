// Admin Panel JavaScript
// Handles user management, dataset upload, and model retraining

let currentUserPage = 1;
let currentPerPage = 25;
let currentJobId = null;
let statusPollInterval = null;

// DOM Elements
const elements = {
    // Stats
    statUsers: document.getElementById('statUsers'),
    statCrimes: document.getElementById('statCrimes'),
    statPredictions: document.getElementById('statPredictions'),
    statReports: document.getElementById('statReports'),

    // Users table
    usersTableBody: document.getElementById('usersTableBody'),
    usersPagination: document.getElementById('usersPagination'),
    paginationInfo: document.getElementById('paginationInfo'),
    perPageSelect: document.getElementById('perPageSelect'),

    // Upload
    dropZone: document.getElementById('dropZone'),
    fileInput: document.getElementById('fileInput'),
    browseBtn: document.getElementById('browseBtn'),
    fileNameDisplay: document.getElementById('fileNameDisplay'),
    uploadForm: document.getElementById('uploadForm'),
    uploadBtn: document.getElementById('uploadBtn'),
    uploadProgress: document.getElementById('uploadProgress'),
    uploadResult: document.getElementById('uploadResult'),
    uploadResultText: document.getElementById('uploadResultText'),

    // Retrain
    retrainBtn: document.getElementById('retrainBtn'),
    trainingStatusContainer: document.getElementById('trainingStatusContainer'),
    trainingStatusBox: document.getElementById('trainingStatusBox'),
    trainingSpinner: document.getElementById('trainingSpinner'),
    trainingStatusTitle: document.getElementById('trainingStatusTitle'),
    trainingStatusDetails: document.getElementById('trainingStatusDetails'),
    trainingResultContainer: document.getElementById('trainingResultContainer'),
    trainingResultText: document.getElementById('trainingResultText')
};

// Check if user is admin before showing page
async function checkAdminAccess() {
    try {
        const result = await verifyToken();
        if (!result.ok || !result.data || result.data.role !== 'admin') {
            showToast('Access denied. Admin privileges required.', 'danger');
            setTimeout(() => {
                window.location.href = '/dashboard';
            }, 2000);
            return false;
        }
        return true;
    } catch (error) {
        showToast('Authentication error. Please login again.', 'danger');
        setTimeout(() => {
            window.location.href = '/auth/login';
        }, 2000);
        return false;
    }
}

// Load admin statistics
async function loadStats() {
    try {
        const token = getAccessToken();
        const response = await fetch('/api/admin/stats', {
            headers: {
                'Authorization': `Bearer ${token}`
            }
        });

        if (response.status === 403) {
            showToast('Admin access required', 'danger');
            return;
        }

        if (!response.ok) {
            throw new Error('Failed to load stats');
        }

        const data = await response.json();

        // Update stat cards with animation
        animateCounter(elements.statUsers, data.users);
        animateCounter(elements.statCrimes, data.crimes);
        animateCounter(elements.statPredictions, data.predictions);
        animateCounter(elements.statReports, data.reports);

    } catch (error) {
        console.error('Error loading stats:', error);
        elements.statUsers.textContent = '!';
        elements.statCrimes.textContent = '!';
        elements.statPredictions.textContent = '!';
        elements.statReports.textContent = '!';
    }
}

// Animate counter
function animateCounter(element, target) {
    const duration = 500;
    const start = 0;
    const startTime = performance.now();

    function update(currentTime) {
        const elapsed = currentTime - startTime;
        const progress = Math.min(elapsed / duration, 1);
        const current = Math.floor(start + (target - start) * progress);
        element.textContent = current.toLocaleString();

        if (progress < 1) {
            requestAnimationFrame(update);
        }
    }

    requestAnimationFrame(update);
}

// Load users with pagination
async function loadUsers(page = 1) {
    currentUserPage = page;

    try {
        const token = getAccessToken();
        const response = await fetch(`/admin/users?page=${page}&per_page=${currentPerPage}`, {
            headers: {
                'Authorization': `Bearer ${token}`
            }
        });

        if (response.status === 403) {
            showToast('Admin access required', 'danger');
            return;
        }

        if (!response.ok) {
            throw new Error('Failed to load users');
        }

        const data = await response.json();
        renderUsersTable(data.users);
        renderPagination(data.page, data.pages, data.total);

    } catch (error) {
        console.error('Error loading users:', error);
        elements.usersTableBody.innerHTML = `
            <tr>
                <td colspan="6" class="text-center text-danger py-4">
                    <i class="bi bi-exclamation-triangle me-2"></i>Failed to load users
                </td>
            </tr>
        `;
    }
}

// Render users table
function renderUsersTable(users) {
    if (users.length === 0) {
        elements.usersTableBody.innerHTML = `
            <tr>
                <td colspan="6" class="text-center text-muted py-4">
                    No users found
                </td>
            </tr>
        `;
        return;
    }

    const currentUserId = getCurrentUserId();
    const rows = users.map(user => {
        const isSelf = user.id === currentUserId;
        const roleOptions = `
            <select class="form-select form-select-sm role-select" 
                    data-user-id="${user.id}" 
                    ${isSelf ? 'disabled' : ''}
                    style="width: auto;">
                <option value="viewer" ${user.role === 'viewer' ? 'selected' : ''}>Viewer</option>
                <option value="admin" ${user.role === 'admin' ? 'selected' : ''}>Admin</option>
            </select>
        `;

        const deleteBtn = isSelf
            ? `<button class="btn btn-outline-secondary btn-sm" disabled title="Cannot delete yourself">
                <i class="bi bi-trash"></i>
               </button>`
            : `<button class="btn btn-outline-danger btn-sm delete-user-btn" 
                data-user-id="${user.id}" 
                title="Delete user">
                <i class="bi bi-trash"></i>
               </button>`;

        return `
            <tr>
                <td>${user.id}</td>
                <td><strong>${escapeHtml(user.username)}</strong></td>
                <td>${escapeHtml(user.email)}</td>
                <td>${roleOptions}</td>
                <td>${formatDate(user.created_at)}</td>
                <td>${deleteBtn}</td>
            </tr>
        `;
    }).join('');

    elements.usersTableBody.innerHTML = rows;

    // Attach event listeners
    attachRoleChangeListeners();
    attachDeleteListeners();
}

// Attach role change listeners
function attachRoleChangeListeners() {
    document.querySelectorAll('.role-select').forEach(select => {
        select.addEventListener('change', async function() {
            const userId = parseInt(this.dataset.userId);
            const newRole = this.value;

            try {
                await updateUserRole(userId, newRole);
            } catch (error) {
                // Revert on error
                this.value = this.value === 'admin' ? 'viewer' : 'admin';
            }
        });
    });
}

// Attach delete listeners
function attachDeleteListeners() {
    document.querySelectorAll('.delete-user-btn').forEach(btn => {
        btn.addEventListener('click', function() {
            const userId = parseInt(this.dataset.userId);
            if (confirm('Are you sure you want to delete this user? This action cannot be undone.')) {
                deleteUser(userId);
            }
        });
    });
}

// Render pagination
function renderPagination(currentPage, totalPages, totalItems) {
    elements.paginationInfo.textContent = `Page ${currentPage} of ${totalPages} (${totalItems} total)`;

    let paginationHtml = `
        <li class="page-item ${currentPage <= 1 ? 'disabled' : ''}">
            <a class="page-link" href="#" data-page="${currentPage - 1}">Previous</a>
        </li>
    `;

    // Page numbers
    const maxPages = 5;
    let startPage = Math.max(1, currentPage - Math.floor(maxPages / 2));
    let endPage = Math.min(totalPages, startPage + maxPages - 1);

    if (endPage - startPage < maxPages - 1) {
        startPage = Math.max(1, endPage - maxPages + 1);
    }

    for (let i = startPage; i <= endPage; i++) {
        paginationHtml += `
            <li class="page-item ${i === currentPage ? 'active' : ''}">
                <a class="page-link" href="#" data-page="${i}">${i}</a>
            </li>
        `;
    }

    paginationHtml += `
        <li class="page-item ${currentPage >= totalPages ? 'disabled' : ''}">
            <a class="page-link" href="#" data-page="${currentPage + 1}">Next</a>
        </li>
    `;

    elements.usersPagination.innerHTML = paginationHtml;

    // Attach pagination listeners
    document.querySelectorAll('.page-link').forEach(link => {
        link.addEventListener('click', function(e) {
            e.preventDefault();
            const page = parseInt(this.dataset.page);
            if (!isNaN(page)) {
                loadUsers(page);
            }
        });
    });
}

// Update user role
async function updateUserRole(userId, role) {
    try {
        const token = getAccessToken();
        const response = await fetch(`/admin/users/${userId}/role`, {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${token}`
            },
            body: JSON.stringify({ role: role })
        });

        const data = await response.json();

        if (!response.ok) {
            showToast(data.error || 'Failed to update role', 'danger');
            // Refresh to get actual state
            loadUsers(currentUserPage);
            return;
        }

        showToast(`User role updated to ${role}`, 'success');

    } catch (error) {
        console.error('Error updating role:', error);
        showToast('Failed to update user role', 'danger');
        loadUsers(currentUserPage);
    }
}

// Delete user
async function deleteUser(userId) {
    try {
        const token = getAccessToken();
        const response = await fetch(`/admin/users/${userId}`, {
            method: 'DELETE',
            headers: {
                'Authorization': `Bearer ${token}`
            }
        });

        const data = await response.json();

        if (!response.ok) {
            showToast(data.error || 'Failed to delete user', 'danger');
            return;
        }

        showToast('User deleted successfully', 'success');
        loadUsers(currentUserPage);
        loadStats(); // Refresh stats

    } catch (error) {
        console.error('Error deleting user:', error);
        showToast('Failed to delete user', 'danger');
    }
}

// Upload dataset
async function uploadDataset(formData) {
    try {
        // Show progress
        elements.uploadProgress.classList.remove('d-none');
        elements.uploadBtn.disabled = true;
        elements.uploadResult.classList.add('d-none');

        const token = getAccessToken();
        const response = await fetch('/admin/upload', {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${token}`
            },
            body: formData
        });

        const data = await response.json();

        elements.uploadProgress.classList.add('d-none');
        elements.uploadBtn.disabled = false;

        if (!response.ok) {
            showToast(data.error || 'Failed to upload dataset', 'danger');
            return;
        }

        // Show success result
        elements.uploadResultText.textContent = `${data.records_inserted} records inserted successfully!`;
        elements.uploadResult.classList.remove('d-none');
        elements.fileInput.value = '';
        elements.fileNameDisplay.textContent = 'No file selected';
        elements.uploadBtn.disabled = true;

        // Refresh stats
        loadStats();

        // Hide result after 5 seconds
        setTimeout(() => {
            elements.uploadResult.classList.add('d-none');
        }, 5000);

    } catch (error) {
        console.error('Error uploading dataset:', error);
        elements.uploadProgress.classList.add('d-none');
        elements.uploadBtn.disabled = false;
        showToast('Failed to upload dataset', 'danger');
    }
}

// Retrain models
async function retrainModels() {
    try {
        // Disable button and show status
        elements.retrainBtn.disabled = true;
        elements.trainingStatusContainer.classList.remove('d-none');
        elements.trainingResultContainer.classList.add('d-none');

        updateTrainingStatus('running', 'Training started...', 'Initializing models with current data');

        const token = getAccessToken();
        const response = await fetch('/admin/retrain', {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${token}`
            }
        });

        const data = await response.json();

        if (!response.ok) {
            throw new Error(data.error || 'Failed to start training');
        }

        currentJobId = data.job_id;
        updateTrainingStatus('running', 'Training in progress...', 'Training Random Forest, Linear Regression, and LSTM models');

        // Start polling status
        startStatusPolling();

    } catch (error) {
        console.error('Error starting training:', error);
        updateTrainingStatus('failed', 'Failed to start training', error.message);
        elements.retrainBtn.disabled = false;
    }
}

// Update training status display
function updateTrainingStatus(status, title, details) {
    elements.trainingStatusBox.className = `training-status ${status}`;

    if (status === 'running') {
        elements.trainingSpinner.classList.remove('d-none');
        elements.trainingSpinner.innerHTML = '<span class="visually-hidden">Loading...</span>';
    } else if (status === 'completed') {
        elements.trainingSpinner.className = 'spinner-border spinner-border-sm text-success me-3';
        elements.trainingSpinner.innerHTML = '<i class="bi bi-check-circle-fill"></i><span class="visually-hidden">Loading...</span>';
    } else if (status === 'failed') {
        elements.trainingSpinner.className = 'spinner-border spinner-border-sm text-danger me-3';
        elements.trainingSpinner.innerHTML = '<i class="bi bi-x-circle-fill"></i><span class="visually-hidden">Loading...</span>';
    }

    elements.trainingStatusTitle.textContent = title;
    elements.trainingStatusDetails.textContent = details;

    if (status !== 'running') {
        elements.retrainBtn.disabled = false;
        stopStatusPolling();
    }
}

// Start polling training status
function startStatusPolling() {
    if (statusPollInterval) {
        clearInterval(statusPollInterval);
    }

    statusPollInterval = setInterval(() => {
        checkTrainingStatus(currentJobId);
    }, 5000); // Poll every 5 seconds
}

// Stop polling training status
function stopStatusPolling() {
    if (statusPollInterval) {
        clearInterval(statusPollInterval);
        statusPollInterval = null;
    }
}

// Check training status
async function checkTrainingStatus(jobId) {
    try {
        const token = getAccessToken();
        const response = await fetch(`/admin/retrain/status/${jobId}`, {
            headers: {
                'Authorization': `Bearer ${token}`
            }
        });

        if (!response.ok) {
            throw new Error('Failed to get training status');
        }

        const data = await response.json();

        if (data.status === 'running') {
            updateTrainingStatus('running', 'Training in progress...',
                `Started at ${formatTime(data.started_at)}. Please wait...`);
        } else if (data.status === 'completed') {
            updateTrainingStatus('completed', 'Training completed successfully!',
                `Completed at ${formatTime(data.completed_at)}`);

            if (data.result) {
                elements.trainingResultContainer.classList.remove('d-none');
                elements.trainingResultText.textContent = JSON.stringify(data.result, null, 2);
            }
        } else if (data.status === 'failed') {
            updateTrainingStatus('failed', 'Training failed',
                data.error || 'An unknown error occurred during training');
        }

    } catch (error) {
        console.error('Error checking training status:', error);
    }
}

// Helper: Get current user ID from token
function getCurrentUserId() {
    const token = getAccessToken();
    if (!token) return null;

    try {
        const payload = JSON.parse(atob(token.split('.')[1]));
        return payload.sub || payload.identity;
    } catch {
        return null;
    }
}

// Helper: Escape HTML to prevent XSS
function escapeHtml(text) {
    if (!text) return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// Helper: Format date
function formatDate(dateString) {
    if (!dateString) return '-';
    const date = new Date(dateString);
    return date.toLocaleDateString('en-US', {
        year: 'numeric',
        month: 'short',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
    });
}

// Helper: Format time only
function formatTime(dateString) {
    if (!dateString) return '-';
    const date = new Date(dateString);
    return date.toLocaleTimeString('en-US', {
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit'
    });
}

// Helper: Show toast notification
function showToast(message, type = 'info') {
    const toastContainer = document.createElement('div');
    toastContainer.className = 'toast-container position-fixed top-0 end-0 p-3';
    toastContainer.style.zIndex = '1100';

    const toastId = `toast-${Date.now()}`;
    toastContainer.innerHTML = `
        <div id="${toastId}" class="toast align-items-center text-white bg-${type} border-0" role="alert">
            <div class="d-flex">
                <div class="toast-body">
                    ${escapeHtml(message)}
                </div>
                <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast"></button>
            </div>
        </div>
    `;

    document.body.appendChild(toastContainer);

    const toastEl = document.getElementById(toastId);
    const toast = new bootstrap.Toast(toastEl, { delay: 4000 });
    toast.show();

    toastEl.addEventListener('hidden.bs.toast', function() {
        toastContainer.remove();
    });
}

// Initialize on page load
document.addEventListener('DOMContentLoaded', async function() {
    // Check admin access
    const isAdmin = await checkAdminAccess();
    if (!isAdmin) return;

    // Load initial data
    loadStats();
    loadUsers(1);

    // Per page change handler
    elements.perPageSelect.addEventListener('change', function() {
        currentPerPage = parseInt(this.value);
        loadUsers(1);
    });

    // File input handlers
    elements.browseBtn.addEventListener('click', function() {
        elements.fileInput.click();
    });

    elements.fileInput.addEventListener('change', function() {
        if (this.files.length > 0) {
            elements.fileNameDisplay.textContent = this.files[0].name;
            elements.uploadBtn.disabled = false;
        } else {
            elements.fileNameDisplay.textContent = 'No file selected';
            elements.uploadBtn.disabled = true;
        }
    });

    // Drag and drop handlers
    elements.dropZone.addEventListener('click', function() {
        elements.fileInput.click();
    });

    elements.dropZone.addEventListener('dragover', function(e) {
        e.preventDefault();
        this.classList.add('dragover');
    });

    elements.dropZone.addEventListener('dragleave', function(e) {
        e.preventDefault();
        this.classList.remove('dragover');
    });

    elements.dropZone.addEventListener('drop', function(e) {
        e.preventDefault();
        this.classList.remove('dragover');

        if (e.dataTransfer.files.length > 0) {
            const file = e.dataTransfer.files[0];
            if (file.name.toLowerCase().endsWith('.csv')) {
                const dataTransfer = new DataTransfer();
                dataTransfer.items.add(file);
                elements.fileInput.files = dataTransfer.files;
                elements.fileNameDisplay.textContent = file.name;
                elements.uploadBtn.disabled = false;
            } else {
                showToast('Only CSV files are accepted', 'danger');
            }
        }
    });

    // Upload form handler
    elements.uploadForm.addEventListener('submit', function(e) {
        e.preventDefault();

        if (elements.fileInput.files.length === 0) {
            showToast('Please select a file to upload', 'warning');
            return;
        }

        const formData = new FormData();
        formData.append('file', elements.fileInput.files[0]);
        uploadDataset(formData);
    });

    // Retrain button handler
    elements.retrainBtn.addEventListener('click', function() {
        if (confirm('Are you sure you want to retrain all models? This may take several minutes.')) {
            retrainModels();
        }
    });
});