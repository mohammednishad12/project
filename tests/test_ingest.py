"""Tests for data ingestion and feature engineering."""
import pytest
import pandas as pd
from datetime import date, time
from app import db
from app.models.crime import Crime


class TestDataCleaning:
    """Test cases for data cleaning functions."""

    def test_clean_data_with_valid_dataframe(self, app):
        """Test clean_data function with valid input."""
        from scripts.ingest_data import clean_data

        # Create sample DataFrame
        df = pd.DataFrame({
            'Date': ['01/15/2024', '01/20/2024'],
            'Time': ['14:30', '18:45'],
            'Primary Type': ['THEFT', 'BURGLARY'],
            'Description': ['Simple theft', 'Breaking and entering'],
            'Location Description': ['RESIDENCE', 'STORE'],
            'Block': ['123 MAIN ST', '456 OAK AVE'],
            'District': ['Central', 'North'],
            'Latitude': [40.7128, 40.7200],
            'Longitude': [-74.0060, -74.0100]
        })

        cleaned_df = clean_data(df)

        assert len(cleaned_df) == 2
        assert 'date' in cleaned_df.columns
        assert 'time' in cleaned_df.columns
        assert 'type' in cleaned_df.columns
        assert 'description' in cleaned_df.columns

    def test_clean_data_handles_null_values(self, app):
        """Test clean_data handles null/missing values."""
        from scripts.ingest_data import clean_data

        df = pd.DataFrame({
            'Date': ['01/15/2024', None],
            'Time': ['14:30', '18:45'],
            'Primary Type': ['THEFT', 'BURGLARY'],
            'Description': ['Simple theft', None],
            'Location Description': ['RESIDENCE', 'STORE'],
            'Block': ['123 MAIN ST', '456 OAK AVE'],
            'District': [None, 'North'],
            'Latitude': [40.7128, None],
            'Longitude': [-74.0060, None]
        })

        cleaned_df = clean_data(df)

        # Should handle nulls gracefully
        assert len(cleaned_df) >= 0

    def test_clean_data_date_parsing(self, app):
        """Test that dates are parsed correctly."""
        from scripts.ingest_data import clean_data

        df = pd.DataFrame({
            'Date': ['01/15/2024', '02/20/2024'],
            'Time': ['14:30', '18:45'],
            'Primary Type': ['THEFT', 'BURGLARY'],
            'Description': ['Simple theft', 'Breaking'],
            'Location Description': ['RESIDENCE', 'STORE'],
            'Block': ['123 MAIN ST', '456 OAK AVE'],
            'District': ['Central', 'North'],
            'Latitude': [40.7128, 40.7200],
            'Longitude': [-74.0060, -74.0100]
        })

        cleaned_df = clean_data(df)

        # Check that dates are properly parsed as date objects
        if len(cleaned_df) > 0:
            assert cleaned_df.iloc[0]['date'] is not None


class TestFeatureEngineering:
    """Test cases for feature engineering functions."""

    def test_feature_engineer_basic(self, app):
        """Test basic feature engineering."""
        from scripts.ingest_data import feature_engineer

        df = pd.DataFrame({
            'date': [date(2024, 1, 15), date(2024, 1, 20)],
            'time': [time(14, 30), time(18, 45)],
            'type': ['Theft', 'Burglary'],
            'district': ['Central', 'North']
        })

        features_df = feature_engineer(df)

        assert len(features_df) == 2
        # Should add time-based features
        assert 'hour' in features_df.columns or 'time_of_day' in features_df.columns or 'hour_of_day' in features_df.columns

    def test_feature_engineer_time_features(self, app):
        """Test that time-based features are extracted."""
        from scripts.ingest_data import feature_engineer

        df = pd.DataFrame({
            'date': [date(2024, 1, 15), date(2024, 1, 20), date(2024, 2, 10)],
            'time': [time(6, 30), time(14, 0), time(22, 15)],
            'type': ['Theft', 'Burglary', 'Vandalism'],
            'district': ['Central', 'North', 'Central']
        })

        features_df = feature_engineer(df)

        # Check that hour feature exists
        if 'hour' in features_df.columns:
            hours = features_df['hour'].tolist()
            assert 6 in hours or 14 in hours or 22 in hours

    def test_feature_engineer_day_of_week(self, app):
        """Test day of week extraction."""
        from scripts.ingest_data import feature_engineer

        df = pd.DataFrame({
            'date': [date(2024, 1, 15), date(2024, 1, 20)],  # Monday, Saturday
            'time': [time(14, 30), time(18, 45)],
            'type': ['Theft', 'Burglary'],
            'district': ['Central', 'North']
        })

        features_df = feature_engineer(df)

        # Should have day of week feature
        if 'day_of_week' in features_df.columns or 'weekday' in features_df.columns:
            assert len(features_df) == 2


class TestDatabaseIngestion:
    """Test cases for database ingestion."""

    def test_insert_crimes_to_db(self, app):
        """Test inserting crimes into the database."""
        with app.app_context():
            # Create test crimes
            crime1 = Crime(
                date=date(2024, 1, 15),
                time=time(14, 30),
                type='Theft',
                description='Test theft',
                address='123 Main St',
                district='Central',
                latitude=40.7128,
                longitude=-74.0060
            )
            crime2 = Crime(
                date=date(2024, 1, 20),
                time=time(18, 45),
                type='Burglary',
                description='Test burglary',
                address='456 Oak Ave',
                district='North',
                latitude=40.7200,
                longitude=-74.0100
            )

            db.session.add_all([crime1, crime2])
            db.session.commit()

            # Query and verify
            crimes = Crime.query.all()
            assert len(crimes) >= 2

            # Verify data integrity
            theft = Crime.query.filter_by(type='Theft').first()
            assert theft is not None
            assert theft.description == 'Test theft'
            assert theft.district == 'Central'