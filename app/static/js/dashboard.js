// Dashboard JavaScript Module
// Handles chart rendering, map initialization, and filter updates

// Global state
let currentFilters = {
    start: '',
    end: '',
    types: [],
    area: ''
};

let map = null;
let heatLayer = null;
let pointsLayer = null;
let crimeMarkers = [];

// Chart instances
let typeChart = null;
let distributionChart = null;
let timeChart = null;
let currentTimePeriod = 'monthly';

// Debounce utility
function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

// Initialize the Leaflet map
function initMap() {
    // Center on Chicago
    const chicagoCenter = [41.8781, -87.6298];
    
    map = L.map('crimeMap').setView(chicagoCenter, 11);
    
    // Add OpenStreetMap tile layer
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        maxZoom: 19,
        attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
    }).addTo(map);
    
    // Initialize heat layer (will be populated later)
    heatLayer = null;
    pointsLayer = null;
    
    // Toggle heatmap button
    document.getElementById('toggle-heatmap').addEventListener('click', function() {
        if (heatLayer) {
            if (map.hasLayer(heatLayer)) {
                map.removeLayer(heatLayer);
                this.classList.remove('active');
            } else {
                heatLayer.addTo(map);
                this.classList.add('active');
            }
        }
    });
    
    // Toggle points button
    document.getElementById('toggle-points').addEventListener('click', function() {
        if (pointsLayer) {
            if (map.hasLayer(pointsLayer)) {
                map.removeLayer(pointsLayer);
                this.classList.remove('active');
            } else {
                pointsLayer.addTo(map);
                this.classList.add('active');
            }
        }
    });
}

// Fetch statistics from API
async function fetchStats(filters) {
    try {
        const params = new URLSearchParams();
        
        if (filters.start) params.append('start', filters.start);
        if (filters.end) params.append('end', filters.end);
        if (filters.types && filters.types.length > 0) {
            params.append('types', filters.types.join(','));
        }
        if (filters.area) params.append('area', filters.area);
        
        const response = await fetch(`/api/stats?${params.toString()}`);
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        const data = await response.json();
        updateCharts(data);
        updateSummaryStats(data);
        
        return data;
    } catch (error) {
        console.error('Error fetching stats:', error);
        showAlert('Failed to load statistics. Please try again.', 'danger');
        throw error;
    }
}

// Fetch heatmap data from API
async function fetchHeatmap(filters) {
    try {
        const params = new URLSearchParams();
        
        if (filters.start) params.append('start', filters.start);
        if (filters.end) params.append('end', filters.end);
        if (filters.types && filters.types.length > 0) {
            params.append('types', filters.types.join(','));
        }
        if (filters.area) params.append('area', filters.area);
        
        const response = await fetch(`/api/heatmap?${params.toString()}`);
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        const geojson = await response.json();
        updateHeatmap(geojson);
        
        return geojson;
    } catch (error) {
        console.error('Error fetching heatmap:', error);
        showAlert('Failed to load map data. Please try again.', 'danger');
        throw error;
    }
}

// Update heatmap layer
function updateHeatmap(geojson) {
    // Remove existing layers
    if (heatLayer) {
        map.removeLayer(heatLayer);
        heatLayer = null;
    }
    if (pointsLayer) {
        map.removeLayer(pointsLayer);
        pointsLayer = null;
    }
    
    // Clear existing markers
    crimeMarkers.forEach(marker => map.removeLayer(marker));
    crimeMarkers = [];
    
    if (!geojson.features || geojson.features.length === 0) {
        return;
    }
    
    // Prepare heatmap data
    const heatData = [];
    
    // Create a marker for each crime point
    geojson.features.forEach(feature => {
        const coords = feature.geometry.coordinates;
        const lat = coords[1];
        const lng = coords[0];
        const props = feature.properties;
        
        // Add to heat data
        heatData.push([lat, lng, 1]);
        
        // Create marker
        const marker = L.circleMarker([lat, lng], {
            radius: 5,
            fillColor: getCrimeColor(props.type),
            color: '#fff',
            weight: 1,
            opacity: 0.7,
            fillOpacity: 0.7
        });
        
        // Add popup with crime info
        marker.bindPopup(`
            <strong>${props.type}</strong><br>
            Date: ${props.date || 'N/A'}
        `);
        
        crimeMarkers.push(marker);
    });
    
    // Create heat layer
    heatLayer = L.heatLayer(heatData, {
        radius: 25,
        blur: 15,
        maxZoom: 17,
        gradient: {
            0.2: 'blue',
            0.4: 'cyan',
            0.6: 'lime',
            0.8: 'yellow',
            1.0: 'red'
        }
    });
    
    // Create points layer (clustered markers)
    pointsLayer = L.layerGroup(crimeMarkers);
    
    // Add heatmap to map by default
    heatLayer.addTo(map);
    
    // Auto-fit bounds if we have points
    if (crimeMarkers.length > 0) {
        const group = L.featureGroup(crimeMarkers);
        map.fitBounds(group.getBounds().pad(0.1));
    }
}

// Get color based on crime type (case-insensitive)
function getCrimeColor(crimeType) {
    const colors = {
        'THEFT': '#e74c3c',
        'BATTERY': '#3498db',
        'CRIMINAL DAMAGE': '#9b59b6',
        'NARCOTICS': '#f39c12',
        'ASSAULT': '#1abc9c',
        'ROBBERY': '#e67e22',
        'MOTOR VEHICLE THEFT': '#34495e',
        'BURGLARY': '#16a085',
        'HOMICIDE': '#c0392b',
        'OTHER': '#95a5a6'
    };
    return colors[crimeType.toUpperCase()] || '#95a5a6';
}

// Update all Chart.js charts
function updateCharts(data) {
    updateTypeChart(data.by_type);
    updateDistributionChart(data.by_type);
    updateTimeChart(data.by_month);
}

// Update bar chart (crime frequency by type)
function updateTypeChart(byType) {
    const ctx = document.getElementById('typeChart').getContext('2d');
    
    const labels = byType.map(item => item.type);
    const values = byType.map(item => item.count);
    const colors = labels.map(label => getCrimeColor(label));
    
    if (typeChart) {
        typeChart.destroy();
    }
    
    typeChart = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: labels,
            datasets: [{
                label: 'Number of Crimes',
                data: values,
                backgroundColor: colors,
                borderColor: colors.map(c => c),
                borderWidth: 1
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            indexAxis: 'y',
            plugins: {
                legend: {
                    display: false
                },
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            return `${context.raw} crimes`;
                        }
                    }
                }
            },
            scales: {
                x: {
                    beginAtZero: true,
                    ticks: {
                        stepSize: 1
                    }
                }
            }
        }
    });
}

// Update pie/donut chart (crime type distribution)
function updateDistributionChart(byType) {
    const ctx = document.getElementById('distributionChart').getContext('2d');
    
    const labels = byType.map(item => item.type);
    const values = byType.map(item => item.count);
    const colors = labels.map(label => getCrimeColor(label));
    
    if (distributionChart) {
        distributionChart.destroy();
    }
    
    distributionChart = new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels: labels,
            datasets: [{
                data: values,
                backgroundColor: colors,
                borderColor: '#fff',
                borderWidth: 2
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: 'right',
                    labels: {
                        boxWidth: 12,
                        padding: 10
                    }
                },
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            const total = context.dataset.data.reduce((a, b) => a + b, 0);
                            const percentage = ((context.raw / total) * 100).toFixed(1);
                            return `${context.label}: ${context.raw} (${percentage}%)`;
                        }
                    }
                }
            }
        }
    });
}

// Update line chart (crimes over time) using Plotly.js
function updateTimeChart(byMonth) {
    // Process data based on current time period
    let labels = [];
    let values = [];
    
    if (currentTimePeriod === 'daily' || currentTimePeriod === 'monthly') {
        // Use monthly data directly
        labels = byMonth.map(item => item.month);
        values = byMonth.map(item => item.count);
    } else if (currentTimePeriod === 'yearly') {
        // Aggregate to yearly
        const yearlyData = {};
        byMonth.forEach(item => {
            const year = item.month.substring(0, 4);
            yearlyData[year] = (yearlyData[year] || 0) + item.count;
        });
        labels = Object.keys(yearlyData).sort();
        values = Object.values(yearlyData);
    }
    
    const trace = {
        x: labels,
        y: values,
        mode: 'lines+markers',
        type: 'scatter',
        fill: 'tozeroy',
        line: { color: '#3498db', width: 2 },
        marker: { size: 6, color: '#3498db' },
        hovertemplate: '<b>%{x}</b><br>%{y} crimes<extra></extra>'
    };
    
    const layout = {
        margin: { t: 20, r: 20, b: 60, l: 50 },
        xaxis: { 
            title: '',
            tickangle: -45,
            automargin: true
        },
        yaxis: { 
            title: 'Crimes',
            zeroline: true
        },
        paper_bgcolor: 'rgba(0,0,0,0)',
        plot_bgcolor: 'rgba(0,0,0,0)',
        hovermode: 'x unified',
        showlegend: false
    };
    
    const config = {
        responsive: true,
        displayModeBar: false
    };
    
    Plotly.newPlot('timeChart', [trace], layout, config);
}

// Update summary statistics cards
function updateSummaryStats(data) {
    // Total crimes
    document.getElementById('stat-total').textContent = data.total_crimes.toLocaleString();
    
    // Top crime type
    if (data.by_type && data.by_type.length > 0) {
        document.getElementById('stat-top-type').textContent = data.by_type[0].type;
    }
    
    // Top district
    if (data.by_district && data.by_district.length > 0) {
        document.getElementById('stat-top-district').textContent = data.by_district[0].district || 'N/A';
    }
    
    // Date range
    const start = currentFilters.start || 'All time';
    const end = currentFilters.end ? ` - ${currentFilters.end}` : '';
    document.getElementById('stat-date-range').textContent = start + end;
}

// Show alert message in UI
function showAlert(message, type = 'info') {
    const alertDiv = document.createElement('div');
    alertDiv.className = `alert alert-${type} alert-dismissible fade show`;
    alertDiv.setAttribute('role', 'alert');
    alertDiv.innerHTML = `
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `;
    
    const container = document.querySelector('main');
    container.insertBefore(alertDiv, container.firstChild);
    
    // Auto-dismiss after 5 seconds
    setTimeout(() => {
        alertDiv.remove();
    }, 5000);
}

// Get current filter values from form
function getFilterValues() {
    // Get date values
    const startInput = document.getElementById('filter-start');
    const endInput = document.getElementById('filter-end');
    
    // Get selected crime types
    const typesSelect = document.getElementById('filter-types');
    const selectedTypes = Array.from(typesSelect.selectedOptions).map(opt => opt.value);
    
    // Get selected area
    const areaSelect = document.getElementById('filter-area');
    const selectedArea = areaSelect.value;
    
    return {
        start: startInput.value,
        end: endInput.value,
        types: selectedTypes,
        area: selectedArea
    };
}

// Apply filters and update dashboard
async function applyFilters() {
    currentFilters = getFilterValues();
    
    try {
        await Promise.all([
            fetchStats(currentFilters),
            fetchHeatmap(currentFilters)
        ]);
    } catch (error) {
        console.error('Error applying filters:', error);
    }
}

// Reset all filters
function resetFilters() {
    // Clear date inputs
    document.getElementById('filter-start').value = '';
    document.getElementById('filter-end').value = '';
    
    // Clear type selection
    const typesSelect = document.getElementById('filter-types');
    Array.from(typesSelect.options).forEach(opt => opt.selected = false);
    
    // Clear area selection
    document.getElementById('filter-area').value = '';
    
    // Apply empty filters
    applyFilters();
}

// Change time period for line chart
function changeTimePeriod(period) {
    currentTimePeriod = period;
    
    // Update toggle button states
    document.querySelectorAll('.time-toggle').forEach(btn => {
        btn.classList.remove('active');
        if (btn.dataset.period === period) {
            btn.classList.add('active');
        }
    });
    
    // Re-fetch stats with new period
    // The by_month data is already fetched, so we just need to re-render the chart
    // This is handled by re-calling updateTimeChart with stored data
    fetchStats(currentFilters);
}

// Debounced apply filters
const debouncedApplyFilters = debounce(applyFilters, 300);

// Initialize dashboard when DOM is ready
document.addEventListener('DOMContentLoaded', function() {
    // Initialize map
    initMap();
    
    // Apply filters button
    document.getElementById('apply-filters').addEventListener('click', applyFilters);
    
    // Reset filters button
    document.getElementById('reset-filters').addEventListener('click', resetFilters);
    
    // Time period toggle buttons
    document.querySelectorAll('.time-toggle').forEach(btn => {
        btn.addEventListener('click', function() {
            changeTimePeriod(this.dataset.period);
        });
    });
    
    // Auto-apply on filter change (debounced)
    document.getElementById('filter-start').addEventListener('change', debouncedApplyFilters);
    document.getElementById('filter-end').addEventListener('change', debouncedApplyFilters);
    document.getElementById('filter-types').addEventListener('change', debouncedApplyFilters);
    document.getElementById('filter-area').addEventListener('change', debouncedApplyFilters);
    
    // Load initial data
    applyFilters();
});