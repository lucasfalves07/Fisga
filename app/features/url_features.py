import ipaddress
import math
import re
import unicodedata
from dataclasses import dataclass, field
from urllib.parse import urlparse

import tldextract

from app.features.brands_br import BRANDS, RISKY_TLDS, SENSITIVE_WORDS, SHORTENERS

_extract = tldextract.TLDExtract(suffix_list_urls=())


@dataclass
class UrlReport:
    url: str
    domain: str
    features: dict = field(default_factory=dict)
    reasons: list[str] = field(default_factory=list)


def _normalize(text: str) -> str:
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]", "", text.lower())


def _is_ip(host: str) -> bool:
    try:
        ipaddress.ip_address(host)
        return True
    except ValueError:
        return False


def _levenshtein(a: str, b: str) -> int:
    if len(a) < len(b):
        a, b = b, a
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i]
        for j, cb in enumerate(b, 1):
            cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (ca != cb)))
        prev = cur
    return prev[-1]


def _brand_impersonated(host: str, registered: str) -> str | None:
    for brand, official in BRANDS.items():
        if any(registered == d or host.endswith("." + d) for d in official):
            return None

    label = _normalize(registered.split(".")[0])
    full = _normalize(host)

    for brand in BRANDS:
        if len(brand) < 4:
            continue
        if brand in full:
            return brand
        if len(label) >= 5 and _levenshtein(label, brand) == 1:
            return brand
    return None


def analyze_url(url: str) -> UrlReport:
    if not re.match(r"^[a-z]+://", url, re.I):
        url = "http://" + url

    parsed = urlparse(url)
    host = (parsed.hostname or "").lower()
    ext = _extract(host)
    registered = ".".join(p for p in [ext.domain, ext.suffix] if p)
    path = (parsed.path + "?" + parsed.query).lower()

    f = {
        "length": len(url),
        "https": parsed.scheme == "https",
        "is_ip": _is_ip(host),
        "subdomains": len([s for s in ext.subdomain.split(".") if s]),
        "hyphens": host.count("-"),
        "digits": sum(c.isdigit() for c in host),
        "has_at": "@" in url,
        "punycode": "xn--" in host,
        "risky_tld": ext.suffix.split(".")[-1] in RISKY_TLDS,
        "shortener": registered in SHORTENERS,
        "sensitive_words": [w for w in SENSITIVE_WORDS if w in path or w in host],
        "brand": _brand_impersonated(host, registered),
    }

    r = []
    if f["brand"]:
        r.append(f"Domínio imita a marca '{f['brand']}' mas não é o domínio oficial")
    if f["is_ip"]:
        r.append("Usa endereço IP no lugar de domínio")
    if f["punycode"]:
        r.append("Domínio com caracteres internacionais (possível homógrafo)")
    if f["risky_tld"]:
        r.append(f"TLD de alto risco (.{ext.suffix})")
    if f["shortener"]:
        r.append("Link encurtado esconde o destino real")
    if f["has_at"]:
        r.append("URL contém '@', que pode esconder o domínio real")
    if not f["https"]:
        r.append("Sem HTTPS")
    if f["subdomains"] >= 3:
        r.append("Muitos subdomínios")
    if f["hyphens"] >= 2:
        r.append("Muitos hífens no domínio")
    if f["length"] > 90:
        r.append("URL muito longa")
    for w in f["sensitive_words"][:2]:
        r.append(f"URL contém palavra sensível: '{w}'")

    return UrlReport(url=url, domain=registered, features=f, reasons=r)


HOST_FEATURES = [
    "host_len", "dominio_len", "subdominios", "pontos", "hifens", "digitos", "prop_digitos",
    "entropia", "prop_vogais", "maior_seq_consoantes", "maior_rotulo", "is_ip", "punycode",
    "tld_risco", "tld_br", "tld_gov", "encurtador", "marca_imitada", "palavras_sensiveis_host",
]


def _entropy(text: str) -> float:
    if not text:
        return 0.0
    counts = [text.count(c) for c in set(text)]
    return -sum(n / len(text) * math.log2(n / len(text)) for n in counts)


def host_features(url: str) -> dict:
    if not re.match(r"^[a-z]+://", url, re.I):
        url = "http://" + url
    host = (urlparse(url).hostname or "").lower()
    if host.startswith("www."):
        host = host[4:]
    ext = _extract(host)
    registered = ".".join(p for p in [ext.domain, ext.suffix] if p)
    label = ext.domain
    letras = [c for c in label if c.isalpha()]
    consoantes = re.findall(r"[bcdfghjklmnpqrstvwxyz]+", label)

    return {
        "host_len": len(host),
        "dominio_len": len(label),
        "subdominios": len([s for s in ext.subdomain.split(".") if s]),
        "pontos": host.count("."),
        "hifens": host.count("-"),
        "digitos": sum(c.isdigit() for c in host),
        "prop_digitos": sum(c.isdigit() for c in host) / max(len(host), 1),
        "entropia": _entropy(label),
        "prop_vogais": sum(c in "aeiou" for c in letras) / max(len(letras), 1),
        "maior_seq_consoantes": max((len(c) for c in consoantes), default=0),
        "maior_rotulo": max((len(p) for p in host.split(".")), default=0),
        "is_ip": int(_is_ip(host)),
        "punycode": int("xn--" in host),
        "tld_risco": int(ext.suffix.split(".")[-1] in RISKY_TLDS),
        "tld_br": int(ext.suffix.endswith("br")),
        "tld_gov": int(ext.suffix in {"gov.br", "gov"}),
        "encurtador": int(registered in SHORTENERS),
        "marca_imitada": int(_brand_impersonated(host, registered) is not None),
        "palavras_sensiveis_host": sum(w in host for w in SENSITIVE_WORDS),
    }


OFFICIAL = {d for dominios in BRANDS.values() for d in dominios}


def is_official(url: str) -> bool:
    if not re.match(r"^[a-z]+://", url, re.I):
        url = "http://" + url
    ext = _extract((urlparse(url).hostname or "").lower())
    registered = ".".join(p for p in [ext.domain, ext.suffix] if p)
    return registered in OFFICIAL or ext.suffix == "gov.br"
