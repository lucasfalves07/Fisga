from functools import lru_cache
from pathlib import Path

import pandas as pd

from app.features.url_features import HOST_FEATURES, host_features, is_official

MODEL_PATH = Path(__file__).resolve().parent.parent / "models" / "url_model.joblib"


@lru_cache(maxsize=1)
def _load():
    if not MODEL_PATH.exists():
        return None
    try:
        import joblib

        return joblib.load(MODEL_PATH)
    except Exception:
        return None


def disponivel() -> bool:
    return _load() is not None


def prob_golpe(url: str) -> float | None:
    model = _load()
    if model is None or is_official(url):
        return None
    x = pd.DataFrame([host_features(url)], columns=HOST_FEATURES)
    return float(model.predict_proba(x)[0][1])
