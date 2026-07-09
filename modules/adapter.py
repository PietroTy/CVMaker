"""
modules/adapter.py — Núcleo de Adaptação de Currículo com Claude API

Pipeline:
  1. Analisa a vaga (extrai requisitos, skills, palavras-chave, tom)
  2. Cruza com o perfil completo do candidato
  3. Gera o currículo adaptado seção por seção conforme o template
"""

import json
from typing import Optional, Callable


# ──────────────────────────────────────────────────────────────────
# Chamada base à API Anthropic
# ──────────────────────────────────────────────────────────────────
def _chamar_claude(api_key: str, system: str, user: str, max_tokens: int = 4096) -> str:
    import anthropic
    client = anthropic.Anthropic(api_key=api_key)
    msg = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=max_tokens,
        system=system,
        messages=[{"role": "user", "content": user}],
    )
    return msg.content[0].text


# ──────────────────────────────────────────────────────────────────
# Passo 1 — Análise da Vaga
# ──────────────────────────────────────────────────────────────────
def analisar_vaga(descricao_vaga: str, api_key: str, status_cb: Optional[Callable] = None) -> dict:
    """Extrai requisitos, skills e palavras-chave da descrição da vaga."""
    if status_cb:
        status_cb("🔍 Analisando requisitos da vaga...")

    system = (
        "Você é um especialista em recrutamento e análise de vagas. "
        "Responda SOMENTE em JSON válido, sem texto fora do JSON."
    )
    user = f"""Analise a seguinte descrição de vaga e extraia as informações em JSON com exatamente esta estrutura:

{{
  "cargo": "título da vaga",
  "empresa": "nome da empresa (se mencionado, senão null)",
  "area": "área de atuação (ex: Engenharia de Software, Marketing, etc.)",
  "nivel": "nível da vaga (Junior, Pleno, Senior, etc.)",
  "hard_skills": ["lista de habilidades técnicas obrigatórias e desejáveis"],
  "soft_skills": ["lista de habilidades comportamentais"],
  "palavras_chave": ["palavras e termos que devem aparecer no currículo para ATS"],
  "responsabilidades_chave": ["3-5 responsabilidades principais"],
  "diferenciais": ["o que faria o candidato se destacar"],
  "tom": "formal | técnico | dinâmico | criativo",
  "resumo_vaga": "1-2 frases resumindo o que a empresa busca"
}}

DESCRIÇÃO DA VAGA:
{descricao_vaga}"""

    resposta = _chamar_claude(api_key, system, user, max_tokens=1500)

    # Remove blocos de código markdown se houver
    resposta = resposta.strip()
    if resposta.startswith("```"):
        resposta = resposta.split("```")[1]
        if resposta.startswith("json"):
            resposta = resposta[4:]
    resposta = resposta.strip()

    try:
        return json.loads(resposta)
    except json.JSONDecodeError:
        # Fallback se o JSON vier malformado
        return {
            "cargo": "Não identificado",
            "empresa": None,
            "area": "Geral",
            "nivel": "Não especificado",
            "hard_skills": [],
            "soft_skills": [],
            "palavras_chave": [],
            "responsabilidades_chave": [],
            "diferenciais": [],
            "tom": "formal",
            "resumo_vaga": descricao_vaga[:200],
        }


# ──────────────────────────────────────────────────────────────────
# Passo 2 — Geração do Currículo Adaptado
# ──────────────────────────────────────────────────────────────────
def adaptar_curriculo(
    perfil_completo: str,
    analise_vaga: dict,
    template: dict,
    idioma: str,
    api_key: str,
    status_cb: Optional[Callable] = None,
) -> dict:
    """
    Gera o currículo adaptado seção por seção conforme o template selecionado.
    Retorna dict {secao_id: texto_gerado}.
    """
    resultados = {}
    secoes = template.get("secoes", [])
    total  = len(secoes)

    vaga_ctx = f"""
CARGO ALVO: {analise_vaga.get('cargo')}
ÁREA: {analise_vaga.get('area')}
NÍVEL: {analise_vaga.get('nivel')}
O QUE A EMPRESA BUSCA: {analise_vaga.get('resumo_vaga')}
HARD SKILLS REQUERIDAS: {', '.join(analise_vaga.get('hard_skills', []))}
SOFT SKILLS REQUERIDAS: {', '.join(analise_vaga.get('soft_skills', []))}
PALAVRAS-CHAVE PARA ATS: {', '.join(analise_vaga.get('palavras_chave', []))}
RESPONSABILIDADES PRINCIPAIS: {'; '.join(analise_vaga.get('responsabilidades_chave', []))}
DIFERENCIAIS VALORIZADOS: {', '.join(analise_vaga.get('diferenciais', []))}
TOM DA EMPRESA: {analise_vaga.get('tom')}
"""

    system_base = template.get("system_prompt", _system_prompt_padrao())

    for i, secao in enumerate(secoes):
        if status_cb:
            status_cb(f"✍️ Gerando seção {i+1}/{total}: {secao['titulo']}...")

        user_prompt = f"""
{secao['prompt']}

━━━ CONTEXTO DA VAGA ━━━
{vaga_ctx}

━━━ PERFIL COMPLETO DO CANDIDATO ━━━
{perfil_completo}

━━━ INSTRUÇÕES ADICIONAIS ━━━
- Idioma de saída: {idioma}
- Priorize experiências e habilidades DIRETAMENTE relevantes para a vaga acima
- Use as palavras-chave da vaga naturalmente no texto (sem forçar)
- Seja objetivo e preciso — recrutadores leem em 30 segundos
- NUNCA invente experiências, datas, empresas ou certificações não mencionadas no perfil
- Se uma informação não estiver no perfil do candidato, OMITA (não preencha com placeholder)
"""

        texto = _chamar_claude(api_key, system_base, user_prompt, max_tokens=secao.get("max_tokens", 800))
        resultados[secao["id"]] = {
            "titulo": secao["titulo"],
            "texto":  texto.strip(),
        }

    return resultados


# ──────────────────────────────────────────────────────────────────
# System prompt padrão de adaptação
# ──────────────────────────────────────────────────────────────────
def _system_prompt_padrao() -> str:
    return (
        "Você é um especialista em recrutamento, carreira e escrita de currículos de alto impacto. "
        "Sua missão é adaptar o currículo do candidato para maximizar as chances de aprovação em uma vaga específica.\n\n"
        "**REGRAS ABSOLUTAS:**\n"
        "1. Use APENAS informações presentes no perfil do candidato. Nunca invente nada.\n"
        "2. Destaque as experiências e habilidades mais relevantes para a vaga. Omita ou minimize o que for irrelevante.\n"
        "3. Incorpore palavras-chave da vaga naturalmente — currículos passam por filtros ATS.\n"
        "4. Seja direto e conciso. Bullet points com verbos de ação e resultados quantificados quando disponíveis.\n"
        "5. Tom profissional alinhado ao da empresa.\n"
        "6. Gere APENAS o conteúdo da seção solicitada, sem cabeçalhos de sistema ou metadados.\n"
        "7. Se uma informação relevante para a seção não estiver no perfil, omita silenciosamente."
    )
