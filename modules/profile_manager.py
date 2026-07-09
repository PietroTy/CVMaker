"""
modules/profile_manager.py — Gerenciador do Banco de Dados Pessoal (JSON)
"""

import os
import json
import pathlib
from typing import Optional

# Caminho padrão para o banco de dados JSON do usuário
PROFILE_PATH = pathlib.Path(__file__).parent.parent / "perfil_usuario.json"


def obter_estrutura_vazia() -> dict:
    """Retorna um dicionário vazio com a estrutura de perfil recomendada."""
    return {
        "dados_pessoais": {
            "nome": "Pietro Turci Moraes Martins",
            "cargo": "Desenvolvedor Full-stack, Pesquisador e Especialista em Automação e IA",
            "email": "",
            "telefone": "",
            "localizacao": "",
            "linkedin": "",
            "github": "https://github.com/PietroTy",
            "website": ""
        },
        "resumo": "",
        "habilidades": {
            "dev_ia": "",
            "ferramentas": "",
            "outras": ""
        },
        "educacao": [],
        "experiencias": [],
        "projetos": [],
        "certificacoes": [],
        "preferencias": {
            "instrucoes_customizadas": "Sempre adote um tom profissional, técnico e focado em resultados tangíveis. Enfatize competências de desenvolvimento de software, arquitetura de sistemas e Inteligência Artificial."
        }
    }


def salvar_perfil(dados: dict, caminho: pathlib.Path = PROFILE_PATH):
    """Salva os dados do perfil em formato JSON indentado."""
    with open(caminho, "w", encoding="utf-8") as f:
        json.dump(dados, f, ensure_ascii=False, indent=2)


def carregar_perfil(caminho: pathlib.Path = PROFILE_PATH) -> dict:
    """Carrega o perfil do JSON ou retorna a estrutura vazia se não existir."""
    if not caminho.exists():
        # Tenta criar com valores padrões vazios
        dados = obter_estrutura_vazia()
        salvar_perfil(dados, caminho)
        return dados
    
    try:
        with open(caminho, "r", encoding="utf-8") as f:
            dados = json.load(f)
            
            # Garante que chaves essenciais existam (retrocompatibilidade/preenchimento automático)
            estrutura_padrao = obter_estrutura_vazia()
            for k, v in estrutura_padrao.items():
                if k not in dados:
                    dados[k] = v
                elif isinstance(v, dict):
                    for sub_k, sub_v in v.items():
                        if sub_k not in dados[k]:
                            dados[k][sub_k] = sub_v
            return dados
    except Exception:
        return obter_estrutura_vazia()


def importar_de_docx_blocos(blocos: dict) -> dict:
    """
    Converte os blocos extraídos do CurrículoVbra.docx em nossa estrutura JSON.
    Isso acelera o preenchimento inicial do banco de dados do usuário!
    """
    dados = obter_estrutura_vazia()
    
    # 1. Dados Pessoais / Tagline
    if "tagline" in blocos:
        dados["dados_pessoais"]["cargo"] = blocos["tagline"]
    
    # 2. Resumo
    if "resumo" in blocos:
        dados["resumo"] = blocos["resumo"]
        
    # 3. Habilidades
    if "skills_dev" in blocos:
        dados["habilidades"]["dev_ia"] = blocos["skills_dev"]
    if "skills_tools" in blocos:
        dados["habilidades"]["ferramentas"] = blocos["skills_tools"]
        
    # 4. Experiências
    # Percorre exp_0_titulo, exp_0_bullets, etc.
    exp_ids = sorted(list(set(
        int(k.split("_")[1]) for k in blocos.keys() if k.startswith("exp_") and k.split("_")[1].isdigit()
    )))
    
    for idx in exp_ids:
        titulo_bruto = blocos.get(f"exp_{idx}_titulo", "")
        bullets = blocos.get(f"exp_{idx}_bullets", [])
        
        # Tenta separar Cargo, Empresa e Período
        cargo = titulo_bruto
        empresa = ""
        periodo = ""
        
        # Exemplo de formato comum: "Desenvolvedor Sênior, Google – 2021 a Presente"
        if "," in titulo_bruto:
            partes = titulo_bruto.split(",", 1)
            cargo = partes[0].strip()
            resto = partes[1].strip()
            if "–" in resto:
                partes_resto = resto.split("–", 1)
                empresa = partes_resto[0].strip()
                periodo = partes_resto[1].strip()
            elif "-" in resto:
                partes_resto = resto.split("-", 1)
                empresa = partes_resto[0].strip()
                periodo = partes_resto[1].strip()
            else:
                empresa = resto
        elif "–" in titulo_bruto:
            partes = titulo_bruto.split("–", 1)
            cargo = partes[0].strip()
            periodo = partes[1].strip()
        
        dados["experiencias"].append({
            "empresa": empresa,
            "cargo": cargo,
            "periodo": periodo,
            "localizacao": "",
            "bullets": bullets if isinstance(bullets, list) else [bullets]
        })
        
    # 5. Projetos
    proj_ids = sorted(list(set(
        int(k.split("_")[1]) for k in blocos.keys() if k.startswith("proj_") and k.split("_")[1].isdigit()
    )))
    
    for idx in proj_ids:
        desc = blocos.get(f"proj_{idx}_desc", "")
        # Como o título do projeto nem sempre é extraído como chave isolada no xml_adapter,
        # criamos um nome genérico que o usuário possa renomear no banco de dados.
        dados["projetos"].append({
            "nome": f"Projeto {idx + 1}",
            "descricao": desc,
            "tecnologias": "",
            "link": ""
        })
        
    return dados


def compilar_perfil_para_prompt(dados: dict) -> str:
    """
    Formata todos os dados do perfil em um bloco Markdown detalhado e limpo.
    Esse bloco será usado pela IA como o contexto absoluto e soberano do candidato.
    """
    pessoal = dados.get("dados_pessoais", {})
    hab = dados.get("habilidades", {})
    
    md = []
    md.append("# 🧠 PERFIL MASTER DO CANDIDATO (FONTE DA VERDADE)")
    md.append(f"**Nome:** {pessoal.get('nome', 'Não especificado')}")
    md.append(f"**Cargo Alvo Principal:** {pessoal.get('cargo', 'Não especificado')}")
    
    contatos = []
    if pessoal.get("email"): contatos.append(f"Email: {pessoal.get('email')}")
    if pessoal.get("telefone"): contatos.append(f"Telefone: {pessoal.get('telefone')}")
    if pessoal.get("localizacao"): contatos.append(f"Localização: {pessoal.get('localizacao')}")
    if pessoal.get("linkedin"): contatos.append(f"LinkedIn: {pessoal.get('linkedin')}")
    if pessoal.get("github"): contatos.append(f"GitHub: {pessoal.get('github')}")
    if pessoal.get("website"): contatos.append(f"Portfólio: {pessoal.get('website')}")
    
    if contatos:
        md.append("**Contatos & Links:** " + " | ".join(contatos))
        
    md.append("\n## 📝 RESUMO PROFISSIONAL")
    md.append(dados.get("resumo", "Não especificado"))
    
    md.append("\n## 💻 HABILIDADES")
    md.append(f"- **Desenvolvimento & IA:** {hab.get('dev_ia', 'Não especificado')}")
    md.append(f"- **Ferramentas & Infraestrutura:** {hab.get('ferramentas', 'Não especificado')}")
    if hab.get("outras"):
        md.append(f"- **Outras Competências / Idiomas:** {hab.get('outras')}")
        
    md.append("\n## 💼 EXPERIÊNCIAS PROFISSIONAIS COMPLETAS")
    exps = dados.get("experiencias", [])
    if not exps:
        md.append("_Nenhuma experiência cadastrada no banco de dados ainda._")
    for i, exp in enumerate(exps):
        empresa_str = f" na {exp.get('empresa')}" if exp.get("empresa") else ""
        periodo_str = f" ({exp.get('periodo')})" if exp.get("periodo") else ""
        loc_str = f" - {exp.get('localizacao')}" if exp.get("localizacao") else ""
        
        md.append(f"\n### {i+1}. {exp.get('cargo')}{empresa_str}{periodo_str}{loc_str}")
        for b in exp.get("bullets", []):
            if b.strip():
                md.append(f"  • {b}")
                
    md.append("\n## 🚀 PROJETOS EXTRAS & PORTFÓLIO")
    projs = dados.get("projetos", [])
    if not projs:
        md.append("_Nenhum projeto cadastrado no banco de dados ainda._")
    for i, proj in enumerate(projs):
        link_str = f" (Link: {proj.get('link')})" if proj.get('link') else ""
        tech_str = f" [Tecnologias: {proj.get('tecnologias')}]" if proj.get('tecnologias') else ""
        md.append(f"\n### {proj.get('nome')}{link_str}{tech_str}")
        md.append(proj.get("descricao", ""))
        
    md.append("\n## 🎓 FORMAÇÃO ACADÊMICA")
    edus = dados.get("educacao", [])
    if not edus:
        md.append("_Nenhuma formação cadastrada no banco de dados._")
    for i, edu in enumerate(edus):
        status_str = f" — {edu.get('status')}" if edu.get('status') else ""
        conclusao_str = f" (Conclusão: {edu.get('conclusao_esperada')})" if edu.get('conclusao_esperada') else ""
        md.append(f"\n### {i+1}. {edu.get('curso', 'Curso')}{status_str}{conclusao_str}")
        md.append(f"  **Instituição:** {edu.get('instituicao', 'N/A')} | **Tipo:** {edu.get('tipo', 'N/A')}")
        if edu.get('destaque'):
            md.append(f"  **Destaque:** {edu.get('destaque')}")

    md.append("\n## 🏅 CERTIFICAÇÕES & CONQUISTAS")
    certs = dados.get("certificacoes", [])
    if not certs:
        md.append("_Nenhuma certificação cadastrada._")
    for cert in certs:
        if cert.strip():
            md.append(f"- {cert}")
            
    # Preferências / Diretrizes customizadas
    pref = dados.get("preferencias", {})
    if pref.get("instrucoes_customizadas"):
        md.append("\n## ⚙️ DIRETRIZES PESSOAIS DE ADAPTAÇÃO (CRÍTICO)")
        md.append(pref.get("instrucoes_customizadas"))
        
    return "\n".join(md)
