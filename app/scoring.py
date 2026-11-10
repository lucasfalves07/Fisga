from app.features.header_checks import check_headers, extract_urls, split_email
from app.features.url_features import analyze_url
from app.llm.analyzer import analyze_text

WEIGHTS = {
    "brand": 0.45,
    "is_ip": 0.3,
    "punycode": 0.3,
    "risky_tld": 0.15,
    "shortener": 0.15,
    "has_at": 0.2,
    "no_https": 0.1,
    "subdomains": 0.1,
    "hyphens": 0.05,
    "long": 0.05,
    "sensitive": 0.05,
}


def verdict(score: float) -> str:
    if score >= 0.7:
        return "provável golpe"
    if score >= 0.4:
        return "suspeito"
    return "provavelmente seguro"


def score_url(url: str) -> dict:
    rep = analyze_url(url)
    f = rep.features

    s = 0.0
    s += WEIGHTS["brand"] if f["brand"] else 0
    s += WEIGHTS["is_ip"] if f["is_ip"] else 0
    s += WEIGHTS["punycode"] if f["punycode"] else 0
    s += WEIGHTS["risky_tld"] if f["risky_tld"] else 0
    s += WEIGHTS["shortener"] if f["shortener"] else 0
    s += WEIGHTS["has_at"] if f["has_at"] else 0
    s += WEIGHTS["no_https"] if not f["https"] else 0
    s += WEIGHTS["subdomains"] if f["subdomains"] >= 3 else 0
    s += WEIGHTS["hyphens"] if f["hyphens"] >= 2 else 0
    s += WEIGHTS["long"] if f["length"] > 90 else 0
    s += WEIGHTS["sensitive"] * min(len(f["sensitive_words"]), 2)

    s = round(min(s, 1.0), 2)
    return {"url": rep.url, "dominio": rep.domain, "score": s, "veredito": verdict(s), "motivos": rep.reasons}


def score_email(raw: str) -> dict:
    headers = check_headers(raw)
    subject, body = split_email(raw)
    text = analyze_text(subject, body)
    urls = [score_url(u) for u in extract_urls(body)[:10]]

    url_max = max((u["score"] for u in urls), default=0.0)
    s = 0.5 * text["score"] + 0.3 * url_max + headers["penalty"]
    s = round(min(s, 1.0), 2)

    motivos = text["motivos"] + headers["reasons"]
    worst = max(urls, key=lambda u: u["score"], default=None)
    if worst and worst["score"] >= 0.4:
        motivos.append(f"Link suspeito: {worst['dominio']}")

    return {
        "score": s,
        "veredito": verdict(s),
        "categoria": text["categoria"],
        "motivos": motivos,
        "detalhes": {
            "texto": text,
            "cabecalhos": {k: v for k, v in headers.items() if k != "reasons"},
            "urls": urls,
        },
    }
