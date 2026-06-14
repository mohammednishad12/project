from flask import Blueprint, request, jsonify, render_template, current_app
from datetime import datetime
from flask_jwt_extended import jwt_required, get_jwt_identity
import os
import uuid
import sys
import pandas as pd

from app import db
from app.models.user import User
from app.models.crime import Crime
from app.models.prediction import Prediction
from app.models.report import Report
from app.utils.decorators import admin_required

admin_bp = Blueprint('admin', __name__)

# In-memory storage for training job status
training_jobs = {}


def parse_date(date_str):
    """Parse a date string into a datetime.date object."""
    if pd.isna(date_str):
        return None

    date_str = str(date_str).strip()

    formats = [
        '%Y-%m-%d',
        '%m/%d/%Y',
        '%d/%m/%Y',
        '%d-%m-%Y',
        '%Y/%m/%d',
        '%m-%d-%Y',
        '%Y-%m-%d %H:%M:%S',
        '%Y-%m-%dT%H:%M:%S',
        '%Y-%m-%dT%H:%M:%S.%f',
        '%m/%d/%Y %I:%M:%S %p',
        '%d/%m/%Y %H:%M:%S',
    ]

    for fmt in formats:
        try:
            dt = datetime.strptime(date_str, fmt)
            return dt.date()
        except ValueError:
            continue

    try:
        return pd.to_datetime(date_str).date()
    except Exception:
        return None


def parse_time(time_str):
    """Parse a time string into a datetime.time object."""
    if pd.isna(time_str):
        return None

    time_str = str(time_str).strip()

    formats = [
        '%H:%M:%S',
        '%H:%M',
        '%I:%M:%S %p',
        '%I:%M %p',
        '%H:%M:%S.%f',
    ]

    for fmt in formats:
        try:
            dt = datetime.strptime(time_str, fmt)
            return dt.time()
        except ValueError:
            continue

    try:
        return pd.to_datetime(time_str).time()
    except Exception:
        return None


def ingest_csv_file(file_path):
    """
    Ingest a CSV file into the crime database.
    Returns the number of records inserted.
    """
    try:
        df = pd.read_csv(file_path, encoding='utf-8')
    except UnicodeDecodeError:
        df = pd.read_csv(file_path, encoding='latin-1')
    except Exception as e:
        raise Exception(f"Failed to read CSV file: {str(e)}")

    if df.empty:
        raise Exception("CSV file is empty")

    # Standardize column names
    column_mapping = {}
    for col in df.columns:
        col_lower = col.lower().strip()

        if col_lower in ['latitude', 'lat', 'y']:
            column_mapping[col] = 'latitude'
        elif col_lower in ['longitude', 'lng', 'lon', 'long', 'x']:
            column_mapping[col] = 'longitude'
        elif col_lower in ['crime_type', 'primary_type', 'type', 'offense_type', 'crime_category']:
            column_mapping[col] = 'type'
        elif col_lower in ['district', 'area', 'community_area', 'ward', 'beat']:
            column_mapping[col] = 'district'
        elif col_lower in ['description', 'desc', 'offense_description', 'crime_description']:
            column_mapping[col] = 'description'
        elif col_lower in ['address', 'block', 'location', 'street_address', 'street']:
            column_mapping[col] = 'address'
        elif col_lower in ['date', 'incident_date', 'occurred_date', 'crime_date']:
            column_mapping[col] = 'date'
        elif col_lower in ['time', 'hour', 'incident_time', 'occurred_time', 'crime_time']:
            column_mapping[col] = 'time'

    df = df.rename(columns=column_mapping)

    # Find columns
    date_col = None
    for col in ['date', 'incident_date', 'occurred_date', 'crime_date']:
        if col in df.columns:
            date_col = col
            break

    time_col = None
    for col in ['time', 'hour', 'incident_time', 'occurred_time', 'crime_time']:
        if col in df.columns:
            time_col = col
            break

    type_col = None
    for col in ['type', 'crime_type', 'primary_type', 'offense_type', 'crime_category']:
        if col in df.columns:
            type_col = col
            break

    desc_col = None
    for col in ['description', 'desc', 'offense_description']:
        if col in df.columns:
            desc_col = col
            break

    lat_col = None
    for col in ['latitude', 'lat']:
        if col in df.columns:
            lat_col = col
            break

    lng_col = None
    for col in ['longitude', 'lng', 'lon', 'long']:
        if col in df.columns:
            lng_col = col
            break

    district_col = None
    for col in ['district', 'area', 'community_area', 'ward', 'beat']:
        if col in df.columns:
            district_col = col
            break

    address_col = None
    for col in ['address', 'block', 'location', 'street_address', 'street']:
        if col in df.columns:
            address_col = col
            break

    # Build crime objects
    crimes = []
    for idx in range(len(df)):
        crime_date = None
        if date_col:
            crime_date = parse_date(df.loc[idx, date_col])

        crime_time = None
        if time_col:
            crime_time = parse_time(df.loc[idx, time_col])

        crime_type = None
        if type_col:
            val = df.loc[idx, type_col]
            if isinstance(val, str):
                crime_type = val.lower().strip()
            elif pd.notna(val):
                crime_type = str(val)

        if not crime_type:
            continue

        description = None
        if desc_col:
            val = df.loc[idx, desc_col]
            if isinstance(val, str):
                description = val.strip()
            elif pd.notna(val):
                description = str(val)

        latitude = None
        if lat_col:
            val = df.loc[idx, lat_col]
            try:
                latitude = float(val) if pd.notna(val) else None
            except (ValueError, TypeError):
                latitude = None

        longitude = None
        if lng_col:
            val = df.loc[idx, lng_col]
            try:
                longitude = float(val) if pd.notna(val) else None
            except (ValueError, TypeError):
                longitude = None

        district = None
        if district_col:
            val = df.loc[idx, district_col]
            if isinstance(val, str):
                district = val.strip()
            elif pd.notna(val):
                district = str(val)

        address = None
        if address_col:
            val = df.loc[idx, address_col]
            if isinstance(val, str):
                address = val.strip()
            elif pd.notna(val):
                address = str(val)

        crimes.append(Crime(
            date=crime_date,
            time=crime_time,
            type=crime_type,
            description=description,
            latitude=latitude,
            longitude=longitude,
            district=district,
            address=address
        ))

    if not crimes:
        raise Exception("No valid crime records found in CSV")

    # Bulk insert
    db.session.bulk_save_objects(crimes)
    db.session.commit()

    return len(crimes)


@admin_bp.route('/admin', methods=['GET'])
@admin_required
def admin_page():
    """Render the admin panel page."""
    return render_template('admin.html')


@admin_bp.route('/admin/users', methods=['GET'])
@admin_required
def get_users():
    """Get paginated list of users."""
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 25, type=int)

    # Limit per_page to reasonable bounds
    per_page = min(max(per_page, 1), 100)

    pagination = User.query.order_by(User.created_at.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )

    users = [user.to_dict() for user in pagination.items]

    return jsonify({
        'users': users,
        'total': pagination.total,
        'pages': pagination.pages,
        'page': page,
        'per_page': per_page
    }), 200


@admin_bp.route('/admin/users/<int:user_id>', methods=['DELETE'])
@admin_required
def delete_user(user_id):
    """Delete a user by ID."""
    current_user_id = int(get_jwt_identity())

    # Can't delete yourself
    if user_id == current_user_id:
        return jsonify({'error': 'Cannot delete your own account'}), 403

    user = User.query.get(user_id)
    if not user:
        return jsonify({'error': 'User not found'}), 404

    db.session.delete(user)
    db.session.commit()

    return jsonify({'success': True, 'message': 'User deleted successfully'}), 200


@admin_bp.route('/admin/users/<int:user_id>/role', methods=['PUT'])
@admin_required
def update_user_role(user_id):
    """Update a user's role."""
    current_user_id = int(get_jwt_identity())

    # Can't change your own role
    if user_id == current_user_id:
        return jsonify({'error': 'Cannot change your own role'}), 403

    user = User.query.get(user_id)
    if not user:
        return jsonify({'error': 'User not found'}), 404

    data = request.get_json()
    if not data:
        return jsonify({'error': 'Request body is required'}), 400

    new_role = data.get('role')
    if new_role not in ('admin', 'viewer'):
        return jsonify({'error': 'Invalid role. Must be "admin" or "viewer"'}), 400

    user.role = new_role
    db.session.commit()

    return jsonify({
        'success': True,
        'message': 'User role updated successfully',
        'user': user.to_dict()
    }), 200


@admin_bp.route('/admin/upload', methods=['POST'])
@admin_required
def upload_dataset():
    """Upload and ingest a CSV dataset."""
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400

    file = request.files['file']

    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400

    # Validate file type
    if not file.filename.lower().endswith('.csv'):
        return jsonify({'error': 'Invalid file type. Only CSV files are accepted'}), 400

    # Create uploads directory if it doesn't exist
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    uploads_dir = os.path.join(project_root, 'uploads')
    os.makedirs(uploads_dir, exist_ok=True)

    # Generate unique filename with timestamp
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    safe_filename = f"{timestamp}_{file.filename}"
    file_path = os.path.join(uploads_dir, safe_filename)

    try:
        # Save the file
        file.save(file_path)

        # Ingest the data
        records_inserted = ingest_csv_file(file_path)

        return jsonify({
            'success': True,
            'records_inserted': records_inserted,
            'filename': safe_filename,
            'message': f'Successfully ingested {records_inserted} crime records'
        }), 201

    except Exception as e:
        # Clean up file on error
        if os.path.exists(file_path):
            os.remove(file_path)
        return jsonify({'error': f'Failed to process file: {str(e)}'}), 400

    finally:
        # Clean up uploaded file after processing
        if os.path.exists(file_path):
            try:
                os.remove(file_path)
            except OSError:
                pass


@admin_bp.route('/admin/retrain', methods=['POST'])
@admin_required
def start_retrain():
    """Start model retraining in a background thread."""
    job_id = str(uuid.uuid4())

    # Initialize job status
    training_jobs[job_id] = {
        'status': 'running',
        'started_at': datetime.now().isoformat(),
        'completed_at': None,
        'result': None,
        'error': None
    }

    # Start training in background thread
    def train_in_background():
        try:
            # Import the training module
            project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            sys.path.insert(0, project_root)

            from scripts.train_models import main as train_main

            # Run training
            result = train_main()

            # Update job status on success
            training_jobs[job_id]['status'] = 'completed'
            training_jobs[job_id]['completed_at'] = datetime.now().isoformat()
            training_jobs[job_id]['result'] = result

        except Exception as e:
            # Update job status on error
            training_jobs[job_id]['status'] = 'failed'
            training_jobs[job_id]['completed_at'] = datetime.now().isoformat()
            training_jobs[job_id]['error'] = str(e)

    thread = threading.Thread(target=train_in_background)
    thread.daemon = True
    thread.start()

    return jsonify({
        'success': True,
        'message': 'Retraining started in background. Check status for progress.',
        'job_id': job_id
    }), 202


@admin_bp.route('/admin/retrain/status/<job_id>', methods=['GET'])
@admin_required
def get_training_status(job_id):
    """Get the status of a training job."""
    if job_id not in training_jobs:
        return jsonify({'error': 'Job not found'}), 404

    job = training_jobs[job_id]

    return jsonify({
        'job_id': job_id,
        'status': job['status'],
        'started_at': job['started_at'],
        'completed_at': job['completed_at'],
        'result': job['result'],
        'error': job.get('error')
    }), 200