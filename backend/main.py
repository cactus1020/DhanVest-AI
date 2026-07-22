from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
import google.generativeai as genai
from fastapi.middleware.cors import CORSMiddleware

import models
from database import SessionLocal, engine

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@app.get("/stocks")
def get_stocks(db: Session = Depends(get_db)):
    stocks = db.query(models.Stock).all()
    results = []
    for stock in stocks:
        score = db.query(models.FactorScore).filter(models.FactorScore.stock_id == stock.id).first()
        results.append({
            "id": stock.id,
            "symbol": stock.symbol,
            "name": stock.name,
            "sector": stock.sector,
            "quality": score.quality_score if score else 0,
            "value": score.value_score if score else 0,
            "momentum": score.momentum_score if score else 0,
            "liquidity": score.liquidity_score if score else 0,
            "composite": score.composite_score if score else 0,
            "explanation_bn": score.ai_explanation_bn if score else ""
        })
    return sorted(results, key=lambda x: x['composite'], reverse=True)

class ExplainRequest(BaseModel):
    stock_id: int
    api_key: str

@app.post("/explain")
def generate_explanation(req: ExplainRequest, db: Session = Depends(get_db)):
    stock = db.query(models.Stock).filter(models.Stock.id == req.stock_id).first()
    score = db.query(models.FactorScore).filter(models.FactorScore.stock_id == req.stock_id).first()
    
    if not stock or not score:
        raise HTTPException(status_code=404, detail="Stock not found")
        
    if not req.api_key:
        raise HTTPException(status_code=400, detail="Gemini API Key is required")
        
    genai.configure(api_key=req.api_key)
    
    prompt = f"""
    You are DhanVest AI, a financial analyst for the Bangladesh Dhaka Stock Exchange.
    Here is the data for {stock.name} ({stock.symbol}) in the {stock.sector} sector:
    - Quality Score: {score.quality_score}/100
    - Value Score: {score.value_score}/100
    - Momentum Score: {score.momentum_score}/100
    - Liquidity Score: {score.liquidity_score}/100
    - Overall DhanVest Composite Score: {score.composite_score}/100
    
    Write a 3-sentence explanation in plain, conversational Bangla for a retail investor.
    Highlight exactly ONE strength based on the highest score and ONE risk based on the lowest score.
    CRITICAL RULE: Never predict the future price. Just explain the present scores.
    """
    
    try:
        model = genai.GenerativeModel("gemini-1.5-flash")
        response = model.generate_content(prompt)
        bn_text = response.text
        
        # Save to DB
        score.ai_explanation_bn = bn_text
        db.commit()
        
        return {"explanation": bn_text}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
