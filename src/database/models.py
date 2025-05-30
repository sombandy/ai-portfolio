"""
Database models and operations for portfolio data storage.
Author: somnath.banerjee
"""

import os
from datetime import datetime, date
from typing import Dict, Any

from sqlalchemy import create_engine, Column, String, Float, Integer, Date, DateTime, UniqueConstraint
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.dialects.postgresql import insert
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Database configuration
DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise ValueError("DATABASE_URL not found in environment variables")

# Fix for SQLAlchemy 2.0+ - replace postgres:// with postgresql://
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

# Create engine and session
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


class PortfolioSummary(Base):
    """
    Table to store daily portfolio summary data.
    """
    __tablename__ = "portfolio_summary"
    
    date = Column(Date, primary_key=True, default=date.today)    
    total = Column(Integer, nullable=False)
    market_value = Column(Integer, nullable=False)
    gain = Column(Integer, nullable=False)
    gain_pct = Column(Float, nullable=False)
    day_change = Column(Float, nullable=False)
    day_change_value = Column(Integer, nullable=False)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    __table_args__ = (
        UniqueConstraint('date', name='uq_portfolio_summary_date'),
    )


def create_tables():
    """
    Create all tables in the database.
    """
    Base.metadata.create_all(bind=engine)
    print("Database tables created successfully!")


def parse_currency_string(value: str) -> int:
    """
    Parse currency string to integer.
    Examples: '$100,000' -> 100000, '$1,234.56' -> 1234
    """
    if isinstance(value, (int, float)):
        return int(value)
    # Remove dollar sign and commas, then convert to int
    cleaned = value.replace('$', '').replace(',', '')
    # Handle decimal values by converting to float first then int
    return int(float(cleaned))


def parse_percentage_string(value: str) -> float:
    """
    Parse percentage string to float.
    Examples: '25.50%' -> 25.50, '-1.23%' -> -1.23
    """
    if isinstance(value, (int, float)):
        return round(float(value), 2)
    # Remove percentage sign and convert to float
    cleaned = value.replace('%', '').strip()
    return round(float(cleaned), 2)


def update_total(t: Any) -> None:
    """
    Update or insert portfolio summary data for today's date.
    
    Args:
        t: DataFrame with single row containing portfolio summary data
    """
    session = SessionLocal()
    try:
        if hasattr(t, 'to_dict'):
            data = t.to_dict('records')[0]
        else:
            data = dict(t)
        
        today = date.today()
        
        total_value = parse_currency_string(data.get('Total', '0'))
        market_value = parse_currency_string(data.get('Market Value', '0'))
        gain_value = parse_currency_string(data.get('Gain', '0'))
        gain_pct_value = parse_percentage_string(data.get('Gain%', '0'))
        day_change_value = parse_percentage_string(data.get('Day Change', '0'))
        day_change_val = parse_currency_string(data.get('Day Change Value', '0'))
        
        stmt = insert(PortfolioSummary).values(
            date=today,
            total=total_value,
            market_value=market_value,
            gain=gain_value,
            gain_pct=gain_pct_value,
            day_change=day_change_value,
            day_change_value=day_change_val,
        )
        
        stmt = stmt.on_conflict_do_update(
            index_elements=['date'],
            set_={
                'total': stmt.excluded.total,
                'market_value': stmt.excluded.market_value,
                'gain': stmt.excluded.gain,
                'gain_pct': stmt.excluded.gain_pct,
                'day_change': stmt.excluded.day_change,
                'day_change_value': stmt.excluded.day_change_value,
            }
        )
        
        session.execute(stmt)
        session.commit()
        print(f"Portfolio summary updated for {today}")
        
    except Exception as e:
        session.rollback()
        print(f"Error updating portfolio summary: {e}")
        raise
    finally:
        session.close()

