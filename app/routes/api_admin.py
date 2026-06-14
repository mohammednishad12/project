from flask import Blueprint, jsonify
from app import db
from app.models.user import User
from app.models.crime import Crime
from app.models.prediction import Prediction
from app.models.report import Report
from app.utils.decorators import admin_required

api_admin_bp = Blueprint('api_admin', __name__)


@api_admin_bp.route('/api/admin/stats', methods=['GET'])
@admin_required
def get_admin_stats():
    """
    Get admin statistics:
    - Total users
    - Total crimes
    - Total predictions
    - Total reports
    """
    users_count = User.query.count()
    crimes_count = Crime.query.count()
    predictions_count = Prediction.query.count()
    reports_count = Report.query.count()

    return jsonify({
        'users': users_count,
        'crimes': crimes_count,
        'predictions': predictions_count,
        'reports': reports_count
    }), 200