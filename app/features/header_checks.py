import re
from email import message_from_string
from email.utils import parseaddr

import tldextract

_extract = tldextract.TLDExtract(suffix_list_urls=())


def _domain(addr: str) -> str:
    _, email = parseaddr(addr or "")
    host = email.split("@")[-1].lower() if "@" in email else ""
    ext = _extract(host)
    return ".".join(p for p in [ext.domain, ext.suffix] if p)


def _auth_result(auth: str, mech: str) -> str | None:
    m = re.search(rf"\b{mech}=(\w+)", auth, re.I)
    return m.group(1).lower() if m else None


def check_headers(raw: str) -> dict:
    msg = message_from_string(raw)
    auth = " ".join(msg.get_all("Authentication-Results") or [])

    sender = msg.get("From", "")
    reply_to = msg.get("Reply-To", "")
    return_path = msg.get("Return-Path", "")

    result = {
        "from_domain": _domain(sender),
        "spf": _auth_result(auth, "spf"),
        "dkim": _auth_result(auth, "dkim"),
        "dmarc": _auth_result(auth, "dmarc"),
        "reasons": [],
        "penalty": 0.0,
    }

    for mech, weight in (("spf", 0.15), ("dkim", 0.15), ("dmarc", 0.2)):
        status = result[mech]
        if status in {"fail", "softfail", "permerror"}:
            result["reasons"].append(f"{mech.upper()} falhou ({status})")
            result["penalty"] += weight
        elif status is None and auth:
            result["reasons"].append(f"{mech.upper()} ausente")
            result["penalty"] += weight / 3

    if reply_to and _domain(reply_to) and _domain(reply_to) != result["from_domain"]:
        result["reasons"].append(f"Reply-To ({_domain(reply_to)}) diferente do remetente")
        result["penalty"] += 0.15

    if return_path and _domain(return_path) and _domain(return_path) != result["from_domain"]:
        result["reasons"].append("Return-Path diferente do remetente")
        result["penalty"] += 0.05

    name, _ = parseaddr(sender)
    if name and re.search(r"@|\.com", name):
        result["reasons"].append("Nome de exibição contém um endereço falso")
        result["penalty"] += 0.15

    result["penalty"] = min(result["penalty"], 0.6)
    return result


def split_email(raw: str) -> tuple[str, str]:
    msg = message_from_string(raw)
    if msg.is_multipart():
        parts = [p.get_payload(decode=True) for p in msg.walk() if p.get_content_type() == "text/plain"]
        body = b"\n".join(p for p in parts if p).decode(errors="ignore")
    else:
        payload = msg.get_payload(decode=True)
        body = payload.decode(errors="ignore") if payload else msg.get_payload()
    return msg.get("Subject", ""), body or ""


def extract_urls(text: str) -> list[str]:
    urls = re.findall(r"https?://[^\s<>\"')]+", text)
    return list(dict.fromkeys(u.rstrip(".,;") for u in urls))
