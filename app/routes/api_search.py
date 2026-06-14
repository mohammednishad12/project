from flask import Blueprint, request, jsonify
from sqlalchemy import or_, func
from datetime import datetime
from app import db
from app.models.crime import Crime

api_search_bp = Blueprint('api_search', __name__)


@api_search_bp.route('/api/crimes', methods=['GET'])
def search_crimes():
    """
    Search and filter crimes with pagination.

    Query Parameters:
        query: Full-text search on district, description, address, or type
        area: Filter by district (case-insensitive partial match)
        type: Filter by crime type (exact match or comma-separated for multiple)
        start: Start date (YYYY-MM-DD)
        end: End date (YYYY-MM-DD)
        time_of_day: Morning (6-12), Afternoon (12-18), Evening (18-24), Night (0-6)
        page: Page number (default 1)
        per_page: Items per page (default 25, max 100)

    Returns:
        JSON with items, total, pages, page, per_page, has_next, has_prev
    """
    try:
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 25, type=int)
    except (ValueError, TypeError):
        return jsonify({'error': 'Invalid page or per_page parameter'}), 400

    # Validate pagination parameters
    if page < 1:
        page = 1
    if per_page < 1:
        per_page = 25
    if per_page > 100:
        per_page = 100

    # Build the base query
    query = Crime.query

    # Full-text search on district, description, address, or type
    search_query = request.args.get('query', '').strip()
    if search_query:
        search_pattern = f'%{search_query}%'
        query = query.filter(
            or_(
                Crime.district.ilike(search_pattern),
                Crime.description.ilike(search_pattern),
                Crime.address.ilike(search_pattern),
                Crime.type.ilike(search_pattern)
            )
        )

    # Filter by district/area (case-insensitive partial match)
    area = request.args.get('area', '').strip()
    if area:
        query = query.filter(Crime.district.ilike(f'%{area}%'))

    # Filter by crime type (exact match or comma-separated for multiple)
    crime_type = request.args.get('type', '').strip()
    if crime_type:
        if ',' in crime_type:
            # Multiple types: split and create IN clause
            types_list = [t.strip().lower() for t in crime_type.split(',') if t.strip()]
            if types_list:
                query = query.filter(
                    func.lower(Crime.type).in_(types_list)
                )
        else:
            # Single type
            query = query.filter(func.lower(Crime.type) == crime_type.lower())

    # Filter by date range
    start_date = request.args.get('start', '').strip()
    end_date = request.args.get('end', '').strip()

    if start_date:
        try:
            start_dt = datetime.strptime(start_date, '%Y-%m-%d').date()
            query = query.filter(Crime.date >= start_dt)
        except ValueError:
            return jsonify({'error': 'Invalid start date format. Use YYYY-MM-DD'}), 400

    if end_date:
        try:
            end_dt = datetime.strptime(end_date, '%Y-%m-%d').date()
            query = query.filter(Crime.date <= end_dt)
        except ValueError:
            return jsonify({'error': 'Invalid end date format. Use YYYY-MM-DD'}), 400

    # Filter by time of day
    time_of_day = request.args.get('time_of_day', '').strip()
    if time_of_day and time_of_day != 'All':
        from datetime import time as time_type
        if time_of_day == 'Morning':
            query = query.filter(
                Crime.time >= time_type(6, 0),
                Crime.time < time_type(12, 0)
            )
        elif time_of_day == 'Afternoon':
            query = query.filter(
                Crime.time >= time_type(12, 0),
                Crime.time < time_type(18, 0)
            )
        elif time_of_day == 'Evening':
            query = query.filter(
                Crime.time >= time_type(18, 0),
                Crime.time < time_type(24, 0)
            )
        elif time_of_day == 'Night':
            query = query.filter(
                Crime.time >= time_type(0, 0),
                Crime.time < time_type(6, 0)
            )

    # Order by date descending (most recent first)
    query = query.order_by(Crime.date.desc(), Crime.time.desc())

    # Paginate
    pagination = query.paginate(page=page, per_page=per_page, error_out=False)

    # Build response
    items = [crime.to_dict() for crime in pagination.items]

    return jsonify({
        'items': items,
        'total': pagination.total,
        'pages': pagination.pages,
        'page': pagination.page,
        'per_page': pagination.per_page,
        'has_next': pagination.has_next,
        'has_prev': pagination.has_prev
    })


@api_search_bp.route('/api/crimes/areas', methods=['GET'])
def get_districts():
    """
    Get list of distinct districts for dropdown population.

    Returns:
        JSON with list of district names
    """
    districts = db.session.query(Crime.district).distinct().filter(
        Crime.district.isnot(None)
    ).order_by(Crime.district).all()

    return jsonify({
        'areas': [d[0] for d in districts if d[0]]
    })


@api_search_bp.route('/api/crimes/types', methods=['GET'])
def get_crime_types():
    """
    Get list of distinct crime types for dropdown population.

    Returns:
        JSON with list of crime type names
    """
    types = db.session.query(Crime.type).distinct().filter(
        Crime.type.isnot(None)
    ).order_by(Crime.type).all()

    return jsonify({
        'types': [t[0] for t in types if t[0]]
    })