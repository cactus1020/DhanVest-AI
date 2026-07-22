from database import engine, Base, SessionLocal
import models

# Create all tables in the database
Base.metadata.create_all(bind=engine)

def seed_stocks():
    db = SessionLocal()
    
    # 10 large caps for our initial universe
    initial_stocks = [
        {"symbol": "GP", "name": "Grameenphone Ltd.", "sector": "Telecommunication"},
        {"symbol": "SQURPHARMA", "name": "Square Pharmaceuticals", "sector": "Pharmaceuticals"},
        {"symbol": "BRACBANK", "name": "BRAC Bank Ltd.", "sector": "Bank"},
        {"symbol": "BATBC", "name": "British American Tobacco", "sector": "Food & Allied"},
        {"symbol": "RENATA", "name": "Renata Ltd.", "sector": "Pharmaceuticals"},
        {"symbol": "BXPHARMA", "name": "Beximco Pharmaceuticals", "sector": "Pharmaceuticals"},
        {"symbol": "UPGDCL", "name": "United Power Generation", "sector": "Fuel & Power"},
        {"symbol": "MARICO", "name": "Marico Bangladesh", "sector": "Pharmaceuticals"},
        {"symbol": "LHBL", "name": "LafargeHolcim Bangladesh", "sector": "Cement"},
        {"symbol": "ROBI", "name": "Robi Axiata Limited", "sector": "Telecommunication"}
    ]
    
    for stock_data in initial_stocks:
        stock = db.query(models.Stock).filter(models.Stock.symbol == stock_data["symbol"]).first()
        if not stock:
            new_stock = models.Stock(**stock_data)
            db.add(new_stock)
            
    db.commit()
    db.close()
    print("Database initialized and stocks seeded.")

if __name__ == "__main__":
    seed_stocks()
