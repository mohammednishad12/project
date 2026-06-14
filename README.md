# Crime Data Visualization and Prediction System

A comprehensive Flask-based web application for visualizing crime data, analyzing patterns, generating reports, and building predictive models using machine learning.

## Table of Contents

- [Overview](#overview)
- [Tech Stack](#tech-stack)
- [Directory Structure](#directory-structure)
- [Setup Instructions](#setup-instructions)
- [Loading Sample Data](#loading-sample-data)
- [Training Models](#training-models)
- [Running Tests](#running-tests)
- [API Documentation](#api-documentation)
- [Database Schema](#database-schema)
- [Authentication](#authentication)
- [Report Generation](#report-generation)
- [Admin Panel](#admin-panel)
- [Environment Variables](#environment-variables)
- [Contributing](#contributing)
- [License](#license)

---

## Overview

This system provides law enforcement agencies and analysts with tools to:

- Visualize crime data on interactive maps and charts
- Search and filter crime records with advanced query capabilities
- Generate comprehensive PDF reports for specific time periods and areas
- Predict crime trends using machine learning models (Random Forest, LSTM)
- Manage users with role-based access control (admin/viewer)

---

## Tech Stack

| Component | Technology |
|-----------|------------|
| **Backend Framework** | Flask 3.0.0 |
| **Database** | SQLAlchemy + SQLite (dev) / MySQL (prod) |
| **Authentication** | Flask-JWT-Extended, Flask-Login, bcrypt |
| **Data Processing** | Pandas, NumPy |
| **Machine Learning** | scikit-learn, TensorFlow/Keras |
| **Visualization** | Matplotlib, Seaborn, Folium |
| **Report Generation** | ReportLab |
| **Testing** | pytest |
| **Frontend** | HTML5, JavaScript, Bootstrap (templates) |

---

## Directory Structure

```
crime-prediction-system/
├── app/
│   ├── __init__.py          # Flask app factory, extensions, blueprints
│   ├── models/
│   │   ├── __init__.py
│   │   ├── crime.py         # Crime model
│   │   ├── user.py          # User model with roles
│   │   ├── prediction.py    # Prediction model
│   │   └── report.py        # Report model
│   ├── routes/
│   │   ├── auth.py          # Authentication endpoints
│   │   ├── dashboard.py     # Dashboard web routes
│   │   ├── predict.py       # Prediction web routes
│   │   ├── search.py        # Search web routes
│   │   ├── reports.py       # Reports web routes
│   │   ├── admin.py         # Admin web routes
│   │   ├── api_dashboard.py # Dashboard API endpoints
│   │   ├── api_predict.py   # Prediction API endpoints
│   │   ├── api_search.py    # Search API endpoints
│   │   ├── api_reports.py   # Reports API endpoints
│   │   └── api_admin.py     # Admin API endpoints
│   ├── ml/
│   │   ├── __init__.py
│   │   └── predict.py       # ML prediction utilities
│   └── utils/
│       ├── __init__.py
│       ├── decorators.py    # Role-based access decorators
│       └── pdf_generator.py # PDF report generation
├── scripts/
│   ├── ingest_data.py       # Data ingestion and cleaning
│   ├── load_sample_data.py  # Load sample crime data
│   └── train_models.py      # Train ML models
├── tests/
│   ├── __init__.py
│   ├── conftest.py          # Pytest fixtures
│   ├── test_auth.py         # Authentication tests
│   ├── test_api.py          # API endpoint tests
│   └── test_ingest.py       # Data ingestion tests
├── notebooks/
│   ├── eda.ipynb            # Exploratory Data Analysis
│   └── model_prototyping.ipynb # Model prototyping notebook
├── templates/               # HTML templates
├── config.py                # Configuration classes
├── run.py                   # Application entry point
├── requirements.txt         # Python dependencies
└── README.md                # This file
```

---

## Setup Instructions

### Prerequisites

- Python 3.9+
- pip (Python package manager)
- Git

### 1. Clone the Repository

```bash
git clone <repository-url>
cd crime-prediction-system
```

### 2. Create Virtual Environment

```bash
# Create virtual environment
python -m venv venv

# Activate it
# On Linux/Mac:
source venv/bin/activate

# On Windows:
venv\Scripts\activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure Environment Variables

```bash
# Copy the example environment file
cp .env.example .env

# Edit .env with your configuration
# Use a strong SECRET_KEY and JWT_SECRET_KEY in production
```

### 5. Initialize Database

```bash
# The database will be created automatically on first run
# Or manually initialize:
python -c "from app import create_app, db; app = create_app(); app.app_context().push(); db.create_all()"
```

### 6. Run the Application

```bash
python run.py
```

The application will start on `http://localhost:5000` (or the port specified in `.env`).

---

## Loading Sample Data

To load sample crime data into the database:

```bash
python scripts/load_sample_data.py
```

This script will:
1. Generate synthetic crime data covering 2023-2024
2. Include various crime types (Theft, Burglary, Vandalism, Assault, Robbery, etc.)
3. Distribute data across multiple districts
4. Insert records into the database

To customize the sample data generation, edit `scripts/load_sample_data.py`.

---

## Training Models

To train the machine learning models:

```bash
python scripts/train_models.py
```

This script will:
1. Load crime data from the database
2. Preprocess data and create features
3. Train Random Forest classifier for crime type prediction
4. Train Linear Regression for crime count forecasting
5. Train LSTM neural network for time-series prediction
6. Save models to the `models/` directory

Training outputs:
- `models/rf_classifier.pkl` - Random Forest model
- `models/linear_regression.pkl` - Linear Regression model
- `models/lstm_model.keras` - LSTM neural network

---

## Running Tests

Run all tests with pytest:

```bash
pytest tests/ -v
```

Run specific test files:

```bash
# Test authentication
pytest tests/test_auth.py -v

# Test API endpoints
pytest tests/test_api.py -v

# Test data ingestion
pytest tests/test_ingest.py -v
```

Run with coverage:

```bash
pytest tests/ --cov=app --cov-report=html
```

---

## API Documentation

### Authentication Endpoints

| Endpoint | Method | Description | Auth Required |
|----------|--------|-------------|---------------|
| `/auth/register` | POST | Register a new user | No |
| `/auth/login` | POST | Login and get JWT tokens | No |
| `/auth/logout` | POST | Logout and invalidate tokens | Yes |
| `/auth/me` | GET | Get current user info | Yes |
| `/auth/refresh` | POST | Refresh access token | Yes (refresh token) |
| `/auth/verify` | GET | Verify JWT token validity | Yes |

#### Register Example
```bash
curl -X POST http://localhost:5000/auth/register \
  -H "Content-Type: application/json" \
  -d '{"username": "analyst", "email": "analyst@example.com", "password": "secure123"}'
```

#### Login Example
```bash
curl -X POST http://localhost:5000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "analyst", "password": "secure123"}'
```

### Dashboard API Endpoints

| Endpoint | Method | Description | Auth Required |
|----------|--------|-------------|---------------|
| `/api/stats` | GET | Get aggregated crime statistics | No |
| `/api/heatmap` | GET | Get GeoJSON for heatmap visualization | No |

#### Stats Parameters
- `start` - Start date (YYYY-MM-DD)
- `end` - End date (YYYY-MM-DD)
- `types` - Comma-separated crime types
- `area` - District name filter

#### Example
```bash
curl "http://localhost:5000/api/stats?start=2024-01-01&end=2024-01-31&area=Central"
```

### Search API Endpoints

| Endpoint | Method | Description | Auth Required |
|----------|--------|-------------|---------------|
| `/api/crimes` | GET | Search crimes with filters and pagination | No |
| `/api/crimes/areas` | GET | Get list of distinct districts | No |
| `/api/crimes/types` | GET | Get list of crime types | No |

#### Search Parameters
- `query` - Full-text search query
- `area` - District filter (case-insensitive partial match)
- `type` - Crime type filter (exact or comma-separated)
- `start` - Start date (YYYY-MM-DD)
- `end` - End date (YYYY-MM-DD)
- `time_of_day` - Morning/Afternoon/Evening/Night
- `page` - Page number (default: 1)
- `per_page` - Items per page (default: 25, max: 100)

#### Example
```bash
curl "http://localhost:5000/api/crimes?area=Central&type=Theft&page=1&per_page=50"
```

#### Response Format
```json
{
  "items": [...],
  "total": 1234,
  "pages": 25,
  "page": 1,
  "per_page": 50,
  "has_next": true,
  "has_prev": false
}
```

### Prediction API Endpoints

| Endpoint | Method | Description | Auth Required |
|----------|--------|-------------|---------------|
| `/api/predict/type` | POST | Predict crime type | No |
| `/api/predict/count` | POST | Predict crime count | No |
| `/api/predict/trend` | GET | Get crime trend forecast | No |

### Reports API Endpoints

| Endpoint | Method | Description | Auth Required |
|----------|--------|-------------|---------------|
| `/api/report/generate` | POST | Generate a new report | Yes |
| `/api/report/preview` | GET | Preview report summary | Yes |
| `/api/reports` | GET | List user's reports | Yes |
| `/api/reports/<id>` | GET | Get specific report | Yes |
| `/api/reports/<id>` | DELETE | Delete a report | Yes (owner/admin) |

### Admin API Endpoints

| Endpoint | Method | Description | Auth Required |
|----------|--------|-------------|---------------|
| `/api/admin/users` | GET | List all users | Yes (admin) |
| `/api/admin/users/<id>` | PUT | Update user role | Yes (admin) |
| `/api/admin/users/<id>` | DELETE | Delete user | Yes (admin) |
| `/api/admin/stats` | GET | Get system statistics | Yes (admin) |

---

## Database Schema

### Users Table

| Column | Type | Description |
|--------|------|-------------|
| `id` | INTEGER (PK) | Unique identifier |
| `username` | VARCHAR(80) | Unique username |
| `email` | VARCHAR(120) | Unique email address |
| `password_hash` | VARCHAR(255) | Bcrypt hashed password |
| `role` | VARCHAR(20) | 'admin' or 'viewer' |
| `created_at` | DATETIME | Creation timestamp |

### Crimes Table

| Column | Type | Description |
|--------|------|-------------|
| `id` | INTEGER (PK) | Unique identifier |
| `date` | DATE | Crime date |
| `time` | TIME | Crime time |
| `type` | VARCHAR(100) | Crime type (e.g., Theft, Burglary) |
| `description` | TEXT | Crime description |
| `address` | VARCHAR(255) | Location address |
| `district` | VARCHAR(100) | District/area name |
| `latitude` | FLOAT | GPS latitude |
| `longitude` | FLOAT | GPS longitude |
| `created_at` | DATETIME | Record creation timestamp |

### Predictions Table

| Column | Type | Description |
|--------|------|-------------|
| `id` | INTEGER (PK) | Unique identifier |
| `user_id` | INTEGER (FK) | User who made prediction |
| `prediction_type` | VARCHAR(50) | Type/count/trend |
| `input_data` | JSON | Input parameters |
| `result` | JSON | Prediction results |
| `model_used` | VARCHAR(50) | Model name/version |
| `created_at` | DATETIME | Prediction timestamp |

### Reports Table

| Column | Type | Description |
|--------|------|-------------|
| `id` | INTEGER (PK) | Unique identifier |
| `user_id` | INTEGER (FK) | Report owner |
| `title` | VARCHAR(200) | Report title |
| `report_type` | VARCHAR(50) | Type of report |
| `parameters` | JSON | Report parameters |
| `file_path` | VARCHAR(255) | Path to generated PDF |
| `status` | VARCHAR(20) | pending/completed/failed |
| `created_at` | DATETIME | Creation timestamp |
| `completed_at` | DATETIME | Completion timestamp |

---

## Authentication

The system uses JWT (JSON Web Tokens) for API authentication:

### Token Structure

**Access Token**: Short-lived token (15 minutes) sent in `Authorization: Bearer <token>` header.

**Refresh Token**: Long-lived token (30 days) stored in HTTP-only cookie.

### Roles

| Role | Permissions |
|------|-------------|
| `viewer` | View dashboard, search crimes, generate reports |
| `admin` | All viewer permissions + user management + system stats |

### Password Security

- Passwords are hashed using bcrypt with automatic salt generation
- Minimum password length: 6 characters
- Passwords never stored in plain text

### JWT Claims

```json
{
  "sub": "<user_id>",
  "role": "viewer|admin",
  "exp": "<expiration_timestamp>",
  "iat": "<issued_at_timestamp>"
}
```

---

## Report Generation

Generate PDF reports through the web interface or API:

### Report Types

1. **Crime Summary Report** - Overview of crime statistics for a period
2. **District Analysis Report** - Detailed analysis for specific districts
3. **Trend Report** - Crime trend analysis with predictions
4. **Incident Report** - List of specific incidents matching criteria

### Parameters

- `start_date` - Report start date
- `end_date` - Report end date
- `area` - Optional district filter
- `crime_types` - Optional crime type filter
- `include_predictions` - Include ML predictions (boolean)

### Example API Request

```bash
curl -X POST http://localhost:5000/api/report/generate \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "January 2024 Crime Summary",
    "report_type": "summary",
    "parameters": {
      "start_date": "2024-01-01",
      "end_date": "2024-01-31",
      "area": "Central",
      "include_predictions": true
    }
  }'
```

---

## Admin Panel

The admin panel provides:

- **User Management**: Create, update, delete users; change roles
- **System Statistics**: View usage statistics, active users
- **Data Management**: Monitor data quality, import/export data
- **Model Management**: View model performance metrics

Access admin features at `/admin` (requires admin role).

---

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `FLASK_ENV` | Environment mode | `development` |
| `SECRET_KEY` | Flask secret key for sessions | Auto-generated (dev) |
| `JWT_SECRET_KEY` | JWT signing key | Auto-generated (dev) |
| `DATABASE_URL` | SQLAlchemy database URI | `sqlite:///crime_data.db` |
| `PORT` | Application port | `5000` |

### Database URL Examples

```bash
# SQLite (development)
DATABASE_URL=sqlite:///crime_data.db

# SQLite with absolute path
DATABASE_URL=sqlite:////absolute/path/to/crime_data.db

# MySQL (production)
DATABASE_URL=mysql+pymysql://user:password@localhost/crime_data_prod

# PostgreSQL
DATABASE_URL=postgresql://user:password@localhost/crime_data_prod
```

---

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

### Code Style

- Follow PEP 8 guidelines
- Use meaningful variable and function names
- Add docstrings to functions and classes
- Include type hints where applicable
- Write tests for new features

---

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## Support

For issues and feature requests, please open an issue on the repository.

---

## Acknowledgments

- Crime data visualization powered by Folium and Leaflet.js
- Machine learning models using scikit-learn and TensorFlow
- PDF generation using ReportLab

---

## Adding Your Own Dataset

Place your CSV file as `data/crime_dataset_modified.csv`, then run:

```bash
# Append to existing data
python3 scripts/load_modified_csv.py

# Replace all existing data
python3 scripts/load_modified_csv.py --replace

# Load a different file
python3 scripts/load_modified_csv.py --file path/to/your.csv
```

Required CSV columns (auto-detected by name):
- `date` / `Date` / `crime_date` / `dt`
- `time` / `Time` / `hour` (optional)
- `type` / `Type` / `crime_type` / `Crime_Type`
- `latitude` / `lat` / `Lat`
- `longitude` / `lng` / `lon` / `Long`
- `district` / `District` / `city` / `City` / `state`
- `address` / `Address` / `location` / `street`
- `description` / `Description` / `desc` / `details`

After loading, the app automatically retrains all ML models.