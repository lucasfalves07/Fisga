import argparse
import json
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import tldextract
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, f1_score, precision_score, recall_score, roc_auc_score
from sklearn.model_selection import GroupKFold, GroupShuffleSplit, cross_val_predict
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from app.features.url_features import HOST_FEATURES, analyze_url, host_features
from app.scoring import PESO_REGRAS, regras

LIMIAR = 0.4
_extract = tldextract.TLDExtract(suffix_list_urls=())


def carregar(caminho: str) -> pd.DataFrame:
    df = pd.read_csv(caminho).drop_duplicates("url")
    df["grupo"] = [".".join(p for p in [e.domain, e.suffix] if p) for e in map(_extract, df["url"])]
    return df.reset_index(drop=True)


def montar_x(urls) -> pd.DataFrame:
    return pd.DataFrame([host_features(u) for u in urls], columns=HOST_FEATURES)


def separar(df: pd.DataFrame, teste: float = 0.25, seed: int = 42):
    gss = GroupShuffleSplit(n_splits=1, test_size=teste, random_state=seed)
    idx_treino, idx_teste = next(gss.split(df, df["label"], df["grupo"]))
    return df.iloc[idx_treino].reset_index(drop=True), df.iloc[idx_teste].reset_index(drop=True)


def modelos() -> dict:
    return {
        "Random Forest": RandomForestClassifier(
            n_estimators=300, max_depth=14, min_samples_leaf=3, class_weight="balanced", n_jobs=-1, random_state=42
        ),
        "Regressão logística": make_pipeline(StandardScaler(), LogisticRegression(max_iter=2000, class_weight="balanced")),
    }


def metricas(y, score) -> dict:
    pred = (np.asarray(score) >= LIMIAR).astype(int)
    return {
        "acuracia": round(accuracy_score(y, pred), 3),
        "precisao": round(precision_score(y, pred, zero_division=0), 3),
        "recall": round(recall_score(y, pred), 3),
        "f1": round(f1_score(y, pred), 3),
        "auc": round(roc_auc_score(y, score), 3),
    }


def score_regras(urls) -> np.ndarray:
    return np.array([regras(analyze_url(u).features) for u in urls])


def escolher_peso(treino: pd.DataFrame, modelo) -> tuple[float, dict]:
    x, y = montar_x(treino["url"]), treino["label"].values
    oof = cross_val_predict(modelo, x, y, groups=treino["grupo"], cv=GroupKFold(5), method="predict_proba")[:, 1]
    r = score_regras(treino["url"])
    resultados = {round(w, 1): metricas(y, w * r + (1 - w) * oof)["f1"] for w in np.arange(0, 1.01, 0.1)}
    return max(resultados, key=resultados.get), resultados


def avaliar(df: pd.DataFrame) -> dict:
    treino, teste = separar(df)
    x_tr, y_tr = montar_x(treino["url"]), treino["label"].values
    x_te, y_te = montar_x(teste["url"]), teste["label"].values
    r_te = score_regras(teste["url"])

    resultado = {
        "tamanho": {"treino": len(treino), "teste": len(teste), "dominios_teste": int(teste["grupo"].nunique())},
        "limiar": LIMIAR,
        "teste": {"Só regras": metricas(y_te, r_te)},
        "scores_teste": {"y": y_te.tolist(), "Só regras": r_te.tolist()},
    }

    for nome, modelo in modelos().items():
        modelo.fit(x_tr, y_tr)
        p = modelo.predict_proba(x_te)[:, 1]
        resultado["teste"][nome] = metricas(y_te, p)
        resultado["scores_teste"][nome] = p.tolist()

    rf = modelos()["Random Forest"]
    _, curva = escolher_peso(treino, rf)
    rf.fit(x_tr, y_tr)
    p_rf = rf.predict_proba(x_te)[:, 1]
    combinado = PESO_REGRAS * r_te + (1 - PESO_REGRAS) * p_rf
    resultado["peso_regras"] = PESO_REGRAS
    resultado["curva_peso_validacao"] = curva
    resultado["curva_peso_teste"] = {
        round(w, 1): metricas(y_te, w * r_te + (1 - w) * p_rf) for w in np.arange(0, 1.01, 0.1)
    }
    resultado["teste"]["Regras + Random Forest"] = metricas(y_te, combinado)
    resultado["scores_teste"]["Regras + Random Forest"] = combinado.tolist()
    resultado["importancia"] = dict(
        sorted(zip(HOST_FEATURES, rf.feature_importances_.round(4).tolist()), key=lambda kv: -kv[1])
    )
    return resultado


def treinar_final(df: pd.DataFrame, saida: Path):
    rf = modelos()["Random Forest"]
    rf.fit(montar_x(df["url"]), df["label"].values)
    saida.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(rf, saida, compress=3)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--dados", default="data/processed/urls.csv")
    p.add_argument("--modelo", default="models/url_model.joblib")
    p.add_argument("--metricas", default="models/metricas.json")
    args = p.parse_args()

    df = carregar(args.dados)
    res = avaliar(df)

    print(f"Treino: {res['tamanho']['treino']}  Teste: {res['tamanho']['teste']} ({res['tamanho']['dominios_teste']} domínios nunca vistos)")
    print(f"Peso das regras no app: {res['peso_regras']}\n")
    print(pd.DataFrame(res["teste"]).T.to_string())

    treinar_final(df, Path(args.modelo))
    resumo = {k: v for k, v in res.items() if k != "scores_teste"}
    Path(args.metricas).write_text(json.dumps(resumo, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\nModelo salvo em {args.modelo}")


if __name__ == "__main__":
    main()
