from flask import Blueprint, request, jsonify
from sqlalchemy import func
from datetime import datetime
from app import db
from app.models.crime import Crime

api_reports_bp = Blueprint('api_reports', __name__)


def _build_filtered_crime_ids_subquery(region, start_str, end_str, types_str):
    """Build a subquery of crime IDs matching all filters."""
    query = db.session.query(Crime.id)

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

    # Apply crime type filter (case-insensitive)
    if types_str:
        types_list = [t.strip().lower() for t in types_str.split(',') if t.strip()]
        if types_list:
            query = query.filter(func.lower(Crime.type).in_(types_list))

    # Apply region/district filter (case-insensitive)
    if region:
        query = query.filter(func.lower(Crime.district) == func.lower(region))

    return query.scalar_subquery()


@api_reports_bp.route('/api/report/preview', methods=['GET'])
def get_report_preview():
    """Get summary statistics for report preview."""
    try:
        # Parse query parameters
        region = request.args.get('region', '')
        start_str = request.args.get('start', '')
        end_str = request.args.get('end', '')
        types_str = request.args.get('types', '')

        # Build filtered crime IDs subquery
        filtered_ids = _build_filtered_crime_ids_subquery(region, start_str, end_str, types_str)

        # Count total matching crimes
        total_crimes = db.session.query(func.count(Crime.id)).filter(
            Crime.id.in_(filtered_ids)
        ).scalar() or 0

        # Get date range
        date_range = f"{start_str or 'N/A'} to {end_str or 'N/A'}"

        # Get top crime types
        top_types_query = db.session.query(
            Crime.type,
            func.count(Crime.id).label('count')
        ).filter(
            Crime.id.in_(filtered_ids)
        ).group_by(Crime.type).order_by(func.count(Crime.id).desc()).limit(5).all()

        top_crime_types = [{'type': row[0], 'count': row[1]} for row in top_types_query]

        # Get monthly breakdown
        monthly_query = db.session.query(
            func.strftime('%Y-%m', Crime.date).label('month'),
            func.count(Crime.id).label('count')
        ).filter(
            Crime.id.in_(filtered_ids)
        ).group_by('month').order_by('month').all()

        monthly_breakdown = []
        prev_count = None
        for row in monthly_query:
            change = None
            if prev_count is not None and prev_count > 0:
                pct_change = ((row[1] - prev_count) / prev_count) * 100
                change = f"{'+' if pct_change >= 0 else ''}{pct_change:.1f}%"

            # Get top type for this month
            month_start = datetime.strptime(row[0] + '-01', '%Y-%m-%d').date()
            month_end = datetime(month_start.year, month_start.month + 1, 1).date() if month_start.month < 12 else datetime(month_start.year + 1, 1, 1).date()

            top_type_query = db.session.query(
                Crime.type,
                func.count(Crime.id).label('count')
            ).filter(
                Crime.id.in_(filtered_ids),
                Crime.date >= month_start,
                Crime.date < month_end
            ).group_by(Crime.type).order_by(func.count(Crime.id).desc()).first()

            top_type = top_type_query[0] if top_type_query else 'N/A'

            monthly_breakdown.append({
                'month': row[0],
                'count': row[1],
                'top_type': top_type,
                'change': change
            })
            prev_count = row[1]

        # Calculate trend direction
        trend_direction = 'stable'
        trend_percent = 0
        if len(monthly_breakdown) >= 2:
            first_month_count = monthly_breakdown[0]['count']
            last_month_count = monthly_breakdown[-1]['count']
            if last_month_count > first_month_count:
                trend_direction = 'increasing'
                trend_percent = ((last_month_count - first_month_count) / first_month_count) * 100 if first_month_count > 0 else 0
            elif last_month_count < first_month_count:
                trend_direction = 'decreasing'
                trend_percent = ((first_month_count - last_month_count) / first_month_count) * 100 if first_month_count > 0 else 0

        # Get hotspots (top 5 districts)
        hotspots_query = db.session.query(
            Crime.district,
            func.count(Crime.id).label('count'),
            func.avg(Crime.latitude).label('avg_lat'),
            func.avg(Crime.longitude).label('avg_lng')
        ).filter(
            Crime.id.in_(filtered_ids),
            Crime.district.isnot(None),
            Crime.latitude.isnot(None),
            Crime.longitude.isnot(None)
        ).group_by(Crime.district).order_by(func.count(Crime.id).desc()).limit(5).all()

        hotspots = [{
            'district': row[0],
            'count': row[1],
            'avg_lat': round(row[2], 4) if row[2] else 0,
            'avg_lng': round(row[3], 4) if row[3] else 0
        } for row in hotspots_query]

        return jsonify({
            'total_crimes': total_crimes,
            'date_range': date_range,
            'top_crime_types': top_crime_types,
            'trend_direction': trend_direction,
            'trend_percent': round(trend_percent, 1),
            'monthly_breakdown': monthly_breakdown[:12],  # Limit to 12 months
            'hotspots': hotspots
        }), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500