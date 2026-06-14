from flask import Blueprint, render_template, redirect
from flask_login import current_user

dashboard_bp = Blueprint('dashboard', __name__)


@dashboard_bp.route('/')
def home():
    if current_user.is_authenticated:
        return redirect('/dashboard')
    return redirect('/auth/login')


@dashboard_bp.route('/dashboard')
def dashboard():
    return render_template('dashboard.html')