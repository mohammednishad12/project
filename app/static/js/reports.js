// Reports Page JavaScript

document.addEventListener('DOMContentLoaded', function() {
    // DOM Elements
    const reportForm = document.getElementById('reportForm');
    const previewSection = document.getElementById('previewSection');
    const downloadSection = document.getElementById('downloadSection');
    const loadingOverlay = document.getElementById('loadingOverlay');
    const errorAlert = document.getElementById('errorAlert');
    const crimeTypesContainer = document.getElementById('crimeTypesContainer');

    // Form Elements
    const regionSelect = document.getElementById('region');
    const startDateInput = document.getElementById('startDate');
    const endDateInput = document.getElementById('endDate');

    // Preview Elements
    const totalCrimesEl = document.getElementById('totalCrimes');
    const topCrimeTypeEl = document.getElementById('topCrimeType');
    const trendDirectionEl = document.getElementById('trendDirection');
    const dateRangeEl = document.getElementById('dateRange');
    const monthlyTableBody = document.getElementById('monthlyTableBody');
    const hotspotsList = document.getElementById('hotspotsList');
    
    // Download Buttons
    const downloadPdfBtn = document.getElementById('downloadPdfBtn');
    const downloadCsvBtn = document.getElementById('downloadCsvBtn');
    
    // Store current filters
    let currentFilters = {};

    // Load crime types dynamically on page load
    loadCrimeTypes();

    /**
     * Fetch crime types from API and build checkboxes
     */
    function loadCrimeTypes() {
        fetch('/api/crimes/types', { method: 'GET' })
            .then(function(response) {
                if (!response.ok) {
                    throw new Error('Failed to load crime types');
                }
                return response.json();
            })
            .then(function(data) {
                if (!data.types || data.types.length === 0) {
                    crimeTypesContainer.innerHTML = '<p class="text-muted">No crime types available</p>';
                    return;
                }
                buildCrimeTypeCheckboxes(data.types);
            })
            .catch(function(error) {
                console.error('Error loading crime types:', error);
                crimeTypesContainer.innerHTML = '<p class="text-muted">Unable to load crime types</p>';
            });
    }

    /**
     * Build crime type checkbox elements
     */
    function buildCrimeTypeCheckboxes(types) {
        crimeTypesContainer.innerHTML = '';
        types.forEach(function(type, index) {
            var wrapper = document.createElement('div');
            wrapper.className = 'col-md-3 col-6';

            var checkDiv = document.createElement('div');
            checkDiv.className = 'form-check';

            var input = document.createElement('input');
            input.className = 'form-check-input crime-type-checkbox';
            input.type = 'checkbox';
            input.value = type;
            input.id = 'type_' + (index + 1);

            var label = document.createElement('label');
            label.className = 'form-check-label';
            label.htmlFor = input.id;
            label.textContent = type;

            checkDiv.appendChild(input);
            checkDiv.appendChild(label);
            wrapper.appendChild(checkDiv);
            crimeTypesContainer.appendChild(wrapper);
        });
    }

    // Form Submit Handler
    reportForm.addEventListener('submit', function(e) {
        e.preventDefault();
        generatePreview();
    });
    
    // Download PDF Button Handler
    downloadPdfBtn.addEventListener('click', function() {
        downloadPDF();
    });
    
    // Download CSV Button Handler
    downloadCsvBtn.addEventListener('click', function() {
        downloadCSV();
    });
    
    /**
     * Collect form filters
     */
    function getFormFilters() {
        // Get selected crime types
        const selectedTypes = [];
        document.querySelectorAll('.crime-type-checkbox:checked').forEach(function(checkbox) {
            selectedTypes.push(checkbox.value);
        });
        
        return {
            region: regionSelect.value,
            start: startDateInput.value,
            end: endDateInput.value,
            types: selectedTypes.join(',')
        };
    }
    
    /**
     * Build query string from filters
     */
    function buildQueryString(filters) {
        const params = new URLSearchParams();
        
        if (filters.region) {
            params.append('region', filters.region);
        }
        if (filters.start) {
            params.append('start', filters.start);
        }
        if (filters.end) {
            params.append('end', filters.end);
        }
        if (filters.types) {
            params.append('types', filters.types);
        }
        
        return params.toString();
    }
    
    /**
     * Show loading overlay
     */
    function showLoading(message) {
        loadingOverlay.classList.add('active');
        if (message) {
            loadingOverlay.querySelector('.text-muted').textContent = message;
        }
    }
    
    /**
     * Hide loading overlay
     */
    function hideLoading() {
        loadingOverlay.classList.remove('active');
    }
    
    /**
     * Show error message
     */
    function showError(message) {
        errorAlert.textContent = message;
        errorAlert.style.display = 'block';
    }
    
    /**
     * Hide error message
     */
    function hideError() {
        errorAlert.style.display = 'none';
    }
    
    /**
     * Generate preview by fetching report summary
     */
    function generatePreview() {
        hideError();
        hideError(); // Reset error display
        
        currentFilters = getFormFilters();
        const queryString = buildQueryString(currentFilters);
        
        showLoading('Generating report preview...');
        
        fetch('/api/report/preview?' + queryString, {
            method: 'GET',
            headers: {
                'Content-Type': 'application/json'
            }
        })
        .then(function(response) {
            if (!response.ok) {
                throw new Error('Failed to generate preview: ' + response.statusText);
            }
            return response.json();
        })
        .then(function(data) {
            hideLoading();
            
            if (data.error) {
                showError(data.error);
                return;
            }
            
            renderPreview(data);
            
            // Show preview and download sections
            previewSection.style.display = 'block';
            downloadSection.style.display = 'block';
        })
        .catch(function(error) {
            hideLoading();
            showError('Error generating preview: ' + error.message);
            console.error('Preview error:', error);
        });
    }
    
    /**
     * Render preview data in the UI
     */
    function renderPreview(data) {
        // Total crimes
        totalCrimesEl.textContent = data.total_crimes.toLocaleString();
        
        // Top crime type
        if (data.top_crime_types && data.top_crime_types.length > 0) {
            topCrimeTypeEl.textContent = data.top_crime_types[0].type;
        } else {
            topCrimeTypeEl.textContent = 'N/A';
        }
        
        // Trend direction
        let trendHtml = '';
        if (data.trend_direction === 'increasing') {
            trendHtml = '<span class="trend-up">↑ ' + data.trend_percent.toFixed(1) + '%</span>';
        } else if (data.trend_direction === 'decreasing') {
            trendHtml = '<span class="trend-down">↓ ' + data.trend_percent.toFixed(1) + '%</span>';
        } else {
            trendHtml = '<span class="trend-stable">→ Stable</span>';
        }
        trendDirectionEl.innerHTML = trendHtml;
        
        // Date range
        dateRangeEl.textContent = data.date_range || 'N/A';
        
        // Monthly breakdown table
        renderMonthlyTable(data.monthly_breakdown || []);
        
        // Hotspots list
        renderHotspots(data.hotspots || []);
    }
    
    /**
     * Render monthly breakdown table
     */
    function renderMonthlyTable(monthlyData) {
        monthlyTableBody.innerHTML = '';
        
        if (monthlyData.length === 0) {
            const tr = document.createElement('tr');
            tr.innerHTML = '<td colspan="4" class="text-center text-muted">No data available</td>';
            monthlyTableBody.appendChild(tr);
            return;
        }
        
        // Show top 6 rows
        const displayData = monthlyData.slice(0, 6);
        
        displayData.forEach(function(row) {
            const tr = document.createElement('tr');
            
            // Format change with color
            let changeHtml = row.change || '-';
            if (row.change) {
                if (row.change.startsWith('+')) {
                    changeHtml = '<span class="text-danger">' + row.change + '</span>';
                } else if (row.change.startsWith('-')) {
                    changeHtml = '<span class="text-success">' + row.change + '</span>';
                }
            }
            
            tr.innerHTML = 
                '<td>' + row.month + '</td>' +
                '<td>' + row.count.toLocaleString() + '</td>' +
                '<td>' + row.top_type + '</td>' +
                '<td>' + changeHtml + '</td>';
            
            monthlyTableBody.appendChild(tr);
        });
        
        // Show "more" row if there's more data
        if (monthlyData.length > 6) {
            const tr = document.createElement('tr');
            tr.innerHTML = '<td colspan="4" class="text-center text-muted">... and ' + (monthlyData.length - 6) + ' more months</td>';
            monthlyTableBody.appendChild(tr);
        }
    }
    
    /**
     * Render hotspots list
     */
    function renderHotspots(hotspots) {
        hotspotsList.innerHTML = '';
        
        if (hotspots.length === 0) {
            hotspotsList.innerHTML = '<p class="text-muted">No hotspot data available</p>';
            return;
        }
        
        hotspots.forEach(function(hotspot, index) {
            const div = document.createElement('div');
            div.className = 'hotspot-item';
            
            div.innerHTML = 
                '<div class="hotspot-rank">' + (index + 1) + '</div>' +
                '<div class="hotspot-info">' +
                    '<div class="hotspot-district">' + hotspot.district + '</div>' +
                    '<div class="hotspot-coords">Lat: ' + hotspot.avg_lat + ', Lng: ' + hotspot.avg_lng + '</div>' +
                '</div>' +
                '<div class="hotspot-count">' + hotspot.count.toLocaleString() + '</div>';
            
            hotspotsList.appendChild(div);
        });
    }
    
    /**
     * Download PDF report
     */
    function downloadPDF() {
        showLoading('Generating PDF report...');

        const queryString = buildQueryString(currentFilters);
        let response; // store for later scope

        fetch('/api/report/pdf?' + queryString, {
            method: 'GET'
        })
        .then(function(resp) {
            response = resp;
            if (!response.ok) {
                throw new Error('Failed to generate PDF: ' + response.statusText);
            }
            return response.blob();
        })
        .then(function(blob) {
            hideLoading();

            // Create download link
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;

            // Get filename from Content-Disposition header or generate one
            const contentDisposition = response.headers.get('Content-Disposition');
            let filename = 'crime_report.pdf';
            if (contentDisposition) {
                const filenameMatch = contentDisposition.match(/filename[^;=\n]*=((['"]).*?\2|[^;\n]*)/);
                if (filenameMatch && filenameMatch[1]) {
                    filename = filenameMatch[1].replace(/['"]/g, '');
                }
            }

            a.download = filename;
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            window.URL.revokeObjectURL(url);
        })
        .catch(function(error) {
            hideLoading();
            showError('Error downloading PDF: ' + error.message);
            console.error('PDF download error:', error);
        });
    }

    /**
     * Download CSV report
     */
    function downloadCSV() {
        showLoading('Generating CSV report...');

        const queryString = buildQueryString(currentFilters);
        let response; // store for later scope

        fetch('/api/report/csv?' + queryString, {
            method: 'GET'
        })
        .then(function(resp) {
            response = resp;
            if (!response.ok) {
                throw new Error('Failed to generate CSV: ' + response.statusText);
            }
            return response.blob();
        })
        .then(function(blob) {
            hideLoading();

            // Create download link
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;

            // Get filename from Content-Disposition header or generate one
            const contentDisposition = response.headers.get('Content-Disposition');
            let filename = 'crime_report.csv';
            if (contentDisposition) {
                const filenameMatch = contentDisposition.match(/filename[^;=\n]*=((['"]).*?\2|[^;\n]*)/);
                if (filenameMatch && filenameMatch[1]) {
                    filename = filenameMatch[1].replace(/['"]/g, '');
                }
            }

            a.download = filename;
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            window.URL.revokeObjectURL(url);
        })
        .catch(function(error) {
            hideLoading();
            showError('Error downloading CSV: ' + error.message);
            console.error('CSV download error:', error);
        });
    }
});