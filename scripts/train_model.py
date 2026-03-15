"""
XGBoost Model Training — Claim Denial Risk Predictor
Run: python train_model.py
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, classification_report

try:
    import xgboost as xgb
    HAS_XGB = True
except ImportError:
    HAS_XGB = False
    print("⚠ XGBoost not installed. Run: pip install xgboost")


def generate_synthetic_data(n_samples=2000):
    """Generate synthetic training data for claim denial prediction."""
    np.random.seed(42)

    # Features
    cpt_risk = np.random.uniform(0.1, 0.95, n_samples)       # CPT code risk factor
    billed_norm = np.random.uniform(0.01, 1.0, n_samples)     # Normalized billed amount
    prior_auth = np.random.binomial(1, 0.3, n_samples).astype(float)  # Prior auth required
    doc_required = np.random.binomial(1, 0.4, n_samples).astype(float) # Documentation required
    compliance = np.random.uniform(0.4, 1.0, n_samples)       # Provider compliance score
    impact = np.random.uniform(0.1, 0.95, n_samples)          # Policy impact level

    X = np.column_stack([cpt_risk, billed_norm, prior_auth, doc_required, compliance, impact])

    # Generate labels (denied = 1, approved = 0)
    # Higher risk when: high CPT risk, high billed amount, missing auth, low compliance, high impact
    denial_prob = (
        cpt_risk * 0.25 +
        billed_norm * 0.15 +
        prior_auth * 0.15 +
        doc_required * 0.10 +
        (1 - compliance) * 0.25 +
        impact * 0.10
    )
    # Add noise
    denial_prob += np.random.normal(0, 0.08, n_samples)
    denial_prob = np.clip(denial_prob, 0, 1)

    y = (denial_prob > 0.45).astype(int)

    return X, y


def train_model():
    """Train XGBoost model and save to file."""
    if not HAS_XGB:
        print("❌ XGBoost is required. Install with: pip install xgboost")
        return

    print("=" * 50)
    print("  XGBoost Claim Denial Risk Model Training")
    print("=" * 50)

    # Check for real data
    excel_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "healthcare_compliance_cleaned.xlsx")
    if os.path.exists(excel_path):
        print(f"📊 Loading real data from {excel_path}")
        try:
            df = pd.read_excel(excel_path)
            # Try to extract features — adjust column names as needed
            print(f"   Columns: {list(df.columns)}")
            print(f"   Rows: {len(df)}")
        except Exception as e:
            print(f"   ⚠ Could not load Excel: {e}")

    # Generate synthetic data
    print("\n📊 Generating synthetic training data...")
    X, y = generate_synthetic_data(2000)
    print(f"   Samples: {len(X)}, Features: {X.shape[1]}")
    print(f"   Denied: {sum(y)}, Approved: {len(y) - sum(y)}")

    # Split
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

    # Train
    print("\n🚀 Training XGBoost model...")
    model = xgb.XGBClassifier(
        n_estimators=150,
        max_depth=5,
        learning_rate=0.1,
        subsample=0.8,
        colsample_bytree=0.8,
        eval_metric="logloss",
        random_state=42,
    )
    model.fit(X_train, y_train, eval_set=[(X_test, y_test)], verbose=False)

    # Evaluate
    y_pred = model.predict(X_test)
    accuracy = accuracy_score(y_test, y_pred)
    print(f"\n📈 Model Accuracy: {accuracy:.4f}")
    print("\nClassification Report:")
    print(classification_report(y_test, y_pred, target_names=["Approved", "Denied"]))

    # Feature importance
    feature_names = ["CPT Risk", "Billed Amount", "Prior Auth", "Documentation", "Compliance", "Policy Impact"]
    importances = model.feature_importances_
    print("Feature Importance:")
    for name, imp in sorted(zip(feature_names, importances), key=lambda x: -x[1]):
        bar = "█" * int(imp * 40)
        print(f"   {name:20s} {imp:.4f} {bar}")

    # Save model
    model_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "models")
    os.makedirs(model_dir, exist_ok=True)
    model_path = os.path.join(model_dir, "xgboost_model.json")
    model.save_model(model_path)
    print(f"\n✅ Model saved to {model_path}")


if __name__ == "__main__":
    train_model()
