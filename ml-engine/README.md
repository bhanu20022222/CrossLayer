# CrossLayer ML Engine

## Status: Month 6 Milestone

The Python ML engine will be implemented in Month 6 of the development roadmap.

## Planned Models
| Model | Purpose |
|-------|---------|
| Linear Regression | Initial interpretable baseline |
| Random Forest | Nonlinear suitability prediction |
| XGBoost | Advanced tabular prediction |
| Decision Tree | Explainable decision baseline |

## Planned Pipeline
1. Prometheus metrics → Feature Extraction
2. Historical Dataset creation
3. Data Cleaning and Feature Engineering
4. Train / Validation / Test split
5. Model Training
6. Model Evaluation (MAE, RMSE, R², Precision, Recall, F1)
7. Prediction API (FastAPI)
8. Go Controller integration

## Technologies
- pandas, NumPy, scikit-learn
- FastAPI for prediction API
- Joblib for model serialisation
