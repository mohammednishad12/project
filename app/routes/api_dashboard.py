from flask import Blueprint, request, jsonify
from sqlalchemy import func, extract
from datetime import datetime
from app import db
from app.models.crime import Crime

api_dashboard_bp = Blueprint('api_dashboard', __name__)


@api_dashboard_bp.route('/api/stats', methods=['GET'])
def get_stats():
    """Get aggregated crime statistics with filters."""
    try:
        start_str = request.args.get('start')
        end_str = request.args.get('end')
        types_str = request.args.get('types')
        area = request.args.get('area')

        # Build filter conditions once
        filters = []
        if start_str:
            try:
                start_date = datetime.strptime(start_str, '%Y-%m-%d').date()
                filters.append(Crime.date >= start_date)
            except ValueError:
                pass
        if end_str:
            try:
                end_date = datetime.strptime(end_str, '%Y-%m-%d').date()
                filters.append(Crime.date <= end_date)
            except ValueError:
                pass
        if types_str:
            types_list = [t.strip() for t in types_str.split(',')]
            types_list = [t for t in types_list if t]
            if types_list:
                filters.append(Crime.type.in_(types_list))
        if area:
            filters.append(func.lower(Crime.district) == func.lower(area))

        # Total count
        total_query = db.session.query(Crime)
        for f in filters:
            total_query = total_query.filter(f)
        total_crimes = total_query.count()

        # By type (top 10)
        type_query = db.session.query(Crime.type, func.count(Crime.id).label('count'))
        for f in filters:
            type_query = type_query.filter(f)
        type_query = type_query.group_by(Crime.type).order_by(func.count(Crime.id).desc()).limit(10)
        by_type = [{'type': row[0], 'count': row[1]} for row in type_query.all()]

        # By month
        month_query = db.session.query(
            func.strftime('%Y-%m', Crime.date).label('month'),
            func.count(Crime.id).label('count')
        )
        for f in filters:
            month_query = month_query.filter(f)
        month_query = month_query.group_by('month').order_by('month')
        by_month = [{'month': row[0], 'count': row[1]} for row in month_query.all()]

        # By district (top 10)
        district_query = db.session.query(
            Crime.district,
            func.count(Crime.id).label('count')
        ).filter(Crime.district.isnot(None))
        for f in filters:
            district_query = district_query.filter(f)
        district_query = district_query.group_by(Crime.district).order_by(func.count(Crime.id).desc()).limit(10)
        by_district = [{'district': row[0], 'count': row[1]} for row in district_query.all()]

        return jsonify({
            'total_crimes': total_crimes,
            'by_type': by_type,
            'by_month': by_month,
            'by_district': by_district
        }), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@api_dashboard_bp.route('/api/heatmap', methods=['GET'])
def get_heatmap():
    """Get crime points as GeoJSON for heatmap visualization."""
    try:
        # Parse query parameters
        start_str = request.args.get('start')
        end_str = request.args.get('end')
        types_str = request.args.get('types')
        area = request.args.get('area')

        # Build base query
        query = db.session.query(Crime).filter(
            Crime.latitude.isnot(None),
            Crime.longitude.isnot(None)
        )

        # Apply date filters
        if start_str:
            try:
                start_date = datetime.strptime(start_str, '%Y-%m-%d').date()
                query = query.filter(Crime.date >= start_date)
            except ValueError:
                pass

        if end_str:
            try:
                end_date = datetime.strptime(end_str, '%Y-%m-%d').date()
                query = query.filter(Crime.date <= end_date)
            except ValueError:
                pass

        # Apply crime type filter
        if types_str:
            types_list = [t.strip() for t in types_str.split(',')]
            types_list = [t for t in types_list if t]
            if types_list:
                query = query.filter(Crime.type.in_(types_list))

        # Apply area/district filter (case-insensitive)
        if area:
            query = query.filter(func.lower(Crime.district) == func.lower(area))

        # Limit to 10000 points for performance
        crimes = query.limit(10000).all()

        # Build GeoJSON FeatureCollection
        features = []
        for crime in crimes:
            feature = {
                'type': 'Feature',
                'geometry': {
                    'type': 'Point',
                    'coordinates': [crime.longitude, crime.latitude]
                },
                'properties': {
                    'type': crime.type,
                    'date': crime.date.isoformat() if crime.date else None,
                    'intensity': 1
                }
            }
            features.append(feature)

        geojson = {
            'type': 'FeatureCollection',
            'features': features
        }

        return jsonify(geojson), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500