from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)

GOLPE = """From: "Correios <noreply@correios.com.br>" <avisos@entregas-br.top>
Reply-To: suporte@gmail.com
Subject: Sua encomenda foi retida
Authentication-Results: mx.exemplo.com; spf=fail; dkim=none; dmarc=fail

Olá, sua encomenda está retida. Pague a taxa de R$ 9,90 via Pix hoje para liberar.
Clique aqui: http://correios-taxa.top/pagamento
"""

LEGITIMO = """From: Equipe Mauá <contato@maua.br>
Subject: Calendário de provas
Authentication-Results: mx.exemplo.com; spf=pass; dkim=pass; dmarc=pass

Segue o calendário de provas do semestre. Bons estudos.
"""


def test_health():
    assert client.get("/health").json() == {"status": "ok"}


def test_email_golpe(monkeypatch):
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    r = client.post("/analyze/email", json={"raw": GOLPE}).json()
    assert r["score"] >= 0.7
    assert r["veredito"] == "provável golpe"


def test_email_legitimo(monkeypatch):
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    r = client.post("/analyze/email", json={"raw": LEGITIMO}).json()
    assert r["score"] < 0.4
