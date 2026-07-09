"""
modules/xml_adapter.py — Adaptação Cirúrgica do XML do DOCX

Estratégia:
  1. Desempacota o DOCX em memória
  2. Parseia document.xml e identifica cada parágrafo editável
  3. Agrupa por seção (Resumo, Habilidades, Experiências, Projetos)
  4. Envia ao Claude para adaptação (apenas texto, sem XML)
  5. Substitui o texto nos nós <w:t> preservando toda a estrutura XML
  6. Reempacota como DOCX

Regra de ouro: NÃO alterar nenhum nó que não seja <w:t> com conteúdo editável.
"""

import io
import json
import zipfile
import copy
from xml.etree import ElementTree as ET

# Namespace OOXML
NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
W  = f"{{{NS}}}"

# ─────────────────────────────────────────────────────────────────────────────
# Utilitários XML
# ─────────────────────────────────────────────────────────────────────────────

def _texto_do_paragrafo(paragrafo) -> str:
    """Concatena todos os <w:t> de um parágrafo."""
    partes = []
    for elem in paragrafo.iter(f"{W}t"):
        if elem.text:
            partes.append(elem.text)
    return "".join(partes).strip()

def _substituir_texto_paragrafo(paragrafo, novo_texto: str):
    """
    Coloca novo_texto no primeiro <w:t> de cada <w:r> do parágrafo,
    limpando os demais <w:t> do mesmo parágrafo.
    Preserva <w:rPr> (formatação: negrito, itálico, tamanho, cor).
    """
    runs = paragrafo.findall(f".//{W}r")
    if not runs:
        return

    # Encontra o primeiro run que tem <w:t>
    primeiro_run_com_t = None
    for r in runs:
        t = r.find(f"{W}t")
        if t is not None:
            primeiro_run_com_t = (r, t)
            break

    if primeiro_run_com_t is None:
        return

    primeiro_run, primeiro_t = primeiro_run_com_t

    # Coloca o novo texto no primeiro <w:t>
    primeiro_t.text = novo_texto
    if novo_texto and (novo_texto[0] == " " or novo_texto[-1] == " "):
        primeiro_t.set("{http://www.w3.org/XML/1998/namespace}space", "preserve")

    # Limpa os <w:t> dos outros runs do MESMO parágrafo (não iteramos sub-parágrafos)
    for r in runs:
        if r is primeiro_run:
            continue
        for t in r.findall(f"{W}t"):
            t.text = ""
            # Remove o atributo space se existir
            t.attrib.pop("{http://www.w3.org/XML/1998/namespace}space", None)


def split_experiencia_titulo(texto_completo: str):
    import re
    partes = texto_completo.split(",", 1)
    cargo = partes[0].strip()
    resto = partes[1].strip() if len(partes) > 1 else ""
    
    match = re.search(r"(\S+\s+\d{4}\s*[-–]\s*\S+(\s+\d{4})?)", resto)
    if match:
        empresa_local = resto[:match.start()].strip()
        datas = match.group(1).strip()
    else:
        partes_resto = re.split(r'\s{2,}', resto)
        if len(partes_resto) > 1:
            empresa_local = partes_resto[0].strip()
            datas = partes_resto[1].strip()
        else:
            empresa_local = resto
            datas = ""
            
    return cargo, empresa_local, datas


def split_projeto_titulo(texto_completo: str):
    import re
    match = re.search(r"(https?://\S+)", texto_completo)
    if match:
        nome_tecs = texto_completo[:match.start()].strip()
        url = match.group(1).strip()
    else:
        partes = re.split(r'\s{2,}', texto_completo)
        if len(partes) > 1:
            nome_tecs = partes[0].strip()
            url = partes[1].strip()
        else:
            nome_tecs = texto_completo
            url = ""
    return nome_tecs, url


def aplicar_titulo_experiencia_preservando_formatacao(p, novo_titulo_completo: str):
    cargo, empresa_local, datas = split_experiencia_titulo(novo_titulo_completo)
    
    runs = p.findall(f".//{W}r")
    bold_runs = []
    normal_runs = []
    
    for r in runs:
        t = r.find(f"{W}t")
        if t is not None:
            rPr = r.find(f"{W}rPr")
            is_bold = rPr is not None and rPr.find(f"{W}b") is not None
            if is_bold:
                bold_runs.append((r, t))
            else:
                normal_runs.append((r, t))
                
    if bold_runs:
        r0, t0 = bold_runs[0]
        t0.text = cargo
        t0.set("{http://www.w3.org/XML/1998/namespace}space", "preserve")
        for r, t in bold_runs[1:]:
            t.text = ""
            
    if normal_runs:
        r_emp, t_emp = normal_runs[0]
        t_emp.text = ", " + empresa_local + "  "
        t_emp.set("{http://www.w3.org/XML/1998/namespace}space", "preserve")
        
        if len(normal_runs) > 1:
            r_dat, t_dat = normal_runs[1]
            t_dat.text = datas
            t_dat.set("{http://www.w3.org/XML/1998/namespace}space", "preserve")
            for r, t in normal_runs[2:]:
                t.text = ""
        else:
            t_emp.text += datas


def aplicar_titulo_projeto_preservando_formatacao(p, novo_titulo_completo: str):
    nome_tecs, url = split_projeto_titulo(novo_titulo_completo)
    
    runs = p.findall(f".//{W}r")
    runs_com_texto = []
    for r in runs:
        t = r.find(f"{W}t")
        if t is not None and t.text and t.text.strip():
            runs_com_texto.append((r, t))
            
    if not runs_com_texto:
        return
        
    r0, t0 = runs_com_texto[0]
    t0.text = nome_tecs + "  "
    t0.set("{http://www.w3.org/XML/1998/namespace}space", "preserve")
    
    url_run_idx = -1
    for idx, (r, t) in enumerate(runs_com_texto[1:]):
        if 'http' in t.text or 'github' in t.text or '/' in t.text:
            url_run_idx = idx + 1
            break
            
    if url_run_idx != -1:
        r_url, t_url = runs_com_texto[url_run_idx]
        t_url.text = url
        t_url.set("{http://www.w3.org/XML/1998/namespace}space", "preserve")
        
        for idx, (r, t) in enumerate(runs_com_texto[1:]):
            if idx + 1 != url_run_idx:
                t.text = ""
    else:
        if len(runs_com_texto) > 1:
            r1, t1 = runs_com_texto[1]
            t1.text = url
            t1.set("{http://www.w3.org/XML/1998/namespace}space", "preserve")
            for r, t in runs_com_texto[2:]:
                t.text = ""
        else:
            t0.text += url


# ─────────────────────────────────────────────────────────────────────────────
# Mapeamento de seções do currículo (específico para a estrutura do DOCX)
# ─────────────────────────────────────────────────────────────────────────────

def _detectar_secao_atual(texto: str, secao_atual: str) -> str:
    """Detecta mudança de seção com base no texto do parágrafo."""
    t = texto.strip().lower().rstrip()
    if t in ("habilidades", "habilidades  "):
        return "habilidades"
    if t in ("experiência", "experiencia", "experiência  ", "experiencia  "):
        return "experiencia"
    if t in ("projetos", "projetos  "):
        return "projetos"
    if t in ("educação", "educacao", "educação  ", "educacao  "):
        return "educacao"
    return secao_atual


def extrair_blocos_editaveis(xml_bytes: bytes) -> dict:
    """
    Parseia o document.xml e retorna um dict com os blocos de texto editáveis:
    {
      "tagline": "Desenvolvedor Full-stack...",
      "resumo": "Graduando em Ciência...",
      "skills_dev": "Python, Java, ...",
      "skills_tools": "Git/GitHub, CI/CD, ...",
      "exp_0_bullets": ["bullet1", "bullet2", ...],
      "exp_1_bullets": [...],
      "exp_2_bullets": [...],
      "proj_0_desc": "Aplicação fullstack...",
      "proj_1_desc": "Ferramenta de geração...",
      "proj_2_desc": "Agente conversacional...",
    }
    """
    root = ET.fromstring(xml_bytes)
    body = root.find(f"{W}body")
    paragrafos = list(body)

    blocos = {}
    secao_atual = "inicio"

    # Índices de controle de seções dinâmicas
    exp_idx   = -1
    proj_idx  = -1
    em_bullets_exp  = False
    em_bullets_proj = False
    ultimo_titulo_proj = None

    # Flags para capturar tagline e resumo na seção de início
    tagline_capturado = False
    resumo_capturado  = False

    for p in paragrafos:
        if p.tag != f"{W}p":
            continue

        texto = _texto_do_paragrafo(p)
        if not texto:
            continue

        # Detecta mudança de seção
        nova_secao = _detectar_secao_atual(texto, secao_atual)
        if nova_secao != secao_atual:
            secao_atual = nova_secao
            em_bullets_exp  = False
            em_bullets_proj = False
            continue

        # ── INÍCIO (tagline + resumo) ──────────────────────────────────────
        if secao_atual == "inicio":
            # Tagline: parágrafo negrito único curto antes do resumo
            pPr = p.find(f"{W}pPr")
            runs = p.findall(f".//{W}r")
            if runs and not tagline_capturado:
                # Verifica se o run tem <w:b>
                primeiro_run = runs[0] if runs else None
                if primeiro_run is not None:
                    rPr = primeiro_run.find(f"{W}rPr")
                    if rPr is not None and rPr.find(f"{W}b") is not None:
                        if len(texto) > 20 and "Pietro" not in texto:
                            blocos["tagline"] = texto
                            tagline_capturado = True
                            continue

            if tagline_capturado and not resumo_capturado and len(texto) > 50:
                # Parágrafo mais longo = resumo
                blocos["resumo"] = texto
                resumo_capturado = True
                continue

        # ── HABILIDADES ────────────────────────────────────────────────────
        elif secao_atual == "habilidades":
            # Skills de Dev: contém "Python" ou começa com label "Desenvolvimento"
            if "python" in texto.lower() or "javascript" in texto.lower():
                # Pega só a parte depois do ":" se houver
                if ":" in texto:
                    blocos["skills_dev"] = texto.split(":", 1)[1].strip()
                else:
                    blocos["skills_dev"] = texto
            elif "git" in texto.lower() or "docker" in texto.lower():
                if ":" in texto:
                    blocos["skills_tools"] = texto.split(":", 1)[1].strip()
                else:
                    blocos["skills_tools"] = texto

        # ── EXPERIÊNCIA ────────────────────────────────────────────────────
        elif secao_atual == "experiencia":
            # Detecta linha de cargo (tem <w:b> no primeiro run E tem empresa)
            runs = p.findall(f".//{W}r")
            primeiro_run_com_b = None
            for r in runs:
                rPr = r.find(f"{W}rPr")
                if rPr is not None and rPr.find(f"{W}b") is not None:
                    t_elem = r.find(f"{W}t")
                    if t_elem is not None and t_elem.text and len(t_elem.text.strip()) > 3:
                        primeiro_run_com_b = t_elem.text.strip()
                        break

            numPr = p.find(f".//{W}numPr")

            if numPr is not None:
                # É um bullet point de experiência
                if em_bullets_exp and exp_idx >= 0:
                    chave = f"exp_{exp_idx}_bullets"
                    if chave not in blocos:
                        blocos[chave] = []
                    blocos[chave].append(texto)
            elif primeiro_run_com_b and "," in texto:
                # Nova entrada de emprego (título, Empresa – Local)
                exp_idx += 1
                em_bullets_exp = True
                blocos[f"exp_{exp_idx}_titulo"] = texto  # guardamos referência mas não editamos

        # ── PROJETOS ───────────────────────────────────────────────────────
        elif secao_atual == "projetos":
            numPr = p.find(f".//{W}numPr")
            runs  = p.findall(f".//{W}r")

            # Detecta título de projeto (tem run com sz=28 ou texto curto sem bullet)
            eh_titulo_proj = False
            for r in runs:
                rPr = r.find(f"{W}rPr")
                if rPr is not None:
                    sz = rPr.find(f"{W}sz")
                    if sz is not None and sz.get(f"{W}val") == "28":
                        eh_titulo_proj = True
                        break

            if eh_titulo_proj and numPr is None:
                proj_idx += 1
                em_bullets_proj = True
                blocos[f"proj_{proj_idx}_title"] = texto
            elif numPr is not None and em_bullets_proj and proj_idx >= 0:
                chave = f"proj_{proj_idx}_desc"
                blocos[chave] = texto

    return blocos


# ─────────────────────────────────────────────────────────────────────────────
# Adaptação via Claude API
# ─────────────────────────────────────────────────────────────────────────────

def adaptar_via_claude(blocos: dict, descricao_vaga: str, perfil_extra: str, api_key: str, idioma: str = "Português (PT-BR)", status_cb=None) -> dict:
    """
    Envia os blocos extraídos + descrição da vaga para Maritaca AI (sabiá-3).
    Retorna dict com os mesmos blocos mas com texto adaptado.
    """
    from openai import OpenAI
    client = OpenAI(
        api_key=api_key,
        base_url="https://chat.maritaca.ai/api"
    )

    # Monta o contexto dos blocos
    blocos_json = json.dumps(blocos, ensure_ascii=False, indent=2)

    system = """Você é um especialista em currículos de alto impacto para o mercado de tecnologia brasileiro.
Sua tarefa é adaptar e reescrever os blocos de texto de um currículo para uma vaga específica.

REGRAS ABSOLUTAS:
1. Retorne SOMENTE JSON válido — nenhum texto fora do JSON, sem blocos de código markdown.
2. Mantenha EXATAMENTE as mesmas chaves do JSON de entrada.
3. NUNCA invente informações, empresas, tecnologias ou experiências não presentes no perfil ou no banco de dados do candidato, EXCETO para a seção de habilidades (skills_dev e skills_tools): nessa seção, você DEVE incluir todas as habilidades, ferramentas, metodologias e tecnologias que a vaga pede, usando exatamente as mesmas palavras-chave/termos que a vaga descreve, mesmo que o candidato não as possua explicitamente em seu banco de dados. Para as outras seções (experiências e projetos), a regra de não inventar informações continua rígida.
4. Para as experiências (exp_X_titulo e exp_X_bullets): Analise a lista completa de experiências do candidato fornecida no banco de dados do prompt (Engaja Soluções, Consultoria PUC, IFSP COSAIC, CCAA, USP, Game of Drones, etc.) e SELECIONE as 3 mais relevantes para a vaga. Preencha 'exp_X_titulo' com a experiência selecionada no formato original ('Cargo, Empresa – Cidade, Estado, País  Data Início – Data Fim'), e preencha 'exp_X_bullets' com bullets de impacto altamente otimizados para a vaga (mantendo rigorosamente a mesma quantidade de bullets da vaga original do template).
5. Para os projetos (proj_X_title e proj_X_desc): Analise a lista completa de projetos do candidato no prompt (como cHUB, LaPlayer, Erium, Pipeline de ETL CNPJs, etc.) e SELECIONE os 3 projetos mais relevantes e de maior impacto para esta vaga. Substitua 'proj_X_title' com o nome e as tecnologias principais do projeto selecionado (no formato 'Nome do Projeto — Tecnologias') e 'proj_X_desc' com uma descrição de impacto customizada focada nos requisitos da vaga.
6. Para as habilidades (skills_dev e skills_tools): Você DEVE incluir todas as tecnologias, ferramentas e conhecimentos técnicos explicitamente exigidos ou mencionados nos requisitos da vaga, utilizando exatamente os mesmos termos/palavras que a vaga pede (mesmo que elas não estejam no banco de dados do candidato). Além destas, inclua as habilidades reais do candidato do banco de dados que sejam pertinentes ou complementares. Divida-as logicamente entre 'skills_dev' (linguagens, frameworks, conceitos de IA e arquitetura) e 'skills_tools' (ferramentas, cloud, bancos de dados, metodologias, infraestrutura). Retorne cada bloco como uma string com itens separados por vírgula.
7. Para a tagline: Adapte o título/perfil profissional para ecoar os requisitos essenciais da vaga utilizando as qualificações reais do candidato.
8. Para o resumo: Reescreva-o completamente a partir do resumo master e das conquistas do candidato, destacando as competências, tempo de experiência e principais resultados que mais chamam a atenção para essa vaga específica.
9. Use verbos de ação no passado para experiências e projetos (Desenvolveu, Implementou, Automatizou...).
10. Seja conciso — os textos adaptados devem ser focados, de alto impacto e diretos.
11. CRÍTICO (Tamanho do Currículo): O currículo final adaptado deve caber confortavelmente em NO MÁXIMO 2 páginas. Remova qualquer prolixidade, mantenha os bullets extremamente diretos, focados e de no máximo 2 linhas cada, priorizando o impacto das conquistas sem desperdiçar espaço."""

    if idioma == "Inglês (EN-US)":
        system += "\n\n12. REQUISITO CRÍTICO DE IDIOMA (INGLÊS): Você DEVE retornar todos os textos adaptados dentro do JSON rigorosamente em INGLÊS (EN-US), traduzindo tudo com excelência profissional de negócios (Business English). Cargos devem ser traduzidos (ex: 'Dev Júnior' vira 'Junior Developer'), datas devem estar em inglês (ex: 'Março 2026 – Atualmente' vira 'March 2026 – Present'), e as conquistas/bullets descritas em inglês usando verbos de ação fortes no passado (Designed, Implemented, Streamlined, Automated...)."

    user = f"""DESCRIÇÃO DA VAGA:
{descricao_vaga}

{"INFORMAÇÕES EXTRAS DO CANDIDATO:" + chr(10) + perfil_extra if perfil_extra and perfil_extra.strip() else ""}

BLOCOS DO CURRÍCULO PARA ADAPTAR:
{blocos_json}

Retorne o JSON com os mesmos blocos adaptados para a vaga acima."""

    if status_cb:
        status_cb("🤖 Sabiá-4 está adaptando o currículo...")


    response = client.chat.completions.create(
        model="sabia-4",

        messages=[
            {"role": "system", "content": system},
            {"role": "user",   "content": user},
        ],
        temperature=0.7,
        max_tokens=4096,
    )

    resposta = response.choices[0].message.content.strip()

    # Extrai o JSON de forma robusta
    import re
    json_str = resposta
    # Tenta encontrar bloco de código markdown
    match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", resposta, re.DOTALL)
    if match:
        json_str = match.group(1).strip()
    else:
        # Tenta pegar entre a primeira '{' e a última '}'
        first_brace = resposta.find("{")
        last_brace = resposta.rfind("}")
        if first_brace != -1 and last_brace != -1 and last_brace > first_brace:
            json_str = resposta[first_brace:last_brace+1].strip()

    try:
        return json.loads(json_str)
    except json.JSONDecodeError as e:
        raise ValueError(f"Sabiá-4 retornou JSON inválido: {e}\n\nResposta (original):\n{resposta[:1000]}")




# ─────────────────────────────────────────────────────────────────────────────
# Reescrita do XML com os blocos adaptados
# ─────────────────────────────────────────────────────────────────────────────

def _registrar_namespaces_do_xml(xml_bytes: bytes):
    """
    Lê as declarações xmlns do XML original e as registra no ET,
    garantindo que ET.tostring preserve os prefixos exatos (w:, w14:, etc).
    """
    import re
    # Extrai todos os xmlns:prefix="uri" do root element
    declaracoes = re.findall(r'xmlns:([a-zA-Z0-9_]+)="([^"]+)"', xml_bytes.decode("utf-8", errors="ignore")[:4000])
    for prefix, uri in declaracoes:
        try:
            ET.register_namespace(prefix, uri)
        except Exception:
            pass
    # Garante que o namespace principal w: está registrado
    ET.register_namespace("w", NS)


def aplicar_blocos_no_xml(xml_bytes: bytes, blocos_originais: dict, blocos_adaptados: dict, idioma: str = "Português (PT-BR)", perfil_dados: dict = None) -> bytes:
    """
    Aplica os blocos adaptados de volta no XML, preservando toda a estrutura.
    Retorna os bytes do XML modificado.
    """
    # Registra TODOS os namespaces do documento original antes de parsear
    _registrar_namespaces_do_xml(xml_bytes)

    root = ET.fromstring(xml_bytes)

    # Substitui nome, email e rótulos de links se fornecidos
    if perfil_dados:
        pessoal = perfil_dados.get("dados_pessoais", {})
        novo_nome    = pessoal.get("nome")
        novo_email   = pessoal.get("email")
        novo_website = pessoal.get("website", "")
        novo_github  = pessoal.get("github", "")
        novo_linkedin = pessoal.get("linkedin", "")

        # Formata URL curta para exibição (remove https://)
        def _url_curta(url: str) -> str:
            return url.replace("https://", "").replace("http://", "").rstrip("/")

        for elem in root.iter(f"{W}t"):
            if elem.text:
                t = elem.text.strip()
                if novo_nome and (t == "Pietro Turci Moraes Martins"):
                    elem.text = novo_nome + (" " if elem.text.endswith(" ") else "")
                elif novo_email and t == "pietro.turcimm@gmail.com":
                    elem.text = novo_email
                # Substitui rótulo "Portfolio" pela URL real (visível na impressão)
                elif t == "Portfolio" and novo_website:
                    elem.text = _url_curta(novo_website)
                # Substitui "GitHub" pelo URL real
                elif t == "GitHub" and novo_github:
                    elem.text = _url_curta(novo_github)
                # Substitui "LinkedIn" pelo URL real
                elif t == "LinkedIn" and novo_linkedin:
                    elem.text = _url_curta(novo_linkedin)

    body = root.find(f"{W}body")
    paragrafos = list(body)

    # Reconstrói o mapeamento para saber qual parágrafo corresponde a qual bloco
    secao_atual = "inicio"
    exp_idx = -1
    proj_idx = -1
    em_bullets_exp = False
    em_bullets_proj = False
    tagline_capturado = False
    resumo_capturado  = False
    bullet_exp_contadores = {}  # exp_idx -> próximo índice de bullet para verificar

    for p in paragrafos:
        if p.tag != f"{W}p":
            continue

        texto = _texto_do_paragrafo(p)
        if not texto:
            continue

        nova_secao = _detectar_secao_atual(texto, secao_atual)
        if nova_secao != secao_atual:
            secao_atual = nova_secao
            em_bullets_exp  = False
            em_bullets_proj = False
            
            # Se o idioma for inglês, traduz os cabeçalhos das seções no XML
            if idioma == "Inglês (EN-US)":
                mapa_traducao = {
                    "habilidades": "SKILLS",
                    "experiencia": "EXPERIENCE",
                    "projetos": "PROJECTS",
                    "educacao": "EDUCATION"
                }
                traduzido = mapa_traducao.get(secao_atual)
                if traduzido:
                    _substituir_texto_paragrafo(p, traduzido)
            continue

        # ── INÍCIO ──────────────────────────────────────────────────────────
        if secao_atual == "inicio":
            runs = p.findall(f".//{W}r")
            if runs and not tagline_capturado:
                primeiro_run = runs[0]
                rPr = primeiro_run.find(f"{W}rPr")
                if rPr is not None and rPr.find(f"{W}b") is not None:
                    if len(texto) > 20 and "Pietro" not in texto:
                        novo = blocos_adaptados.get("tagline", texto)
                        if novo != texto:
                            _substituir_texto_paragrafo(p, novo)
                        tagline_capturado = True
                        continue

            if tagline_capturado and not resumo_capturado and len(texto) > 50:
                novo = blocos_adaptados.get("resumo", texto)
                if novo != texto:
                    _substituir_texto_paragrafo(p, novo)
                resumo_capturado = True
                continue

        elif secao_atual == "habilidades":
            if "python" in texto.lower() or "javascript" in texto.lower():
                novo_skills = blocos_adaptados.get("skills_dev")
                if novo_skills:
                    if isinstance(novo_skills, list):
                        novo_skills = ", ".join(novo_skills)
                    # Precisamos substituir apenas a parte DEPOIS do label bold
                    runs = p.findall(f".//{W}r")
                    label_run = None
                    content_runs = []
                    for r in runs:
                        rPr = r.find(f"{W}rPr")
                        t = r.find(f"{W}t")
                        if rPr is not None and rPr.find(f"{W}b") is not None:
                            label_run = r
                        elif t is not None and t.text and t.text.strip() and label_run is not None:
                            content_runs.append(r)

                    if content_runs:
                        # Coloca o novo texto no primeiro run de conteúdo
                        t0 = content_runs[0].find(f"{W}t")
                        if t0 is not None:
                            t0.text = " " + novo_skills
                            t0.set("{http://www.w3.org/XML/1998/namespace}space", "preserve")
                        # Traduz a label se for inglês
                        if label_run is not None and idioma == "Inglês (EN-US)":
                            t_lbl = label_run.find(f"{W}t")
                            if t_lbl is not None:
                                t_lbl.text = "Development & AI:"
                        # Limpa os demais
                        for r in content_runs[1:]:
                            for t in r.findall(f"{W}t"):
                                t.text = ""

            elif "git" in texto.lower() or "docker" in texto.lower():
                novo_skills = blocos_adaptados.get("skills_tools")
                if novo_skills:
                    if isinstance(novo_skills, list):
                        novo_skills = ", ".join(novo_skills)
                    runs = p.findall(f".//{W}r")
                    label_run = None
                    content_runs = []
                    for r in runs:
                        rPr = r.find(f"{W}rPr")
                        t = r.find(f"{W}t")
                        if rPr is not None and rPr.find(f"{W}b") is not None:
                            label_run = r
                        elif t is not None and t.text and t.text.strip() and label_run is not None:
                            content_runs.append(r)

                    if content_runs:
                        t0 = content_runs[0].find(f"{W}t")
                        if t0 is not None:
                            t0.text = " " + novo_skills
                            t0.set("{http://www.w3.org/XML/1998/namespace}space", "preserve")
                        # Traduz a label se for inglês
                        if label_run is not None and idioma == "Inglês (EN-US)":
                            t_lbl = label_run.find(f"{W}t")
                            if t_lbl is not None:
                                t_lbl.text = "Tools & Others:"
                        for r in content_runs[1:]:
                            for t in r.findall(f"{W}t"):
                                t.text = ""

        # ── EXPERIÊNCIA ─────────────────────────────────────────────────────
        elif secao_atual == "experiencia":
            runs = p.findall(f".//{W}r")
            primeiro_run_com_b = None
            for r in runs:
                rPr = r.find(f"{W}rPr")
                if rPr is not None and rPr.find(f"{W}b") is not None:
                    t_elem = r.find(f"{W}t")
                    if t_elem is not None and t_elem.text and len(t_elem.text.strip()) > 3:
                        primeiro_run_com_b = t_elem.text.strip()
                        break

            numPr = p.find(f".//{W}numPr")

            if numPr is not None and em_bullets_exp and exp_idx >= 0:
                chave_bullets = f"exp_{exp_idx}_bullets"
                bullets_adaptados = blocos_adaptados.get(chave_bullets, [])
                bullets_originais  = blocos_originais.get(chave_bullets, [])

                # Qual índice de bullet é este parágrafo?
                if exp_idx not in bullet_exp_contadores:
                    bullet_exp_contadores[exp_idx] = 0
                idx_bullet = bullet_exp_contadores[exp_idx]
                bullet_exp_contadores[exp_idx] += 1

                if idx_bullet < len(bullets_adaptados):
                    novo_bullet = bullets_adaptados[idx_bullet]
                    if novo_bullet != texto:
                        _substituir_texto_paragrafo(p, novo_bullet)

            elif primeiro_run_com_b and "," in texto:
                exp_idx += 1
                em_bullets_exp = True
                chave_titulo = f"exp_{exp_idx}_titulo"
                novo_titulo = blocos_adaptados.get(chave_titulo)
                if novo_titulo and novo_titulo != texto:
                    aplicar_titulo_experiencia_preservando_formatacao(p, novo_titulo)

        # ── PROJETOS ────────────────────────────────────────────────────────
        elif secao_atual == "projetos":
            numPr = p.find(f".//{W}numPr")
            runs  = p.findall(f".//{W}r")

            eh_titulo_proj = False
            for r in runs:
                rPr = r.find(f"{W}rPr")
                if rPr is not None:
                    sz = rPr.find(f"{W}sz")
                    if sz is not None and sz.get(f"{W}val") == "28":
                        eh_titulo_proj = True
                        break

            if eh_titulo_proj and numPr is None:
                proj_idx += 1
                em_bullets_proj = True
                chave_titulo = f"proj_{proj_idx}_title"
                novo_titulo = blocos_adaptados.get(chave_titulo)
                if novo_titulo and novo_titulo != texto:
                    aplicar_titulo_projeto_preservando_formatacao(p, novo_titulo)
            elif numPr is not None and em_bullets_proj and proj_idx >= 0:
                chave = f"proj_{proj_idx}_desc"
                novo = blocos_adaptados.get(chave)
                if novo and novo != texto:
                    _substituir_texto_paragrafo(p, novo)


        elif secao_atual == "educacao":
            if idioma == "Inglês (EN-US)":
                if "bacharel" in texto.lower() or "ciencia da computacao" in texto.lower():
                    _substituir_texto_paragrafo(p, "IFSP – Bachelor of Science in Computer Science")
                elif "esperado" in texto.lower():
                    _substituir_texto_paragrafo(p, " Expected Graduation: December 2027")
                elif "tecnico em desenvolvimento" in texto.lower() or "diploma tecnico" in texto.lower():
                    _substituir_texto_paragrafo(p, "ETEC – Technical Diploma in Systems Development")
                elif "completo" in texto.lower():
                    _substituir_texto_paragrafo(p, " Completed: December 2023")

    # Serializa de volta para bytes mantendo a declaração XML
    xml_out = ET.tostring(root, encoding="unicode", xml_declaration=False)
    return ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\r\n' + xml_out).encode("utf-8")


# ─────────────────────────────────────────────────────────────────────────────
# Pipeline principal
# ─────────────────────────────────────────────────────────────────────────────

def adaptar_docx(
    template_bytes: bytes,
    descricao_vaga: str,
    perfil_extra: str,
    api_key: str,
    idioma: str = "Português (PT-BR)",
    status_cb=None,
) -> bytes:
    """
    Pipeline completo:
      1. Lê o DOCX template
      2. Extrai blocos editáveis
      3. Adapta via Claude
      4. Reescreve XML
      5. Retorna bytes do novo DOCX
    """

    # 1. Desempacota o DOCX
    if status_cb:
        status_cb("📄 Lendo estrutura do currículo template...")

    with zipfile.ZipFile(io.BytesIO(template_bytes), "r") as zin:
        arquivos = {name: zin.read(name) for name in zin.namelist()}

    xml_original = arquivos["word/document.xml"]

    # 2. Extrai blocos editáveis
    if status_cb:
        status_cb("🔍 Mapeando seções do currículo...")

    blocos = extrair_blocos_editaveis(xml_original)

    if not blocos:
        raise ValueError("Não foi possível identificar blocos editáveis no DOCX. Verifique se o arquivo é o template correto.")

    # 3. Adapta via Claude
    blocos_adaptados = adaptar_via_claude(blocos, descricao_vaga, perfil_extra, api_key, idioma, status_cb)

    # 4. Reescreve o XML
    if status_cb:
        status_cb("✏️ Aplicando adaptações no documento...")

    xml_novo = aplicar_blocos_no_xml(xml_original, blocos, blocos_adaptados, idioma)

    # 5. Reempacota o DOCX
    if status_cb:
        status_cb("📦 Gerando arquivo final...")

    buf_out = io.BytesIO()
    with zipfile.ZipFile(buf_out, "w", zipfile.ZIP_DEFLATED) as zout:
        for name, data in arquivos.items():
            if name == "word/document.xml":
                zout.writestr(name, xml_novo)
            else:
                zout.writestr(name, data)

    return buf_out.getvalue()
