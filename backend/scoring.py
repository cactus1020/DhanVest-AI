import pandas as pd
import os
from supabase import create_client, Client
from dotenv import load_dotenv

def calculate_scores():
    env_path = os.path.join(os.path.dirname(__file__), '..', '..', 'Ai for antigravity', 'ar-shop', '.env')
    load_dotenv(env_path)
    
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
    supabase: Client = create_client(url, key)
    
    stocks_res = supabase.table('stocks').select('*').execute()
    daily_res = supabase.table('daily_data').select('*').order('date').execute()
    
    stocks = stocks_res.data
    daily_data = pd.DataFrame(daily_res.data)
    
    if daily_data.empty:
        print("No daily data available.")
        return
        
    for stock in stocks:
        stock_id = stock['id']
        stock_data = daily_data[daily_data['stock_id'] == stock_id].copy()
        if stock_data.empty:
            continue
            
        latest = stock_data.iloc[-1]
        
        # Fallback for quality and value since real_dse_data.csv doesn't have fundamentals
        quality_score = 50.0
        value_score = 50.0
            
        # MOMENTUM SCORE (0-100)
        # 3 month return (approx 60 trading days)
        if len(stock_data) > 60:
            price_3m_ago = stock_data.iloc[-60]['close_price']
            price_now = latest['close_price']
            if price_3m_ago > 0:
                ret = (price_now - price_3m_ago) / price_3m_ago
                # 20% return in 3m gives 100 score
                momentum_score = min(max((ret + 0.1) / 0.3 * 100, 0), 100)
            else:
                momentum_score = 50.0
        else:
            momentum_score = 50.0
            
        # LIQUIDITY SCORE (0-100)
        avg_vol = stock_data['volume'].tail(20).mean()
        # 200k volume gives 100 score
        liquidity_score = min(max((avg_vol / 200000) * 100, 0), 100)
        
        # --- AI ML PREDICTION (Random Forest) ---
        ai_boost = 0
        try:
            import pickle
            import numpy as np
            model_path = os.path.join(os.path.dirname(__file__), "dhanvest_model.pkl")
            if os.path.exists(model_path):
                with open(model_path, 'rb') as f:
                    model = pickle.load(f)
                
                if len(stock_data) >= 20:
                    ma5 = stock_data['close_price'].tail(5).mean()
                    ma20 = stock_data['close_price'].tail(20).mean()
                    vol_ma5 = stock_data['volume'].tail(5).mean()
                    ret_daily = (latest['close_price'] - stock_data.iloc[-2]['close_price']) / stock_data.iloc[-2]['close_price'] if stock_data.iloc[-2]['close_price'] > 0 else 0
                    mom_ratio = ma5 / ma20 if ma20 > 0 else 1
                    
                    X_input = pd.DataFrame([{
                        'close': latest['close_price'],
                        'volume': latest['volume'],
                        'return_daily': ret_daily,
                        'momentum_ratio': mom_ratio,
                        'vol_ma5': vol_ma5
                    }])
                    
                    prediction = model.predict(X_input)[0]
                    if prediction == 1:
                        ai_boost = 15
        except Exception as e:
            print(f"AI Prediction Error: {e}")
            pass
            
        # COMPOSITE SCORE
        composite_score = (
            quality_score * 0.15 +
            value_score * 0.15 +
            momentum_score * 0.40 + # Weighted heavily since we don't have true fundamentals
            liquidity_score * 0.30
        ) + ai_boost
        
        composite_score = min(composite_score, 100.0)
        
        # Upsert to Supabase
        score_data = {
            "stock_id": stock_id,
            "quality_score": round(quality_score, 2),
            "value_score": round(value_score, 2),
            "momentum_score": round(momentum_score, 2),
            "liquidity_score": round(liquidity_score, 2),
            "composite_score": round(composite_score, 2)
        }
        
        supabase.table('factor_scores').upsert(score_data, on_conflict='stock_id').execute()
            
    print("Scores calculated and updated in Supabase.")

if __name__ == "__main__":
    calculate_scores()
