"""
config.py — Configuração Central do Adaptador de Currículo
"""

import os
import json
import pathlib

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# ──────────────────────────────────────────
# App
# ──────────────────────────────────────────
APP_NOME    = "CVMaker"
APP_SUB     = "Adapte seu currículo para qualquer vaga com IA"
APP_AUTOR   = "CVMaker"
APP_ANO     = "2025"

# ──────────────────────────────────────────
# Modelos Claude
# ──────────────────────────────────────────
MODELO_PADRAO = "sabia-4"

# ──────────────────────────────────────────
# API Key
# ──────────────────────────────────────────
def get_api_key() -> str | None:
    return os.environ.get("MARITACA_API_KEY")

# ──────────────────────────────────────────
# Templates de currículo
# ──────────────────────────────────────────
TEMPLATES_DIR = pathlib.Path(__file__).parent / "templates"

def listar_templates() -> list[dict]:
    templates = []
    for arquivo in sorted(TEMPLATES_DIR.glob("*.json")):
        try:
            with open(arquivo, encoding="utf-8") as f:
                templates.append(json.load(f))
        except Exception:
            pass
    return sorted(templates, key=lambda t: t.get("prioridade", 99))

def carregar_template(template_id: str) -> dict:
    caminho = TEMPLATES_DIR / f"{template_id}.json"
    if not caminho.exists():
        raise FileNotFoundError(f"Template '{template_id}' não encontrado.")
    with open(caminho, encoding="utf-8") as f:
        return json.load(f)

# ──────────────────────────────────────────
# Formatos de exportação
# ──────────────────────────────────────────
FORMATOS_EXPORTACAO = ["pdf", "docx", "txt"]
IDIOMAS = ["Português", "Inglês", "Espanhol"]
