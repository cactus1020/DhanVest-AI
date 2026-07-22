import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score
import pickle
import os

# 1. Load Real Data
file_path = os.path.join(os.path.dirname(__file__), "..", "real_dse_data.csv")
df = pd.read_csv(file_path)

# Ensure numeric types
numeric_cols = ['ltp', 'high', 'low', 'open', 'close', 'ycp', 'trade', 'value', 'volume']
for col in numeric_cols:
    df[col] = pd.to_numeric(df[col], errors='coerce')

# Feature Engineering
print("Feature Engineering...")
features = []

for symbol, group in df.groupby('symbol'):
    group = group.copy()
    
    # Calculate simple features
    group['return_daily'] = group['close'].pct_change()
    group['ma5'] = group['close'].rolling(5).mean()
    group['ma20'] = group['close'].rolling(20).mean()
    group['vol_ma5'] = group['volume'].rolling(5).mean()
    
    # Momentum indicator
    group['momentum_ratio'] = group['ma5'] / group['ma20']
    
    # Target: 5-day future return > 0 (1 if up, 0 if down)
    group['future_close_5d'] = group['close'].shift(-5)
    group['future_return_5d'] = (group['future_close_5d'] - group['close']) / group['close']
    group['target'] = (group['future_return_5d'] > 0).astype(int)
    
    features.append(group)

df_feat = pd.concat(features).dropna()

X = df_feat[['close', 'volume', 'return_daily', 'momentum_ratio', 'vol_ma5']]
y = df_feat['target']

print(f"Data shape after feature engineering: {X.shape}")

# 2. Train Model
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

print("Training Random Forest Classifier...")
model = RandomForestClassifier(n_estimators=100, max_depth=5, random_state=42)
model.fit(X_train, y_train)

# 3. Evaluate
preds = model.predict(X_test)
acc = accuracy_score(y_test, preds)
print(f"Model Accuracy on Test Data: {acc * 100:.2f}%")

# 4. Save Model
model_path = os.path.join(os.path.dirname(__file__), "dhanvest_model.pkl")
with open(model_path, 'wb') as f:
    pickle.dump(model, f)
    
print(f"Model successfully saved to {model_path}")
