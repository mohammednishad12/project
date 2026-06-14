from flask import Blueprint, render_template, request, jsonify, send_file
from sqlalchemy import func
from datetime import datetime
from app import db
from app.models.crime import Crime
from app.models.report import Report
from app.utils.pdf_generator import generate_pdf_report
import csv
import io
import os

reports_bp = Blueprint('reports', __name__)


@reports_bp.route('/reports')
def index():
    """Render the reports page."""
    return render_template('reports.html')


@reports_bp.route('/api/report/pdf', methods=['GET'])
def download_pdf():
    """Generate and download a PDF report."""
    try:
        # Parse query parameters
        region = request.args.get('region', '')
        start_str = request.args.get('start', '')
        end_str = request.args.get('end', '')
        types_str = request.args.get('types', '')

        # Build base query
        query = db.session.query(Crime)

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

        # Generate PDF report
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        pdf_filename = f'report_{timestamp}.pdf'
        
        # Ensure reports directory exists
        reports_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'reports')
        os.makedirs(reports_dir, exist_ok=True)
        
        pdf_filepath = generate_pdf_report(
            query=query,
            region=region,
            start_date=start_str,
            end_date=end_str,
            types=types_str,
            filename=pdf_filename
        )

        # Create report record in database
        parameters = {
            'region': region,
            'start': start_str,
            'end': end_str,
            'types': types_str
        }
        
        report_record = Report(
            user_id=1,  # Placeholder - use actual user_id when auth is integrated
            parameters_json=str(parameters),
            file_path=pdf_filepath,
            format='pdf'
        )
        db.session.add(report_record)
        db.session.commit()

        # Return file as download
        return send_file(
            pdf_filepath,
            mimetype='application/pdf',
            as_attachment=True,
            download_name=pdf_filename
        )

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@reports_bp.route('/api/report/csv', methods=['GET'])
def download_csv():
    """Generate and download a CSV report."""
    try:
        # Parse query parameters
        region = request.args.get('region', '')
        start_str = request.args.get('start', '')
        end_str = request.args.get('end', '')
        types_str = request.args.get('types', '')

        # Build base query
        query = db.session.query(Crime)

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

        # Generate CSV in memory
        output = io.StringIO()
        writer = csv.writer(output)
        
        # Write header
        writer.writerow([
            'ID', 'Date', 'Time', 'Type', 'Description', 
            'District', 'Address', 'Latitude', 'Longitude'
        ])
        
        # Write data rows
        crimes = query.order_by(Crime.date.desc()).all()
        for crime in crimes:
            writer.writerow([
                crime.id,
                crime.date.isoformat() if crime.date else '',
                crime.time.isoformat() if crime.time else '',
                crime.type or '',
                crime.description or '',
                crime.district or '',
                crime.address or '',
                crime.latitude if crime.latitude is not None else '',
                crime.longitude if crime.longitude is not None else ''
            ])
        
        # Get CSV content
        csv_content = output.getvalue()
        output.close()
        
        # Create report record in database
        parameters = {
            'region': region,
            'start': start_str,
            'end': end_str,
            'types': types_str
        }
        
        report_record = Report(
            user_id=1,  # Placeholder - use actual user_id when auth is integrated
            parameters_json=str(parameters),
            file_path='',
            format='csv'
        )
        db.session.add(report_record)
        db.session.commit()

        # Return as file download
        output = io.BytesIO()
        output.write(csv_content.encode('utf-8'))
        output.seek(0)
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        csv_filename = f'report_{timestamp}.csv'
        
        return send_file(
            output,
            mimetype='text/csv',
            as_attachment=True,
            download_name=csv_filename
        )

    except Exception as e:
        return jsonify({'error': str(e)}), 500