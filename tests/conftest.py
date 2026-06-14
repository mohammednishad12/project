import pytest
from app import create_app, db
from app.models.user import User
from app.models.crime import Crime


@pytest.fixture
def app():
    """Create and configure a new app instance for each test."""
    app = create_app('testing')
    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    """Create a test client for the app."""
    return app.test_client()


@pytest.fixture
def runner(app):
    """Create a test CLI runner for the app."""
    return app.test_cli_runner()


@pytest.fixture
def sample_user(app):
    """Create a sample user for testing."""
    with app.app_context():
        user = User(
            username='testuser',
            email='test@example.com',
            role='viewer'
        )
        user.set_password('password123')
        db.session.add(user)
        db.session.commit()
        return user


@pytest.fixture
def admin_user(app):
    """Create an admin user for testing."""
    with app.app_context():
        user = User(
            username='admin',
            email='admin@example.com',
            role='admin'
        )
        user.set_password('adminpass123')
        db.session.add(user)
        db.session.commit()
        return user


@pytest.fixture
def auth_headers(client, sample_user):
    """Get authentication headers for a sample user."""
    response = client.post('/auth/login', json={
        'username': 'testuser',
        'password': 'password123'
    })
    token = response.get_json()['access_token']
    return {'Authorization': f'Bearer {token}'}


@pytest.fixture
def admin_headers(client, admin_user):
    """Get authentication headers for an admin user."""
    response = client.post('/auth/login', json={
        'username': 'admin',
        'password': 'adminpass123'
    })
    token = response.get_json()['access_token']
    return {'Authorization': f'Bearer {token}'}