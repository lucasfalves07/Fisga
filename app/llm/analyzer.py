import json
import os
import re

from dotenv import load_dotenv

load_dotenv()

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
CREDENTIALS = ["senha", "token", "código de verificação", "cpf", "dados do cartão", "atualize seus dados"]


def heuristic(subject: str, body: str) -> dict:
    text = f"{subject}\n{body}".lower()
    reasons, score = [], 0.0

    hits = [w for w in URGENCY if w in text]
    if hits:
        reasons.append(f"Linguagem de urgência ({hits[0]})")
        score += 0.25
    hits = [w for w in MONEY if w in text]
    if hits:
        reasons.append(f"Pede pagamento ou menciona {hits[0]}")
        score += 0.25
    hits = [w for w in CREDENTIALS if w in text]
    if hits:
        reasons.append(f"Solicita dado sensível ({hits[0]})")
        score += 0.3
    if re.search(r"clique (aqui|no link)|acesse o link", text):
        reasons.append("Pressiona para clicar em link")
        score += 0.15

    return {"score": min(score, 1.0), "categoria": "outro" if score else "legitimo", "motivos": reasons, "fonte": "heuristica"}


def analyze_text(subject: str, body: str) -> dict:
    key = os.getenv("GROQ_API_KEY")
    if not key:
        return heuristic(subject, body)

    try:
        from groq import Groq

        client = Groq(api_key=key)
        resp = client.chat.completions.create(
            model=os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile"),
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
    except Exception:
        return heuristic(subject, body)
