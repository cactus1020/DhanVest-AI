import os
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import google.generativeai as genai
from fastapi.middleware.cors import CORSMiddleware
from supabase import create_client, Client
from dotenv import load_dotenv

env_path = os.path.join(os.path.dirname(__file__), '..', '..', 'Ai for antigravity', 'ar-shop', '.env')
load_dotenv(env_path)

SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/stocks")
def get_stocks():
    stocks_response = supabase.table('stocks').select('*').execute()
    scores_response = supabase.table('factor_scores').select('*').execute()
    
    stocks = stocks_response.data
    scores = {s['stock_id']: s for s in scores_response.data}
    
    results = []
    for stock in stocks:
        score = scores.get(stock['id'])
        results.append({
            "id": stock['id'],
            "symbol": stock['symbol'],
            "name": stock['name'],
            "sector": stock['sector'],
            "quality": score['quality_score'] if score else 0,
            "value": score['value_score'] if score else 0,
            "momentum": score['momentum_score'] if score else 0,
            "liquidity": score['liquidity_score'] if score else 0,
            "composite": score['composite_score'] if score else 0,
            "explanation_bn": score['ai_explanation_bn'] if score else ""
        })
    return sorted(results, key=lambda x: x['composite'], reverse=True)

class ExplainRequest(BaseModel):
    stock_id: int
    api_key: str

@app.post("/explain")
def generate_explanation(req: ExplainRequest):
    stock_response = supabase.table('stocks').select('*').eq('id', req.stock_id).execute()
    score_response = supabase.table('factor_scores').select('*').eq('stock_id', req.stock_id).execute()
    
    if not stock_response.data or not score_response.data:
        raise HTTPException(status_code=404, detail="Stock not found")
        
    stock = stock_response.data[0]
    score = score_response.data[0]
    
    if not req.api_key:
        raise HTTPException(status_code=400, detail="Gemini API Key is required")
        
    genai.configure(api_key=req.api_key)
    
    prompt = f"""
    You are DhanVest AI, a financial analyst for the Bangladesh Dhaka Stock Exchange.
    Here is the data for {stock['name']} ({stock['symbol']}) in the {stock['sector']} sector:
    - Quality Score: {score['quality_score']}/100
    - Value Score: {score['value_score']}/100
    - Momentum Score: {score['momentum_score']}/100
    - Liquidity Score: {score['liquidity_score']}/100
    - Overall DhanVest Composite Score: {score['composite_score']}/100
    
    Write a 3-sentence explanation in plain, conversational Bangla for a retail investor.
    Highlight exactly ONE strength based on the highest score and ONE risk based on the lowest score.
    CRITICAL RULE: Never predict the future price. Just explain the present scores.
    """
    
    try:
        model = genai.GenerativeModel("gemini-1.5-flash")
        response = model.generate_content(prompt)
        bn_text = response.text
        
        # Save to DB
        supabase.table('factor_scores').update({"ai_explanation_bn": bn_text}).eq('stock_id', req.stock_id).execute()
        
        return {"explanation": bn_text}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
