// Search & Filter Module - Frontend JavaScript

// State management
let currentPage = 1;
let currentPerPage = 25;
let currentSort = { field: 'date', direction: 'desc' };
let currentFilters = {
    query: '',
    area: '',
    type: '',
    start: '',
    end: '',
    time_of_day: ''
};
let debounceTimer = null;
let typeChart = null;
let timeChart = null;

// Initialize on page load
document.addEventListener('DOMContentLoaded', function() {
    initializeDropdowns();
    initializeEventListeners();
    // Initial search
    searchCrimes(1);
});

// Populate dropdown options from API
async function initializeDropdowns() {
    try {
        // Fetch distinct areas (districts)
        const areasResponse = await fetch('/api/crimes/areas');
        if (areasResponse.ok) {
            const areasData = await areasResponse.json();
            populateDropdown('filterArea', areasData.areas);
        }

        // Fetch distinct crime types
        const typesResponse = await fetch('/api/crimes/types');
        if (typesResponse.ok) {
            const typesData = await typesResponse.json();
            populateDropdown('filterType', typesData.types);
        }
    } catch (error) {
        console.error('Error loading dropdown options:', error);
    }
}

// Populate a select dropdown with options
function populateDropdown(elementId, options) {
    const select = document.getElementById(elementId);
    if (!select) return;

    // Clear existing options except first (All/placeholder)
    while (select.options.length > 1) {
        select.remove(1);
    }

    // Add new options
    options.forEach(function(option) {
        const opt = document.createElement('option');
        opt.value = option;
        opt.textContent = option;
        select.appendChild(opt);
    });
}

// Initialize all event listeners
function initializeEventListeners() {
    // Search form submit
    const searchForm = document.getElementById('searchForm');
    if (searchForm) {
        searchForm.addEventListener('submit', function(e) {
            e.preventDefault();
            updateFiltersFromForm();
            searchCrimes(1);
        });
    }

    // Clear filters button
    const clearBtn = document.getElementById('clearFilters');
    if (clearBtn) {
        clearBtn.addEventListener('click', clearAllFilters);
    }

    // Filter changes with debounce (for automatic search)
    const filterInputs = ['searchQuery', 'filterArea', 'filterType', 'filterStart', 'filterEnd', 'filterTimeOfDay'];
    filterInputs.forEach(function(inputId) {
        const input = document.getElementById(inputId);
        if (input) {
            input.addEventListener('change', function() {
                updateFiltersFromForm();
                debouncedSearch();
            });
            // Also trigger on input for text fields
            if (inputId === 'searchQuery') {
                input.addEventListener('input', function() {
                    updateFiltersFromForm();
                    debouncedSearch();
                });
            }
        }
    });

    // Per page selection
    const perPageSelect = document.getElementById('perPageSelect');
    if (perPageSelect) {
        perPageSelect.addEventListener('change', function() {
            currentPerPage = parseInt(this.value, 10);
            searchCrimes(1);
        });
    }

    // Sort column clicks
    const sortHeaders = document.querySelectorAll('th[data-sort]');
    sortHeaders.forEach(function(th) {
        th.addEventListener('click', function() {
            const field = this.dataset.sort;
            const currentDir = currentSort.field === field ? currentSort.direction : 'desc';
            const newDir = currentDir === 'asc' ? 'desc' : 'asc';
            currentSort = { field: field, direction: newDir };
            updateSortIcons(field, newDir);
            searchCrimes(currentPage);
        });
    });

    // Pagination clicks (delegated)
    document.getElementById('paginationList').addEventListener('click', function(e) {
        const link = e.target.closest('.page-link');
        if (link && !link.parentElement.classList.contains('disabled') && !link.parentElement.classList.contains('active')) {
            const page = link.dataset.page;
            if (page) {
                searchCrimes(parseInt(page, 10));
            }
        }
    });
}

// Update filters from form inputs
function updateFiltersFromForm() {
    currentFilters = {
        query: document.getElementById('searchQuery')?.value || '',
        area: document.getElementById('filterArea')?.value || '',
        type: document.getElementById('filterType')?.value || '',
        start: document.getElementById('filterStart')?.value || '',
        end: document.getElementById('filterEnd')?.value || '',
        time_of_day: document.getElementById('filterTimeOfDay')?.value || ''
    };
}

// Debounced search (300ms delay)
function debouncedSearch() {
    if (debounceTimer) {
        clearTimeout(debounceTimer);
    }
    debounceTimer = setTimeout(function() {
        searchCrimes(1);
    }, 300);
}

// Clear all filters and reset
function clearAllFilters() {
    // Reset form inputs
    document.getElementById('searchQuery').value = '';
    document.getElementById('filterArea').value = '';
    document.getElementById('filterType').value = '';
    document.getElementById('filterStart').value = '';
    document.getElementById('filterEnd').value = '';
    document.getElementById('filterTimeOfDay').value = '';

    // Reset filters state
    currentFilters = {
        query: '',
        area: '',
        type: '',
        start: '',
        end: '',
        time_of_day: ''
    };

    // Reset sort
    currentSort = { field: 'date', direction: 'desc' };
    updateSortIcons('date', 'desc');

    // Trigger search
    searchCrimes(1);
}

// Main search function - fetches crimes from API
async function searchCrimes(page) {
    currentPage = page;

    // Show loading indicator
    showLoading(true);

    // Build query parameters
    const params = new URLSearchParams();
    params.append('page', page);
    params.append('per_page', currentPerPage);

    if (currentFilters.query) params.append('query', currentFilters.query);
    if (currentFilters.area) params.append('area', currentFilters.area);
    if (currentFilters.type) params.append('type', currentFilters.type);
    if (currentFilters.start) params.append('start', currentFilters.start);
    if (currentFilters.end) params.append('end', currentFilters.end);
    if (currentFilters.time_of_day) params.append('time_of_day', currentFilters.time_of_day);

    try {
        const response = await fetch('/api/crimes?' + params.toString());

        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.error || 'Search failed');
        }

        const data = await response.json();

        // Store items for client-side sorting
        window.currentItems = data.items;

        // Render results
        renderTable(data.items);
        renderPagination(data);
        updatePaginationInfo(data);
        renderMiniCharts(data.items);

        // Show results section
        document.getElementById('resultsSection').style.display = 'block';

        // Show/hide no results message
        if (data.total === 0) {
            document.getElementById('noResults').style.display = 'block';
            document.querySelector('.table-responsive').style.display = 'none';
        } else {
            document.getElementById('noResults').style.display = 'none';
            document.querySelector('.table-responsive').style.display = 'block';
        }

        // Show mini charts
        if (data.total > 0) {
            document.getElementById('miniChartsSection').style.display = 'flex';
        }

    } catch (error) {
        console.error('Search error:', error);
        alert('Error searching crimes: ' + error.message);
    } finally {
        showLoading(false);
    }
}

// Render table rows from crime items
function renderTable(items) {
    const tbody = document.getElementById('resultsBody');
    if (!tbody) return;

    tbody.innerHTML = '';

    if (!items || items.length === 0) {
        return;
    }

    // Sort items client-side if needed
    let sortedItems = [...items];
    if (currentSort.field) {
        sortedItems.sort(function(a, b) {
            let valA = a[currentSort.field];
            let valB = b[currentSort.field];

            // Handle null values
            if (valA === null || valA === undefined) valA = '';
            if (valB === null || valB === undefined) valB = '';

            // Compare based on sort direction
            if (valA < valB) return currentSort.direction === 'asc' ? -1 : 1;
            if (valA > valB) return currentSort.direction === 'asc' ? 1 : -1;
            return 0;
        });
    }

    sortedItems.forEach(function(crime) {
        const tr = document.createElement('tr');

        // Date
        const dateTd = document.createElement('td');
        dateTd.textContent = formatDate(crime.date);
        tr.appendChild(dateTd);

        // Time
        const timeTd = document.createElement('td');
        timeTd.textContent = formatTime(crime.time);
        tr.appendChild(timeTd);

        // Type with badge
        const typeTd = document.createElement('td');
        const typeBadge = document.createElement('span');
        typeBadge.className = 'badge bg-primary badge-type';
        typeBadge.textContent = crime.type || 'N/A';
        typeTd.appendChild(typeBadge);
        tr.appendChild(typeTd);

        // District
        const districtTd = document.createElement('td');
        districtTd.textContent = crime.district || 'N/A';
        tr.appendChild(districtTd);

        // Address
        const addressTd = document.createElement('td');
        addressTd.textContent = crime.address || 'N/A';
        addressTd.style.maxWidth = '200px';
        addressTd.style.overflow = 'hidden';
        addressTd.style.textOverflow = 'ellipsis';
        addressTd.style.whiteSpace = 'nowrap';
        tr.appendChild(addressTd);

        // Description
        const descTd = document.createElement('td');
        descTd.textContent = crime.description || 'N/A';
        descTd.style.maxWidth = '250px';
        descTd.style.overflow = 'hidden';
        descTd.style.textOverflow = 'ellipsis';
        descTd.style.whiteSpace = 'nowrap';
        descTd.title = crime.description || 'N/A'; // Show full text on hover
        tr.appendChild(descTd);

        // Latitude
        const latTd = document.createElement('td');
        latTd.textContent = crime.latitude !== null ? crime.latitude.toFixed(6) : 'N/A';
        tr.appendChild(latTd);

        // Longitude
        const lngTd = document.createElement('td');
        lngTd.textContent = crime.longitude !== null ? crime.longitude.toFixed(6) : 'N/A';
        tr.appendChild(lngTd);

        tbody.appendChild(tr);
    });
}

// Render pagination controls
function renderPagination(meta) {
    const paginationList = document.getElementById('paginationList');
    if (!paginationList) return;

    paginationList.innerHTML = '';

    if (meta.pages <= 0) {
        return;
    }

    const currentPage = meta.page;
    const totalPages = meta.pages;

    // Calculate page range to show (up to 5 pages around current)
    let startPage = Math.max(1, currentPage - 2);
    let endPage = Math.min(totalPages, currentPage + 2);

    // Adjust range to always show 5 pages when possible
    if (endPage - startPage < 4) {
        if (startPage === 1) {
            endPage = Math.min(totalPages, startPage + 4);
        } else if (endPage === totalPages) {
            startPage = Math.max(1, endPage - 4);
        }
    }

    // Previous button
    const prevLi = document.createElement('li');
    prevLi.className = 'page-item' + (meta.has_prev ? '' : ' disabled');
    const prevLink = document.createElement('a');
    prevLink.className = 'page-link';
    prevLink.href = '#';
    prevLink.dataset.page = currentPage - 1;
    prevLink.innerHTML = '&laquo;';
    prevLi.appendChild(prevLink);
    paginationList.appendChild(prevLi);

    // First page + ellipsis if needed
    if (startPage > 1) {
        const firstLi = document.createElement('li');
        firstLi.className = 'page-item' + (currentPage === 1 ? ' active' : '');
        const firstLink = document.createElement('a');
        firstLink.className = 'page-link';
        firstLink.href = '#';
        firstLink.dataset.page = 1;
        firstLink.textContent = '1';
        firstLi.appendChild(firstLink);
        paginationList.appendChild(firstLi);

        if (startPage > 2) {
            const ellipsisLi = document.createElement('li');
            ellipsisLi.className = 'page-item disabled';
            ellipsisLi.innerHTML = '<span class="page-link">...</span>';
            paginationList.appendChild(ellipsisLi);
        }
    }

    // Page numbers
    for (let i = startPage; i <= endPage; i++) {
        const li = document.createElement('li');
        li.className = 'page-item' + (i === currentPage ? ' active' : '');
        const link = document.createElement('a');
        link.className = 'page-link';
        link.href = '#';
        link.dataset.page = i;
        link.textContent = i;
        li.appendChild(link);
        paginationList.appendChild(li);
    }

    // Last page + ellipsis if needed
    if (endPage < totalPages) {
        if (endPage < totalPages - 1) {
            const ellipsisLi = document.createElement('li');
            ellipsisLi.className = 'page-item disabled';
            ellipsisLi.innerHTML = '<span class="page-link">...</span>';
            paginationList.appendChild(ellipsisLi);
        }

        const lastLi = document.createElement('li');
        lastLi.className = 'page-item' + (currentPage === totalPages ? ' active' : '');
        const lastLink = document.createElement('a');
        lastLink.className = 'page-link';
        lastLink.href = '#';
        lastLink.dataset.page = totalPages;
        lastLink.textContent = totalPages;
        lastLi.appendChild(lastLink);
        paginationList.appendChild(lastLi);
    }

    // Next button
    const nextLi = document.createElement('li');
    nextLi.className = 'page-item' + (meta.has_next ? '' : ' disabled');
    const nextLink = document.createElement('a');
    nextLink.className = 'page-link';
    nextLink.href = '#';
    nextLink.dataset.page = currentPage + 1;
    nextLink.innerHTML = '&raquo;';
    nextLi.appendChild(nextLink);
    paginationList.appendChild(nextLi);
}

// Update pagination info text
function updatePaginationInfo(meta) {
    const infoEl = document.getElementById('paginationInfo');
    if (!infoEl) return;

    const start = (meta.page - 1) * meta.per_page + 1;
    const end = Math.min(meta.page * meta.per_page, meta.total);

    if (meta.total === 0) {
        infoEl.textContent = 'Showing 0 results';
    } else {
        infoEl.textContent = 'Showing ' + start + '-' + end + ' of ' + meta.total + ' results';
    }
}

// Update sort icons in table headers
function updateSortIcons(field, direction) {
    const headers = document.querySelectorAll('th[data-sort]');
    headers.forEach(function(th) {
        const icon = th.querySelector('.sort-icon');
        if (!icon) return;

        if (th.dataset.sort === field) {
            icon.className = 'sort-icon bi ' + (direction === 'asc' ? 'bi-chevron-up active' : 'bi-chevron-down active');
        } else {
            icon.className = 'sort-icon bi bi-chevron-expand';
        }
    });
}

// Show/hide loading indicator
function showLoading(show) {
    const spinner = document.getElementById('loadingSpinner');
    if (spinner) {
        spinner.classList.toggle('show', show);
    }
    const resultsSection = document.getElementById('resultsSection');
    if (resultsSection) {
        if (show) {
            resultsSection.style.opacity = '0.5';
        } else {
            resultsSection.style.opacity = '1';
        }
    }
}

// Format date string
function formatDate(dateStr) {
    if (!dateStr) return 'N/A';
    try {
        const date = new Date(dateStr);
        return date.toLocaleDateString('en-US', {
            year: 'numeric',
            month: 'short',
            day: 'numeric'
        });
    } catch (e) {
        return dateStr;
    }
}

// Format time string
function formatTime(timeStr) {
    if (!timeStr) return 'N/A';
    try {
        // Handle ISO time format (HH:MM:SS)
        const parts = timeStr.split(':');
        if (parts.length >= 2) {
            const hours = parseInt(parts[0], 10);
            const minutes = parseInt(parts[1], 10);
            const ampm = hours >= 12 ? 'PM' : 'AM';
            const hour12 = hours % 12 || 12;
            return hour12 + ':' + (minutes < 10 ? '0' : '') + minutes + ' ' + ampm;
        }
        return timeStr;
    } catch (e) {
        return timeStr;
    }
}

// Render mini charts using Chart.js
function renderMiniCharts(items) {
    if (!items || items.length === 0) {
        document.getElementById('miniChartsSection').style.display = 'none';
        return;
    }

    // Aggregate data by type
    const typeCounts = {};
    const dateCounts = {};

    items.forEach(function(crime) {
        // Count by type
        const type = crime.type || 'Unknown';
        typeCounts[type] = (typeCounts[type] || 0) + 1;

        // Count by date
        const date = crime.date || 'Unknown';
        if (!dateCounts[date]) {
            dateCounts[date] = 0;
        }
        dateCounts[date]++;
    });

    // Get top 8 types for the chart
    const sortedTypes = Object.entries(typeCounts)
        .sort(function(a, b) { return b[1] - a[1]; })
        .slice(0, 8);

    // Get dates sorted
    const sortedDates = Object.keys(dateCounts).sort();

    // Prepare chart data
    const typeLabels = sortedTypes.map(function(entry) { return entry[0]; });
    const typeData = sortedTypes.map(function(entry) { return entry[1]; });
    const timeLabels = sortedDates.map(function(d) { return formatDate(d); });
    const timeData = sortedDates.map(function(d) { return dateCounts[d]; });

    // Color palette
    const colors = [
        'rgba(255, 99, 132, 0.7)',
        'rgba(54, 162, 235, 0.7)',
        'rgba(255, 206, 86, 0.7)',
        'rgba(75, 192, 192, 0.7)',
        'rgba(153, 102, 255, 0.7)',
        'rgba(255, 159, 64, 0.7)',
        'rgba(199, 199, 199, 0.7)',
        'rgba(83, 102, 255, 0.7)'
    ];

    // Render Type Chart
    const typeCanvas = document.getElementById('typeChart');
    if (typeCanvas) {
        if (typeChart) {
            typeChart.destroy();
        }
        typeChart = new Chart(typeCanvas, {
            type: 'bar',
            data: {
                labels: typeLabels,
                datasets: [{
                    label: 'Count',
                    data: typeData,
                    backgroundColor: colors.slice(0, typeLabels.length),
                    borderColor: colors.slice(0, typeLabels.length).map(function(c) { return c.replace('0.7', '1'); }),
                    borderWidth: 1
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        display: false
                    }
                },
                scales: {
                    y: {
                        beginAtZero: true,
                        ticks: {
                            stepSize: 1
                        }
                    },
                    x: {
                        ticks: {
                            maxRotation: 45,
                            minRotation: 45
                        }
                    }
                }
            }
        });
    }

    // Render Time Chart
    const timeCanvas = document.getElementById('timeChart');
    if (timeCanvas) {
        if (timeChart) {
            timeChart.destroy();
        }
        timeChart = new Chart(timeCanvas, {
            type: 'line',
            data: {
                labels: timeLabels,
                datasets: [{
                    label: 'Crimes',
                    data: timeData,
                    fill: true,
                    backgroundColor: 'rgba(54, 162, 235, 0.2)',
                    borderColor: 'rgba(54, 162, 235, 1)',
                    borderWidth: 2,
                    tension: 0.4,
                    pointRadius: 3,
                    pointHoverRadius: 5
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        display: false
                    }
                },
                scales: {
                    y: {
                        beginAtZero: true,
                        ticks: {
                            stepSize: 1
                        }
                    },
                    x: {
                        ticks: {
                            maxRotation: 45,
                            minRotation: 45
                        }
                    }
                }
            }
        });
    }
}