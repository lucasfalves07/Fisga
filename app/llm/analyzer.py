import json
import os
import re
import unicodedata

from dotenv import load_dotenv

load_dotenv(override=True)

PROMPT = """Você é analista de fraudes de um banco brasileiro. Avalie a mensagem abaixo e diga se é golpe.

Considere golpes comuns no Brasil: Pix, boleto falso, falsa central de banco, "Correios: taxa pendente",
falso gov.br/Receita, falso emprego, falso parente pedindo dinheiro, prêmio ou sorteio.

Responda só com JSON neste formato:
{{"score": 0.0 a 1.0, "categoria": "pix|boleto|banco|correios|governo|emprego|parente|premio|outro|legitimo", "motivos": ["frase curta", ...]}}

Assunto: {subject}
Mensagem:
{body}
"""

URGENCY = ["urgente", "imediatamente", "hoje", "24 horas", "bloqueada", "bloqueio", "suspensa", "última chance"]
MONEY = ["pix", "boleto", "taxa", "pagamento", "transferência", "chave"]
ENTREGA = ["encomenda", "objeto", "entrega", "rastreio", "taxad", "fiscaliza", "reagend", "retid"]
CREDENTIALS = ["senha", "token", "código de verificação", "cpf", "dados do cartão", "atualize seus dados"]


def _sem_acento(texto: str) -> str:
    return unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode().lower()


def heuristic(subject: str, body: str) -> dict:
    text = _sem_acento(f"{subject}\n{body}")
    reasons, score = [], 0.0

    hits = [w for w in URGENCY if _sem_acento(w) in text]
    if hits:
        reasons.append(f"Linguagem de urgência ({hits[0]})")
        score += 0.25
    hits = [w for w in MONEY if _sem_acento(w) in text]
    if hits:
        reasons.append(f"Pede pagamento ou menciona {hits[0]}")
        score += 0.25
    if any(_sem_acento(w) in text for w in ENTREGA) and any(_sem_acento(w) in text for w in MONEY):
        reasons.append("Cobra taxa para liberar ou reagendar entrega")
        score += 0.25
    hits = [w for w in CREDENTIALS if _sem_acento(w) in text]
    if hits:
        reasons.append(f"Solicita dado sensível ({hits[0]})")
        score += 0.3
    if re.search(r"clique (aqui|no link)|acesse o link", text):
        reasons.append("Pressiona para clicar em link")
        score += 0.15

    return {"score": min(score, 1.0), "categoria": "outro" if score else "legitimo", "motivos": reasons, "fonte": "heuristica"}


def llm(subject: str, body: str) -> dict:
    from groq import Groq

    client = Groq(api_key=os.environ["GROQ_API_KEY"])
    resp = client.chat.completions.create(
        model=os.getenv("GROQ_MODEL", "openai/gpt-oss-120b"),
        messages=[{"role": "user", "content": PROMPT.format(subject=subject, body=body[:4000])}],
        temperature=0,
        response_format={"type": "json_object"},
    )
    data = json.loads(resp.choices[0].message.content)
    return {
        "score": max(0.0, min(float(data.get("score", 0)), 1.0)),
        "categoria": data.get("categoria", "outro"),
        "motivos": data.get("motivos", [])[:5],
        "fonte": "llm",
    }


def analyze_text(subject: str, body: str) -> dict:
    if not os.getenv("GROQ_API_KEY"):
        return heuristic(subject, body)
    try:
        return llm(subject, body)
    except Exception:
        return heuristic(subject, body)
