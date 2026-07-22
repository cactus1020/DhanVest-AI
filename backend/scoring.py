import pandas as pd
from database import SessionLocal, engine
import models

def calculate_scores():
    db = SessionLocal()
    # Read stocks
    stocks = pd.read_sql("SELECT * FROM stocks", engine)
    
    # Read daily data
    daily_data = pd.read_sql("SELECT * FROM daily_data ORDER BY date", engine)
    
    # We will score each stock
    for _, stock in stocks.iterrows():
        stock_id = stock['id']
        stock_data = daily_data[daily_data['stock_id'] == stock_id].copy()
        if stock_data.empty:
            continue
            
        # Latest fundamentals
        latest = stock_data.iloc[-1]
        
        # QUALITY SCORE (0-100)
        # ROE > 25 is great, Debt < 0.5 is great.
        roe = latest['roe']
        debt = latest['debt_to_equity']
        q_roe = min(max(roe / 25.0 * 100, 0), 100)
        q_debt = min(max((1.5 - debt) / 1.5 * 100, 0), 100)
        quality_score = (q_roe * 0.7) + (q_debt * 0.3)
        
        # VALUE SCORE (0-100)
        pe = latest['pe_ratio']
        if pe <= 0:
            value_score = 0
        else:
            # P/E of 10 is 100 score, P/E of 30 is 0 score
            value_score = max(100 - ((pe - 10) * 5), 0)
            value_score = min(value_score, 100)
            
        # MOMENTUM SCORE (0-100)
        # 3 month return
        if len(stock_data) > 60:
            price_3m_ago = stock_data.iloc[-60]['close_price']
            price_now = latest['close_price']
            ret = (price_now - price_3m_ago) / price_3m_ago
            # 20% return in 3m gives 100 score
            momentum_score = min(max((ret + 0.1) / 0.3 * 100, 0), 100)
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
            import os
            import numpy as np
            model_path = os.path.join(os.path.dirname(__file__), "dhanvest_model.pkl")
            if os.path.exists(model_path):
                with open(model_path, 'rb') as f:
                    model = pickle.load(f)
                
                # Calculate features
                if len(stock_data) >= 20:
                    ma5 = stock_data['close_price'].tail(5).mean()
                    ma20 = stock_data['close_price'].tail(20).mean()
                    vol_ma5 = stock_data['volume'].tail(5).mean()
                    ret_daily = (latest['close_price'] - stock_data.iloc[-2]['close_price']) / stock_data.iloc[-2]['close_price']
                    mom_ratio = ma5 / ma20
                    
                    X_input = pd.DataFrame([{
                        'close': latest['close_price'],
                        'volume': latest['volume'],
                        'return_daily': ret_daily,
                        'momentum_ratio': mom_ratio,
                        'vol_ma5': vol_ma5
                    }])
                    
                    prediction = model.predict(X_input)[0]
                    # If AI predicts an upward trend in 5 days, boost composite score by 15%
                    if prediction == 1:
                        ai_boost = 15
        except Exception as e:
            print(f"AI Prediction Error: {e}")
            pass
            
        # COMPOSITE SCORE
        composite_score = (
            quality_score * 0.32 +
            value_score * 0.28 +
            momentum_score * 0.25 +
            liquidity_score * 0.15
        ) + ai_boost
        
        composite_score = min(composite_score, 100.0)
        
        # Save to DB
        existing_score = db.query(models.FactorScore).filter(models.FactorScore.stock_id == stock_id).first()
        if existing_score:
            existing_score.quality_score = round(quality_score, 2)
            existing_score.value_score = round(value_score, 2)
            existing_score.momentum_score = round(momentum_score, 2)
            existing_score.liquidity_score = round(liquidity_score, 2)
            existing_score.composite_score = round(composite_score, 2)
        else:
            new_score = models.FactorScore(
                stock_id=stock_id,
                quality_score=round(quality_score, 2),
                value_score=round(value_score, 2),
                momentum_score=round(momentum_score, 2),
                liquidity_score=round(liquidity_score, 2),
                composite_score=round(composite_score, 2)
            )
            db.add(new_score)
            
    db.commit()
    db.close()
    print("Scores calculated and updated in the database.")

if __name__ == "__main__":
    calculate_scores()
