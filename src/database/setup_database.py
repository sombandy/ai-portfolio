#!/usr/bin/env python3
"""
Script to create database schema for portfolio application.
Run this script to set up the PostgreSQL database tables.

Usage:
    python -m src.database.setup_database              # Create tables (preserves existing data)
    python -m src.database.setup_database --drop       # Drop all tables and recreate
"""

import sys
import os
import argparse

# Add the project root to Python path
sys.path.insert(
    0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
)

from src.database.models import create_tables, engine, Base
from sqlalchemy import inspect, text


def check_database_connection():
    """Check if database connection is working."""
    try:
        with engine.connect() as conn:
            print("✓ Database connection successful!")
            return True
    except Exception as e:
        print(f"✗ Database connection failed: {e}")
        return False


def check_existing_tables():
    """Check and list existing tables in the database."""
    inspector = inspect(engine)
    existing_tables = inspector.get_table_names()

    if existing_tables:
        print(f"\nExisting tables in database: {', '.join(existing_tables)}")
    else:
        print("\nNo existing tables found in database.")

    return existing_tables


def drop_tables():
    """Drop all tables defined in the models."""
    try:
        # Drop all tables
        Base.metadata.drop_all(bind=engine)
        print("✓ All tables dropped successfully!")
        return True
    except Exception as e:
        print(f"✗ Error dropping tables: {e}")
        return False


def drop_specific_tables(table_names):
    """Drop specific tables by name."""
    try:
        with engine.connect() as conn:
            for table_name in table_names:
                conn.execute(text(f"DROP TABLE IF EXISTS {table_name} CASCADE"))
                conn.commit()
                print(f"✓ Dropped table: {table_name}")
        return True
    except Exception as e:
        print(f"✗ Error dropping specific tables: {e}")
        return False


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--drop", action="store_true", help="Drop all existing tables")
    args = parser.parse_args()

    print("Portfolio Database Setup")
    print("-" * 50)

    if not check_database_connection():
        print("\nPlease ensure DATABASE_URL is correctly set in .env file")
        print("Example: DATABASE_URL=postgresql://user:password@localhost:5432/dbname")
        sys.exit(1)

    existing_tables = check_existing_tables()
    if args.drop:
        if existing_tables:
            print("\n⚠️  WARNING: --drop flag detected!")
            print("This will DELETE ALL DATA in the following tables:")
            for table in existing_tables:
                print(f"  - {table}")

            print("\nDropping existing tables...")
            if drop_tables():
                print("✓ Tables dropped successfully")
                existing_tables = []  # Update the list
            else:
                print("\nFailed to drop tables. Exiting.")
                sys.exit(1)
        else:
            print("\nNo existing tables to drop.")

    print("\nCreating database tables...")
    try:
        create_tables()
        print("✓ Database tables created successfully!")

        new_tables = check_existing_tables()
        created_tables = set(new_tables) - set(existing_tables)
        if created_tables:
            print(f"✓ New tables created: {', '.join(created_tables)}")

    except Exception as e:
        print(f"✗ Error creating tables: {e}")
        sys.exit(1)

    print("\nDatabase setup completed successfully!")
    print("\nYou can now run your portfolio application and data will be")
    print("automatically saved to the database when summary() is called.")


if __name__ == "__main__":
    main()
