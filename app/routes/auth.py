import re
from flask import Blueprint, request, jsonify, render_template, make_response, redirect
from flask_jwt_extended import (
    create_access_token, create_refresh_token,
    jwt_required, get_jwt_identity, get_jwt
)
from app import db
from app.models.user import User

auth_bp = Blueprint('auth', __name__)


def validate_username(username):
    """Validate username is 3-80 characters."""
    if not username or not isinstance(username, str):
        return False
    return 3 <= len(username) <= 80


def validate_email(email):
    """Validate email format."""
    if not email or not isinstance(email, str):
        return False
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None


def validate_password(password):
    """Validate password is at least 6 characters."""
    if not password or not isinstance(password, str):
        return False
    return len(password) >= 6


@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    """Register a new user (GET renders page, POST handles API)."""
    if request.method == 'GET':
        return render_template('auth/register.html')

    data = request.get_json()
    if not data:
        return jsonify({'error': 'Request body is required'}), 400

    username = data.get('username', '').strip()
    email = data.get('email', '').strip().lower()
    password = data.get('password', '')
    role = data.get('role', 'viewer')

    # Validate username
    if not validate_username(username):
        return jsonify({'error': 'Username must be 3-80 characters'}), 400

    # Validate email
    if not validate_email(email):
        return jsonify({'error': 'Valid email is required'}), 400

    # Validate password
    if not validate_password(password):
        return jsonify({'error': 'Password must be at least 6 characters'}), 400

    # Validate role
    if role not in ('admin', 'viewer'):
        role = 'viewer'

    # Check for existing user
    if User.query.filter_by(username=username).first():
        return jsonify({'error': 'Username already exists'}), 409

    if User.query.filter_by(email=email).first():
        return jsonify({'error': 'Email already registered'}), 409

    # Create new user
    user = User(username=username, email=email, role=role)
    user.set_password(password)

    db.session.add(user)
    db.session.commit()

    return jsonify({
        'message': 'User registered successfully',
        'user': user.to_dict()
    }), 201


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    """Authenticate user (GET renders page, POST handles API)."""
    if request.method == 'GET':
        return render_template('auth/login.html')

    data = request.get_json()
    if not data:
        return jsonify({'error': 'Request body is required'}), 400

    username = data.get('username', '').strip()
    password = data.get('password', '')

    if not username or not password:
        return jsonify({'error': 'Username and password are required'}), 400

    # Find user
    user = User.query.filter_by(username=username).first()

    if not user or not user.check_password(password):
        return jsonify({'error': 'Invalid username or password'}), 401

    # Create tokens
    access_token = create_access_token(
        identity=user.id,
        additional_claims={'role': user.role}
    )
    refresh_token = create_refresh_token(identity=user.id)

    response = jsonify({
        'message': 'Login successful',
        'access_token': access_token,
        'refresh_token': refresh_token,
        'user': user.to_dict()
    })

    # Set refresh token in httpOnly cookie
    response.set_cookie(
        'refresh_token',
        refresh_token,
        httponly=True,
        secure=False,  # Set to True in production with HTTPS
        samesite='Lax',
        max_age=30 * 24 * 60 * 60  # 30 days
    )

    return response, 200


@auth_bp.route('/logout', methods=['GET', 'POST'])
def logout():
    """Logout user and invalidate tokens."""
    if request.method == 'GET':
        # Browser navigation - clear cookies and redirect to login
        response = make_response(redirect('/auth/login'))
        response.delete_cookie('refresh_token')
        return response
    
    # POST: API call - clear cookies and return success
    response = jsonify({'message': 'Logout successful'})
    response.delete_cookie('refresh_token')
    return response, 200


@auth_bp.route('/me', methods=['GET'])
@jwt_required()
def get_current_user_info():
    """Get current authenticated user info."""
    current_user_id = get_jwt_identity()
    user = User.query.get(current_user_id)

    if not user:
        return jsonify({'error': 'User not found'}), 404

    return jsonify({'user': user.to_dict()}), 200


@auth_bp.route('/refresh', methods=['POST'])
@jwt_required(refresh=True)
def refresh():
    """Refresh access token using refresh token from cookie."""
    current_user_id = get_jwt_identity()
    user = User.query.get(current_user_id)

    if not user:
        return jsonify({'error': 'User not found'}), 404

    access_token = create_access_token(
        identity=user.id,
        additional_claims={'role': user.role}
    )

    return jsonify({
        'access_token': access_token,
        'user': user.to_dict()
    }), 200


@auth_bp.route('/verify', methods=['GET'])
@jwt_required()
def verify_token():
    """Verify if the current JWT token is valid."""
    current_user_id = get_jwt_identity()
    claims = get_jwt()
    user = User.query.get(current_user_id)

    if not user:
        return jsonify({'error': 'User not found'}), 404

    return jsonify({
        'valid': True,
        'user': user.to_dict(),
        'role': claims.get('role')
    }), 200