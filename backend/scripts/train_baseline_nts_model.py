import os
import pickle
from sklearn.ensemble import RandomForestRegressor
import numpy as np

def train():
    # Synthetic data
    X = np.random.rand(100, 10)
    y = np.random.rand(100) * 100

    model = RandomForestRegressor(n_estimators=10)
    model.fit(X, y)

    os.makedirs('models', exist_ok=True)
    path = 'models/baseline_nts.pkl'
    with open(path, 'wb') as f:
        pickle.dump(model, f)
    
    print(f"Model saved to {path}")

if __name__ == '__main__':
    train()
