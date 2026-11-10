import argparse
import csv
import io
import os
import random
import sys
import zipfile
from datetime import date
from pathlib import Path

import httpx
import tldextract
from dotenv import load_dotenv

from app.features.brands_br import BRANDS

load_dotenv()

OPENPHISH = "https://openphish.com/feed.txt"
PHISHING_DB = "https://raw.githubusercontent.com/Phishing-Database/Phishing.Database/master/phishing-links-ACTIVE.txt"
PHISHTANK = "https://data.phishtank.com/data/{key}/online-valid.csv"
TRANCO = "https://tranco-list.eu/top-1m.csv.zip"

TERMOS_BR = [
    "pix", "boleto", "correios", "receita", "govbr", "gov-br", "detran", "serasa",
    "cpf", "fgts", "inss", "bolsafamilia", "caixatem", "nota-fiscal", "rastreio",
    "encomenda", "taxa", "multa", "ipva", "regularizar", "desbloqueio",
]

OFICIAIS = sorted({d for dominios in BRANDS.values() for d in dominios})

_extract = tldextract.TLDExtract(suffix_list_urls=())


def baixar(url: str, timeout: int = 60) -> bytes:
    headers = {"User-Agent": "fisga-dataset/0.1"}
    r = httpx.get(url, headers=headers, timeout=timeout, follow_redirects=True)
    r.raise_for_status()
    return r.content


def alvo_br(url: str) -> bool:
    u = url.lower()
    host = u.split("//")[-1].split("/")[0]
    if host.endswith(".br") or ".br." in host:
        return True
    if any(marca in u.replace("-", "").replace(".", "") for marca in BRANDS if len(marca) >= 4):
        return True
    return any(t in u for t in TERMOS_BR)


def oficial(url: str) -> bool:
    ext = _extract(url)
    dominio = ".".join(p for p in [ext.domain, ext.suffix] if p)
    return dominio in OFICIAIS or ext.suffix == "gov.br" or dominio == "gov.br"


def openphish() -> list[str]:
    texto = baixar(OPENPHISH).decode(errors="ignore")
    return [l.strip() for l in texto.splitlines() if l.startswith("http")]


def phishing_database() -> list[str]:
    texto = baixar(PHISHING_DB, timeout=300).decode(errors="ignore")
    return [l.strip() for l in texto.splitlines() if l.startswith("http")]


def phishtank() -> list[str]:
    key = os.getenv("PHISHTANK_KEY")
    if not key:
        return []
    texto = baixar(PHISHTANK.format(key=key), timeout=180).decode(errors="ignore")
    return [row["url"] for row in csv.DictReader(io.StringIO(texto))]


def tranco(limite_br: int, limite_global: int) -> list[str]:
    with zipfile.ZipFile(io.BytesIO(baixar(TRANCO, timeout=180))) as z:
        texto = z.read(z.namelist()[0]).decode()

    br, globais = [], []
    for linha in texto.splitlines():
        _, dominio = linha.split(",", 1)
        if dominio.endswith(".br"):
            if len(br) < limite_br:
                br.append(dominio)
        elif len(globais) < limite_global:
            globais.append(dominio)
        if len(br) >= limite_br and len(globais) >= limite_global:
            break
    return [f"https://{d}" for d in br + globais]


def coletar(fontes, limite_br: int, limite_global: int) -> list[dict]:
    hoje = date.today().isoformat()
    linhas, vistos = [], set()

    def add(url, label, fonte):
        chave = url.strip().rstrip("/").lower()
        if chave in vistos:
            return
        vistos.add(chave)
        linhas.append({"url": url.strip(), "label": label, "fonte": fonte, "data_coleta": hoje})

    for nome, func in fontes.items():
        try:
            urls = func()
        except Exception as e:
            print(f"[{nome}] falhou: {e}", file=sys.stderr)
            continue
        br = [u for u in urls if alvo_br(u) and not oficial(u)]
        print(f"[{nome}] {len(urls)} urls, {len(br)} com alvo BR")
        for u in br:
            add(u, 1, nome)

    for d in OFICIAIS:
        add(f"https://{d}", 0, "oficial")

    try:
        legit = tranco(limite_br, limite_global)
        print(f"[tranco] {len(legit)} dominios legitimos")
        for u in legit:
            add(u, 0, "tranco")
    except Exception as e:
        print(f"[tranco] falhou: {e}", file=sys.stderr)

    return linhas


def salvar(linhas: list[dict], saida: Path, balancear: bool):
    if balancear:
        pos = [l for l in linhas if l["label"] == 1]
        neg = [l for l in linhas if l["label"] == 0]
        n = min(len(pos), len(neg))
        random.seed(42)
        linhas = random.sample(pos, n) + random.sample(neg, n)
        random.shuffle(linhas)

    saida.parent.mkdir(parents=True, exist_ok=True)
    with saida.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["url", "label", "fonte", "data_coleta"])
        w.writeheader()
        w.writerows(linhas)

    pos = sum(l["label"] for l in linhas)
    print(f"{len(linhas)} linhas salvas em {saida} ({pos} golpes, {len(linhas) - pos} legitimas)")


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--saida", default="data/processed/urls.csv")
    p.add_argument("--legitimas-br", type=int, default=3000)
    p.add_argument("--legitimas-globais", type=int, default=1000)
    p.add_argument("--balancear", action="store_true")
    args = p.parse_args()

    fontes = {"openphish": openphish, "phishing_database": phishing_database, "phishtank": phishtank}
    linhas = coletar(fontes, args.legitimas_br, args.legitimas_globais)

    saida = Path(args.saida)
    if saida.exists():
        with saida.open(encoding="utf-8") as f:
            antigas = list(csv.DictReader(f))
        novas = {l["url"].lower() for l in linhas}
        for a in antigas:
            if a["url"].lower() not in novas:
                a["label"] = int(a["label"])
                linhas.append(a)

    salvar(linhas, saida, args.balancear)


if __name__ == "__main__":
    main()
