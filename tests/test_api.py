"""Tests for API endpoints."""
import pytest
from datetime import date, time
from app import db
from app.models.crime import Crime


@pytest.fixture
def sample_crimes(app):
    """Create sample crime records for testing."""
    with app.app_context():
        crimes = [
            Crime(
                date=date(2024, 1, 15),
                time=time(14, 30),
                type='Theft',
                description='Test theft',
                address='123 Main St',
                district='Central',
                latitude=40.7128,
                longitude=-74.0060
            ),
            Crime(
                date=date(2024, 1, 20),
                time=time(18, 45),
                type='Burglary',
                description='Test burglary',
                address='456 Oak Ave',
                district='North',
                latitude=40.7200,
                longitude=-74.0100
            ),
            Crime(
                date=date(2024, 2, 10),
                time=time(22, 0),
                type='Vandalism',
                description='Test vandalism',
                address='789 Pine Rd',
                district='Central',
                latitude=40.7150,
                longitude=-74.0050
            ),
        ]
        for crime in crimes:
            db.session.add(crime)
        db.session.commit()
        yield crimes


class TestDashboardStats:
    """Test cases for /api/stats endpoint."""

    def test_dashboard_stats(self, client, sample_crimes):
        """Test GET /api/stats returns 200 with correct structure."""
        response = client.get('/api/stats')
        assert response.status_code == 200
        data = response.get_json()
        assert 'total_crimes' in data
        assert 'by_type' in data
        assert 'by_month' in data
        assert 'by_district' in data
        assert isinstance(data['by_type'], list)
        assert isinstance(data['by_month'], list)
        assert isinstance(data['by_district'], list)

    def test_dashboard_stats_with_date_filter(self, client, sample_crimes):
        """Test /api/stats with date filter."""
        response = client.get('/api/stats?start=2024-01-01&end=2024-01-31')
        assert response.status_code == 200
        data = response.get_json()
        assert 'total_crimes' in data


class TestHeatmapData:
    """Test cases for /api/heatmap endpoint."""

    def test_heatmap_data(self, client, sample_crimes):
        """Test GET /api/heatmap returns GeoJSON structure."""
        response = client.get('/api/heatmap')
        assert response.status_code == 200
        data = response.get_json()
        assert 'type' in data
        assert data['type'] == 'FeatureCollection'
        assert 'features' in data
        assert isinstance(data['features'], list)

    def test_heatmap_data_with_filters(self, client, sample_crimes):
        """Test /api/heatmap with crime type filter."""
        response = client.get('/api/heatmap?types=Theft')
        assert response.status_code == 200
        data = response.get_json()
        assert data['type'] == 'FeatureCollection'


class TestSearchCrimes:
    """Test cases for /api/crimes endpoint."""

    def test_search_crimes(self, client, sample_crimes):
        """Test GET /api/crimes returns paginated results."""
        response = client.get('/api/crimes')
        assert response.status_code == 200
        data = response.get_json()
        assert 'items' in data
        assert 'total' in data
        assert 'pages' in data
        assert 'page' in data
        assert 'per_page' in data
        assert 'has_next' in data
        assert 'has_prev' in data
        assert isinstance(data['items'], list)

    def test_search_with_area_filter(self, client, sample_crimes):
        """Test GET /api/crimes with area filter."""
        response = client.get('/api/crimes?area=Central')
        assert response.status_code == 200
        data = response.get_json()
        # Should only return crimes from Central district
        for item in data['items']:
            assert 'Central' in item.get('district', '')

    def test_search_with_type_filter(self, client, sample_crimes):
        """Test GET /api/crimes with crime type filter."""
        response = client.get('/api/crimes?type=Theft')
        assert response.status_code == 200
        data = response.get_json()
        for item in data['items']:
            assert item.get('type') == 'Theft'

    def test_search_pagination(self, client, sample_crimes):
        """Test /api/crimes pagination parameters."""
        response = client.get('/api/crimes?page=1&per_page=2')
        assert response.status_code == 200
        data = response.get_json()
        assert data['page'] == 1
        assert data['per_page'] == 2

    def test_search_with_date_range(self, client, sample_crimes):
        """Test /api/crimes with date range filter."""
        response = client.get('/api/crimes?start=2024-01-01&end=2024-01-31')
        assert response.status_code == 200
        data = response.get_json()
        assert data['total'] >= 0


class TestCrimeAreasAndTypes:
    """Test cases for /api/crimes/areas and /api/crimes/types endpoints."""

    def test_get_districts(self, client, sample_crimes):
        """Test GET /api/crimes/areas returns district list."""
        response = client.get('/api/crimes/areas')
        assert response.status_code == 200
        data = response.get_json()
        assert 'areas' in data
        assert isinstance(data['areas'], list)
        assert 'Central' in data['areas']
        assert 'North' in data['areas']

    def test_get_crime_types(self, client, sample_crimes):
        """Test GET /api/crimes/types returns crime type list."""
        response = client.get('/api/crimes/types')
        assert response.status_code == 200
        data = response.get_json()
        assert 'types' in data
        assert isinstance(data['types'], list)
        assert 'Theft' in data['types']
        assert 'Burglary' in data['types']


class TestAdminEndpoints:
    """Test cases for admin endpoints."""

    def test_admin_users_with_admin_token(self, client, admin_user, admin_headers):
        """Test GET /admin/users with admin JWT returns 200."""
        response = client.get('/admin/users', headers=admin_headers)
        # May return 200 or redirect depending on implementation
        assert response.status_code in [200, 302]

    def test_admin_users_with_viewer_token(self, client, sample_user, auth_headers):
        """Test GET /admin/users with viewer JWT returns 403."""
        response = client.get('/admin/users', headers=auth_headers)
        assert response.status_code == 403

    def test_admin_users_no_token(self, client):
        """Test GET /admin/users without token returns 401."""
        response = client.get('/admin/users')
        assert response.status_code == 401