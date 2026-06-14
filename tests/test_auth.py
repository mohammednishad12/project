"""Tests for authentication endpoints."""
import pytest


class TestAuthRegister:
    """Test cases for user registration."""

    def test_register_success(self, client):
        """Test successful user registration."""
        response = client.post('/auth/register', json={
            'username': 'newuser',
            'email': 'newuser@example.com',
            'password': 'securepass123'
        })
        assert response.status_code == 201
        data = response.get_json()
        assert data['message'] == 'User registered successfully'
        assert data['user']['username'] == 'newuser'
        assert data['user']['email'] == 'newuser@example.com'
        assert data['user']['role'] == 'viewer'

    def test_register_duplicate_username(self, client, sample_user):
        """Test registration with duplicate username returns 409."""
        response = client.post('/auth/register', json={
            'username': 'testuser',
            'email': 'different@example.com',
            'password': 'securepass123'
        })
        assert response.status_code == 409
        data = response.get_json()
        assert 'already exists' in data['error'].lower()

    def test_register_duplicate_email(self, client, sample_user):
        """Test registration with duplicate email returns 409."""
        response = client.post('/auth/register', json={
            'username': 'differentuser',
            'email': 'test@example.com',
            'password': 'securepass123'
        })
        assert response.status_code == 409
        data = response.get_json()
        assert 'already registered' in data['error'].lower()

    def test_register_invalid_username_short(self, client):
        """Test registration with too short username."""
        response = client.post('/auth/register', json={
            'username': 'ab',
            'email': 'test@example.com',
            'password': 'password123'
        })
        assert response.status_code == 400
        assert 'username' in response.get_json()['error'].lower()

    def test_register_invalid_email(self, client):
        """Test registration with invalid email format."""
        response = client.post('/auth/register', json={
            'username': 'validuser',
            'email': 'not-an-email',
            'password': 'password123'
        })
        assert response.status_code == 400
        assert 'email' in response.get_json()['error'].lower()

    def test_register_short_password(self, client):
        """Test registration with too short password."""
        response = client.post('/auth/register', json={
            'username': 'validuser',
            'email': 'test@example.com',
            'password': '12345'
        })
        assert response.status_code == 400
        assert 'password' in response.get_json()['error'].lower()


class TestAuthLogin:
    """Test cases for user login."""

    def test_login_success(self, client, sample_user):
        """Test successful login returns token."""
        response = client.post('/auth/login', json={
            'username': 'testuser',
            'password': 'password123'
        })
        assert response.status_code == 200
        data = response.get_json()
        assert 'access_token' in data
        assert 'refresh_token' in data
        assert data['user']['username'] == 'testuser'

    def test_login_invalid_password(self, client, sample_user):
        """Test login with wrong password returns 401."""
        response = client.post('/auth/login', json={
            'username': 'testuser',
            'password': 'wrongpassword'
        })
        assert response.status_code == 401
        assert 'invalid' in response.get_json()['error'].lower()

    def test_login_nonexistent_user(self, client):
        """Test login with nonexistent user returns 401."""
        response = client.post('/auth/login', json={
            'username': 'nonexistent',
            'password': 'password123'
        })
        assert response.status_code == 401
        assert 'invalid' in response.get_json()['error'].lower()

    def test_login_missing_fields(self, client):
        """Test login with missing fields returns 400."""
        response = client.post('/auth/login', json={
            'username': 'testuser'
        })
        assert response.status_code == 400


class TestAuthMe:
    """Test cases for /auth/me endpoint."""

    def test_me_endpoint_with_token(self, client, sample_user, auth_headers):
        """Test /auth/me with valid JWT returns user info."""
        response = client.get('/auth/me', headers=auth_headers)
        assert response.status_code == 200
        data = response.get_json()
        assert data['user']['username'] == 'testuser'
        assert data['user']['email'] == 'test@example.com'

    def test_me_endpoint_no_token(self, client):
        """Test /auth/me without token returns 401."""
        response = client.get('/auth/me')
        assert response.status_code == 401

    def test_me_endpoint_invalid_token(self, client):
        """Test /auth/me with invalid token returns 422."""
        response = client.get('/auth/me', headers={
            'Authorization': 'Bearer invalid-token'
        })
        assert response.status_code == 422


class TestAuthVerify:
    """Test cases for token verification."""

    def test_verify_token_valid(self, client, sample_user, auth_headers):
        """Test /auth/verify with valid token."""
        response = client.get('/auth/verify', headers=auth_headers)
        assert response.status_code == 200
        data = response.get_json()
        assert data['valid'] is True
        assert data['user']['username'] == 'testuser'

    def test_verify_token_no_token(self, client):
        """Test /auth/verify without token returns 401."""
        response = client.get('/auth/verify')
        assert response.status_code == 401


class TestAuthRefresh:
    """Test cases for token refresh."""

    def test_refresh_token(self, client, sample_user):
        """Test /auth/refresh with valid refresh token."""
        # First login to get refresh token
        login_response = client.post('/auth/login', json={
            'username': 'testuser',
            'password': 'password123'
        })
        refresh_token = login_response.get_json()['refresh_token']

        # Use refresh token
        response = client.post('/auth/refresh', headers={
            'Authorization': f'Bearer {refresh_token}'
        })
        assert response.status_code == 200
        data = response.get_json()
        assert 'access_token' in data