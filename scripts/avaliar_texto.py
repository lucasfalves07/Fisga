import argparse
import hashlib
import json
import os
import time
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv

from app.features.header_checks import extract_urls
from app.llm.analyzer import heuristic, llm
from app.scoring import combinar_email, score_url
from scripts.treinar_modelo import metricas

load_dotenv()

CACHE = Path("data/processed/llm_cache.json")


def _chave(texto: str) -> str:
    modelo = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
    return hashlib.sha1(f"{modelo}|{texto}".encode()).hexdigest()


def notas_llm(textos: list[str], pausa: float) -> tuple[list[float | None], int]:
    cache = json.loads(CACHE.read_text(encoding="utf-8")) if CACHE.exists() else {}
    notas, falhas = [], 0
    for i, t in enumerate(textos, 1):
        k = _chave(t)
        if k not in cache:
            for tentativa in range(4):
                try:
                    cache[k] = llm("", t)["score"]
                    break
                except Exception as e:
                    espera = 20 * (tentativa + 1) if "429" in str(e) or "rate" in str(e).lower() else 3
                    print(f"  [{i}] erro ({type(e).__name__}), tentando de novo em {espera}s")
                    time.sleep(espera)
            CACHE.parent.mkdir(parents=True, exist_ok=True)
            CACHE.write_text(json.dumps(cache), encoding="utf-8")
            time.sleep(pausa)
        if k in cache:
            notas.append(cache[k])
        else:
            notas.append(None)
            falhas += 1
        if i % 20 == 0:
            print(f"  LLM: {i}/{len(textos)}")
    return notas, falhas


def url_max(texto: str) -> tuple[float, bool]:
    urls = extract_urls(texto)
    return max((score_url(u)["score"] for u in urls), default=0.0), bool(urls)


def avaliar(df: pd.DataFrame, usar_llm: bool, pausa: float) -> dict:
    y = df["label"].values
    links = [url_max(t) for t in df["texto"]]
    heur = [heuristic("", t)["score"] for t in df["texto"]]

    scores = {
        "Heurística (só texto)": heur,
        "Fisga com heurística": [combinar_email(h, u, 0, tem)[0] for h, (u, tem) in zip(heur, links)],
    }

    falhas = 0
    if usar_llm:
        notas, falhas = notas_llm(df["texto"].tolist(), pausa)
        ok = [n is not None for n in notas]
        if not all(ok):
            print(f"Aviso: {falhas} mensagens sem resposta do LLM ficaram de fora da comparação.")
        df, y = df[ok].reset_index(drop=True), y[ok]
        scores = {k: [v for v, o in zip(vs, ok) if o] for k, vs in scores.items()}
        links = [l for l, o in zip(links, ok) if o]
        notas = [n for n in notas if n is not None]
        scores["LLM (só texto)"] = notas
        scores["Fisga com LLM"] = [combinar_email(n, u, 0, tem)[0] for n, (u, tem) in zip(notas, links)]

    resultado = {
        "mensagens": len(df),
        "golpes": int(y.sum()),
        "falhas_llm": falhas,
        "teste": {nome: metricas(y, s) for nome, s in scores.items()},
        "recall_por_categoria": {},
        "erros": {},
    }
    golpes = df["label"] == 1
    for nome, s in scores.items():
        pred = pd.Series(s) >= 0.4
        resultado["recall_por_categoria"][nome] = (
            pred[golpes].groupby(df.loc[golpes, "categoria"]).mean().round(2).to_dict()
        )
        resultado["erros"][nome] = {
            "falsos_negativos": df.loc[golpes & ~pred, "texto"].tolist(),
            "falsos_positivos": df.loc[~golpes & pred, "texto"].tolist(),
        }
    return resultado


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--dados", default="data/mensagens.csv")
    p.add_argument("--saida", default="models/metricas_texto.json")
    p.add_argument("--sem-llm", action="store_true")
    p.add_argument("--pausa", type=float, default=2.5)
    args = p.parse_args()

    usar_llm = bool(os.getenv("GROQ_API_KEY")) and not args.sem_llm
    if not usar_llm:
        print("Sem GROQ_API_KEY: avaliando só a heurística.\n")

    df = pd.read_csv(args.dados)
    res = avaliar(df, usar_llm, args.pausa)

    print(f"{res['mensagens']} mensagens ({res['golpes']} golpes)\n")
    print(pd.DataFrame(res["teste"]).T.to_string())
    print("\nRecall por tipo de golpe:")
    print(pd.DataFrame(res["recall_por_categoria"]).to_string())

    Path(args.saida).write_text(json.dumps(res, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\nMétricas e erros salvos em {args.saida}")


if __name__ == "__main__":
    main()
