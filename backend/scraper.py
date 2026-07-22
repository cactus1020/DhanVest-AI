from database import SessionLocal
import models
import random
from datetime import datetime, timedelta

def seed_historical_data():
    db = SessionLocal()
    stocks = db.query(models.Stock).all()
    
    # We simulate 1 year of daily historical data for each stock to feed the ML/Scoring engine
    # In production, this would be replaced by an API call to AmarStock/DSE Data feed.
    print("Generating 1 year of historical market data...")
    
    end_date = datetime.now().date()
    start_date = end_date - timedelta(days=365)
    
    for stock in stocks:
        current_date = start_date
        
        # Base realistic prices and fundamentals for simulation
        base_price = random.uniform(50.0, 300.0)
        base_pe = random.uniform(10.0, 25.0)
        base_roe = random.uniform(10.0, 35.0)
        
        while current_date <= end_date:
            # Skip weekends (DSE is closed Fri/Sat)
            if current_date.weekday() not in [4, 5]:
                # Random walk for price
                daily_change = random.uniform(-0.02, 0.02)
                base_price = base_price * (1 + daily_change)
                
                # Small fluctuations in fundamentals (usually quarterly, but daily for simulation)
                daily_pe = base_pe + random.uniform(-1.0, 1.0)
                
                data = models.DailyData(
                    stock_id=stock.id,
                    date=current_date,
                    close_price=round(base_price, 2),
                    volume=int(random.uniform(50000, 500000)),
                    pe_ratio=round(daily_pe, 2),
                    roe=round(base_roe, 2),
                    debt_to_equity=round(random.uniform(0.1, 1.5), 2)
                )
                db.add(data)
                
            current_date += timedelta(days=1)
            
    db.commit()
    db.close()
    print("Historical data successfully seeded to database.")

if __name__ == "__main__":
    seed_historical_data()
