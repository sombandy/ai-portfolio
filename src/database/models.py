"""
Database models and operations for portfolio data storage.
Author: somnath.banerjee
"""

import os
from datetime import datetime, date
from typing import Any

from sqlalchemy import create_engine, Column, Float, Integer, Date, DateTime, UniqueConstraint
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise ValueError("DATABASE_URL not found in environment variables")

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
    gain_pct = Column(Float(precision=2), nullable=False)
    day_change = Column(Float(precision=2), nullable=False)
    day_change_value = Column(Integer, nullable=False)
    updated_at = Column(DateTime, default=lambda: datetime.now().replace(microsecond=0),
                    onupdate=lambda: datetime.now().replace(microsecond=0))

    __table_args__ = (
        UniqueConstraint('date', name='uq_portfolio_summary_date'),
    )


def create_tables():
    """
    Create all tables in the database.
    """
    Base.metadata.create_all(bind=engine)
    print("Database tables created successfully!")



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
        
        total_value = data.get('Total', '0')
        market_value = data.get('Market Value', '0')
        gain_value = data.get('Gain', '0')
        gain_pct_value = data.get('Gain%', '0')
        day_change_value = data.get('Day Change', '0')
        day_change_val = data.get('Day Change Value', '0')
        gain_pct_value = round(float(gain_pct_value), 2)
        day_change_value = round(float(day_change_value), 2)

        entry = PortfolioSummary(
            date=today,
            total=total_value,
            market_value=market_value,
            gain=gain_value,
            gain_pct=gain_pct_value,
            day_change=day_change_value,
            day_change_value=day_change_val,
        )
        session.merge(entry)
        session.commit()
        print(f"Portfolio summary updated for {today}")
        
    except Exception as e:
        session.rollback()
        print(f"Error updating portfolio summary: {e}")
        raise
    finally:
        session.close()
