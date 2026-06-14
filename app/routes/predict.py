"""
Prediction Page Blueprint

This module provides the prediction page route.
"""

from flask import Blueprint, render_template

predict_bp = Blueprint('predict', __name__)


@predict_bp.route('/predict')
def prediction_page():
    """
    Render the ML prediction page.

    Returns:
        Rendered prediction.html template
    """
    return render_template('prediction.html')