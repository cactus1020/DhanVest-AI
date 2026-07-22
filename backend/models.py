from sqlalchemy import Column, Integer, String, Float, Date, ForeignKey
from database import Base

class Stock(Base):
    __tablename__ = "stocks"

    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String, unique=True, index=True)
    name = Column(String)
    sector = Column(String)

class DailyData(Base):
    __tablename__ = "daily_data"

    id = Column(Integer, primary_key=True, index=True)
    stock_id = Column(Integer, ForeignKey("stocks.id"), index=True)
    date = Column(Date, index=True)
    close_price = Column(Float)
    volume = Column(Integer)
    pe_ratio = Column(Float, nullable=True)
    roe = Column(Float, nullable=True)
    debt_to_equity = Column(Float, nullable=True)
    
class FactorScore(Base):
    __tablename__ = "factor_scores"
    
    id = Column(Integer, primary_key=True, index=True)
    stock_id = Column(Integer, ForeignKey("stocks.id"), unique=True, index=True)
    quality_score = Column(Float, default=0.0)
    value_score = Column(Float, default=0.0)
    momentum_score = Column(Float, default=0.0)
    liquidity_score = Column(Float, default=0.0)
    composite_score = Column(Float, default=0.0)
    ai_explanation_bn = Column(String, nullable=True)
    ai_explanation_en = Column(String, nullable=True)
