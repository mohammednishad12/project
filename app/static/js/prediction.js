/**
 * Crime Prediction Frontend JavaScript
 * 
 * Handles:
 * - Prediction form submission
 * - Location selection via map click
 * - Results display and chart rendering
 * - Hotspot map visualization
 */

// Global state
let locationMap = null;
let hotspotMap = null;
let selectedLocation = {
    lat: 28.61,
    lng: 77.21
};

// Initialize on DOM load
document.addEventListener('DOMContentLoaded', function() {
    initLocationMap();
    initHotspotMap();
    setDefaultDates();
    setupEventListeners();
});

/**
 * Initialize the location selection map
 */
function initLocationMap() {
    // Delhi center coordinates
    const delhiCenter = [28.61, 77.21];

    locationMap = L.map('locationMap').setView(delhiCenter, 11);

    // Add OpenStreetMap tiles
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: '&copy; OpenStreetMap contributors',
        maxZoom: 18
    }).addTo(locationMap);

    // Add click handler for location selection
    locationMap.on('click', function(e) {
        selectedLocation = {
            lat: e.latlng.lat,
            lng: e.latlng.lng
        };
        updateLocationInputs();
        addLocationMarker();
    });

    // Add initial marker
    addLocationMarker();
}

/**
 * Add or update marker on location map
 */
function addLocationMarker() {
    // Remove existing markers
    locationMap.eachLayer(function(layer) {
        if (layer instanceof L.Marker) {
            locationMap.removeLayer(layer);
        }
    });

    // Add new marker
    const marker = L.marker([selectedLocation.lat, selectedLocation.lng], {
        draggable: true
    }).addTo(locationMap);

    marker.bindPopup(
        `<strong>Selected Location</strong><br>` +
        `Lat: ${selectedLocation.lat.toFixed(4)}<br>` +
        `Lng: ${selectedLocation.lng.toFixed(4)}`
    ).openPopup();

    // Update inputs on drag
    marker.on('dragend', function(e) {
        const pos = e.target.getLatLng();
        selectedLocation = {
            lat: pos.lat,
            lng: pos.lng
        };
        updateLocationInputs();
    });
}

/**
 * Update location inputs from selected location
 */
function updateLocationInputs() {
    const latInput = document.getElementById('inputLat');
    const lngInput = document.getElementById('inputLng');

    if (latInput) latInput.value = selectedLocation.lat.toFixed(4);
    if (lngInput) lngInput.value = selectedLocation.lng.toFixed(4);
}

/**
 * Set default dates (today and 7 days from now)
 */
function setDefaultDates() {
    const today = new Date();
    const nextWeek = new Date();
    nextWeek.setDate(today.getDate() + 7);

    const formatDate = function(date) {
        return date.toISOString().split('T')[0];
    };

    const startInput = document.getElementById('inputStartDate');
    const endInput = document.getElementById('inputEndDate');

    if (startInput) startInput.value = formatDate(today);
    if (endInput) endInput.value = formatDate(nextWeek);
}

/**
 * Setup event listeners for form and inputs
 */
function setupEventListeners() {
    const form = document.getElementById('predictionForm');
    if (form) {
        form.addEventListener('submit', function(e) {
            e.preventDefault();
            runPrediction();
        });
    }

    // Update location from inputs
    const latInput = document.getElementById('inputLat');
    const lngInput = document.getElementById('inputLng');

    if (latInput) {
        latInput.addEventListener('change', function() {
            selectedLocation.lat = parseFloat(this.value) || 28.61;
            if (locationMap) {
                locationMap.eachLayer(function(layer) {
                    if (layer instanceof L.Marker) {
                        locationMap.removeLayer(layer);
                    }
                });
                L.marker([selectedLocation.lat, selectedLocation.lng], {draggable: true}).addTo(locationMap);
            }
        });
    }

    if (lngInput) {
        lngInput.addEventListener('change', function() {
            selectedLocation.lng = parseFloat(this.value) || 77.21;
            if (locationMap) {
                locationMap.eachLayer(function(layer) {
                    if (layer instanceof L.Marker) {
                        locationMap.removeLayer(layer);
                    }
                });
                L.marker([selectedLocation.lat, selectedLocation.lng], {draggable: true}).addTo(locationMap);
            }
        });
    }
}

/**
 * Initialize the hotspot visualization map
 */
function initHotspotMap() {
    const delhiCenter = [28.61, 77.21];

    hotspotMap = L.map('hotspotMap').setView(delhiCenter, 10);

    // Add OpenStreetMap tiles
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: '&copy; OpenStreetMap contributors',
        maxZoom: 18
    }).addTo(hotspotMap);
}

/**
 * Main prediction function
 */
async function runPrediction() {
    // Get form data
    const lat = parseFloat(document.getElementById('inputLat').value);
    const lng = parseFloat(document.getElementById('inputLng').value);
    const startDate = document.getElementById('inputStartDate').value;
    const endDate = document.getElementById('inputEndDate').value;

    // Validate inputs
    if (!lat || !lng || !startDate || !endDate) {
        showError('Please fill in all required fields.');
        return;
    }

    // Show loading
    showLoading(true);

    // Build request payload
    const payload = {
        location: {
            lat: lat,
            lng: lng
        },
        date_range: {
            start: startDate,
            end: endDate
        }
    };

    try {
        const response = await fetch('/api/predict', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(payload)
        });

        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.error || 'Prediction request failed');
        }

        const data = await response.json();

        // Display results
        displayResults(data);

        // Show results section
        document.getElementById('resultsSection').classList.remove('result-hidden');

        // Scroll to results
        document.getElementById('resultsSection').scrollIntoView({ behavior: 'smooth' });

    } catch (error) {
        console.error('Prediction error:', error);
        showError('Failed to run prediction: ' + error.message);
    } finally {
        showLoading(false);
    }
}

/**
 * Display prediction results
 */
function displayResults(data) {
    // Show demo warning if applicable
    if (data.is_demo) {
        document.getElementById('demoWarning').style.display = 'block';
    } else {
        document.getElementById('demoWarning').style.display = 'none';
    }

    const predictions = data.predictions;

    // Update crime type prediction
    if (predictions.crime_type) {
        document.getElementById('predictedType').textContent = predictions.crime_type.type || 'Unknown';
        const confidence = predictions.crime_type.confidence || 0;
        document.getElementById('confidenceValue').textContent = (confidence * 100).toFixed(0);
        document.getElementById('confidenceBar').style.width = (confidence * 100) + '%';
    }

    // Update crime count
    if (predictions.crime_count) {
        const count = predictions.crime_count.predicted_count;
        if (Array.isArray(count)) {
            const total = count.reduce((sum, c) => sum + c, 0);
            document.getElementById('predictedCount').textContent = total.toLocaleString();
        } else {
            document.getElementById('predictedCount').textContent = (count || 0).toLocaleString();
        }

        const days = data.request ? data.request.days : 1;
        document.getElementById('countPeriod').textContent = `Over ${days} day${days > 1 ? 's' : ''}`;
    }

    // Update forecast total
    if (predictions.lstm_forecast) {
        const forecast = predictions.lstm_forecast.forecast || [];
        const total = forecast.reduce((sum, c) => sum + c, 0);
        document.getElementById('forecastTotal').textContent = total.toLocaleString();

        // Render forecast chart
        const dates = predictions.lstm_forecast.dates || [];
        renderForecastChart(forecast, dates);
    }

    // Update summary table
    updateSummaryTable(data);

    // Update hotspots map
    if (data.hotspots && data.hotspots.length > 0) {
        updateHotspotsMap(data.hotspots);
    }
}

/**
 * Update summary stats table
 */
function updateSummaryTable(data) {
    const request = data.request || {};

    // Location
    document.getElementById('summaryLocation').textContent =
        `${request.location?.lat?.toFixed(4) || '-'}, ${request.location?.lng?.toFixed(4) || '-'}`;
    document.getElementById('summaryDistrict').textContent = request.district || 'Unknown';

    // Date range
    const start = request.date_range?.start || '-';
    const end = request.date_range?.end || '-';
    document.getElementById('summaryDateRange').textContent = `${start} to ${end}`;
    document.getElementById('summaryDays').textContent = `${request.days || 0} day(s)`;

    // Crime type
    const predictions = data.predictions || {};
    if (predictions.crime_type) {
        document.getElementById('summaryCrimeType').textContent = predictions.crime_type.type || 'Unknown';
        const conf = (predictions.crime_type.confidence || 0) * 100;
        document.getElementById('summaryConfidence').textContent = `${conf.toFixed(0)}% confidence`;
    }

    // Risk level
    const hotspots = data.hotspots || [];
    let maxIntensity = 0;
    hotspots.forEach(h => {
        if (h.intensity > maxIntensity) maxIntensity = h.intensity;
    });

    let riskLevel, riskDetail;
    if (maxIntensity >= 0.7) {
        riskLevel = 'HIGH';
        document.getElementById('summaryRisk').className = 'text-danger fw-bold';
        riskDetail = 'Multiple high-intensity hotspots detected';
    } else if (maxIntensity >= 0.4) {
        riskLevel = 'MEDIUM';
        document.getElementById('summaryRisk').className = 'text-warning fw-bold';
        riskDetail = 'Moderate crime activity expected';
    } else {
        riskLevel = 'LOW';
        document.getElementById('summaryRisk').className = 'text-success fw-bold';
        riskDetail = 'Below-average crime activity expected';
    }

    document.getElementById('summaryRisk').textContent = riskLevel;
    document.getElementById('summaryRiskDetail').textContent = riskDetail;
}

/**
 * Render forecast chart using Plotly.js
 */
function renderForecastChart(forecast, dates) {
    const chartElement = document.getElementById('forecastChart');

    if (!chartElement) return;

    // Format dates for display
    const formattedDates = dates.map(d => {
        const date = new Date(d);
        return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
    });

    const trace = {
        x: formattedDates,
        y: forecast,
        type: 'scatter',
        mode: 'lines+markers',
        name: 'Predicted Crimes',
        line: {
            color: '#17a2b8',
            width: 3
        },
        marker: {
            size: 8,
            color: '#17a2b8',
            line: {
                color: 'white',
                width: 2
            }
        },
        fill: 'tozeroy',
        fillcolor: 'rgba(23, 162, 184, 0.2)'
    };

    const layout = {
        autoexpand: true,
        responsive: true,
        xaxis: {
            title: 'Date',
            showgrid: true,
            gridcolor: 'rgba(0,0,0,0.1)'
        },
        yaxis: {
            title: 'Predicted Crime Count',
            showgrid: true,
            gridcolor: 'rgba(0,0,0,0.1)',
            zeroline: true,
            zerolinecolor: 'rgba(0,0,0,0.2)'
        },
        hovermode: 'x unified',
        showlegend: false,
        margin: {
            l: 50,
            r: 20,
            t: 20,
            b: 50
        }
    };

    const config = {
        displayModeBar: true,
        displaylogo: false,
        responsive: true,
        modeBarButtonsToRemove: ['lasso2d', 'select2d']
    };

    Plotly.newPlot(chartElement, [trace], layout, config);
}

/**
 * Update hotspots map with crime hotspot markers
 */
function updateHotspotsMap(hotspots) {
    if (!hotspotMap) {
        initHotspotMap();
    }

    // Clear existing layers except tile layer
    hotspotMap.eachLayer(function(layer) {
        if (!(layer instanceof L.TileLayer)) {
            hotspotMap.removeLayer(layer);
        }
    });

    // Add hotspot markers
    hotspots.forEach(function(hotspot) {
        const intensity = hotspot.intensity || 0;

        // Determine color based on intensity
        let color;
        let intensityClass;
        if (intensity >= 0.7) {
            color = '#dc3545';  // Red
            intensityClass = 'intensity-high';
        } else if (intensity >= 0.4) {
            color = '#ffc107';  // Yellow
            intensityClass = 'intensity-medium';
        } else {
            color = '#28a745';  // Green
            intensityClass = 'intensity-low';
        }

        // Calculate marker size based on intensity
        const size = 20 + (intensity * 30);

        // Create circle marker
        const marker = L.circleMarker([hotspot.lat, hotspot.lng], {
            radius: size / 2,
            fillColor: color,
            fillOpacity: 0.7,
            color: 'white',
            weight: 2,
            opacity: 1
        }).addTo(hotspotMap);

        // Create popup content
        const popupContent = `
            <div class="p-2">
                <strong>${hotspot.district || 'District'}</strong><br>
                <span class="badge bg-${intensity >= 0.7 ? 'danger' : intensity >= 0.4 ? 'warning' : 'success'}">
                    ${(intensity * 100).toFixed(0)}% Intensity
                </span><br>
                <small class="text-muted">Predicted Type: ${hotspot.predicted_type || 'Unknown'}</small>
            </div>
        `;

        marker.bindPopup(popupContent);

        // Add tooltip
        marker.bindTooltip(
            `${hotspot.district || 'District'}: ${(intensity * 100).toFixed(0)}% intensity`,
            { direction: 'top', offset: [0, -10] }
        );
    });

    // Fit bounds to show all hotspots
    if (hotspots.length > 0) {
        const bounds = L.latLngBounds(hotspots.map(h => [h.lat, h.lng]));
        hotspotMap.fitBounds(bounds, { padding: [30, 30] });
    }
}

/**
 * Show/hide loading overlay
 */
function showLoading(show) {
    const overlay = document.getElementById('loadingOverlay');
    if (overlay) {
        if (show) {
            overlay.classList.add('active');
        } else {
            overlay.classList.remove('active');
        }
    }
}

/**
 * Show error message
 */
function showError(message) {
    // Create or update error alert
    let alertElement = document.querySelector('.alert-danger.prediction-error');

    if (!alertElement) {
        alertElement = document.createElement('div');
        alertElement.className = 'alert alert-danger alert-dismissible prediction-error fade show';
        alertElement.setAttribute('role', 'alert');

        const container = document.querySelector('.container');
        if (container) {
            container.insertBefore(alertElement, container.firstChild);
        }
    }

    alertElement.innerHTML = `
        <i class="bi bi-exclamation-triangle me-2"></i>
        <strong>Error:</strong> ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `;

    // Auto-dismiss after 5 seconds
    setTimeout(() => {
        if (alertElement && alertElement.parentNode) {
            alertElement.remove();
        }
    }, 5000);
}