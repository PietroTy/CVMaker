"""
app.py — CV Adapter
Adapta seu currículo DOCX para vagas específicas usando Claude AI.
Interface ultra-clean e de alta estética, focada 100% na produtividade.
"""

import io
import os
import streamlit as st
from dotenv import load_dotenv
from modules.profile_manager import (
    carregar_perfil,
    salvar_perfil,
    compilar_perfil_para_prompt
)

load_dotenv()

# ─────────────────────────────────────────────────────────────────────────────
# Configuração da página
# ─────────────────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="CV Adapter",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─────────────────────────────────────────────────────────────────────────────
# Inicializa perfil: prioriza cache do navegador (query param) > disco
# ─────────────────────────────────────────────────────────────────────────────
import json as _json
import base64 as _base64

if "perfil_edicao" not in st.session_state:
    _perfil_cache = st.query_params.get("p", "")
    if _perfil_cache:
        try:
            _decoded = _json.loads(_base64.b64decode(_perfil_cache.encode()).decode())
            st.session_state["perfil_edicao"] = _decoded
        except Exception:
            st.session_state["perfil_edicao"] = carregar_perfil()
    else:
        st.session_state["perfil_edicao"] = carregar_perfil()

PERFIL_TEMPLATE_DUMMY = {
    "dados_pessoais": {
        "nome": "Seu Nome Completo",
        "cargo": "Seu Cargo Alvo / Tagline Profissional",
        "email": "seu.email@exemplo.com",
        "telefone": "+55 (11) 99999-9999",
        "localizacao": "Cidade, Estado, Brasil",
        "linkedin": "https://linkedin.com/in/seu-perfil",
        "github": "https://github.com/seu-usuario",
        "website": "https://seusite.com"
    },
    "resumo": "Profissional com X anos de experiência em [área]. Graduado em [Curso] pela [Instituição]. Especializado em [tecnologias/áreas principais]. Experiência comprovada em [conquista relevante]. Inglês [nível].",
    "habilidades": {
        "dev_ia": "Tecnologia 1, Tecnologia 2, Tecnologia 3, Framework 1, Framework 2, Linguagem 1",
        "ferramentas": "Ferramenta 1, Ferramenta 2, Metodologia 1, Plataforma 1, Cloud 1",
        "outras": "Inglês Fluente, Espanhol Intermediário, Liderança, Comunicação, Trabalho em Equipe"
    },
    "educacao": [
        {
            "instituicao": "Nome da Universidade / Faculdade",
            "curso": "Bacharelado em [Área de Estudo]",
            "periodo": "Esperado: Mês AAAA",
            "descricao": "Destaques relevantes, projetos acadêmicos ou iniciação científica."
        },
        {
            "instituicao": "Nome da Escola Técnica / Curso",
            "curso": "Técnico em [Área] ou Curso de [Tema]",
            "periodo": "Completo: Mês AAAA",
            "descricao": ""
        }
    ],
    "experiencias": [
        {
            "empresa": "Nome da Empresa Atual",
            "cargo": "Seu Cargo Atual",
            "periodo": "Mês AAAA – Atualmente",
            "localizacao": "Cidade, Estado, Brasil · Presencial / Remoto / Híbrido",
            "tipo_contrato": "Efetivo / Estágio / PJ / Freelance",
            "bullets": [
                "Descreva sua principal responsabilidade com foco em resultado concreto e mensurável.",
                "Conquista quantitativa relevante (ex: reduziu X% no tempo de Y processo usando Tecnologia Z).",
                "Projeto ou entrega estratégica que você liderou ou foi protagonista.",
                "Colaboração com times ou stakeholders que gerou impacto no negócio."
            ]
        },
        {
            "empresa": "Nome da Empresa Anterior",
            "cargo": "Cargo Anterior",
            "periodo": "Mês AAAA – Mês AAAA",
            "localizacao": "Cidade, Estado, Brasil · Presencial",
            "tipo_contrato": "Estágio",
            "bullets": [
                "Responsabilidade principal no cargo, focando em entregas concretas.",
                "Resultado quantitativo alcançado durante o período.",
                "Projeto relevante liderado utilizando tecnologias e ferramentas chave."
            ]
        }
    ],
    "projetos": [
        {
            "nome": "Nome do Projeto 1",
            "descricao": "Descrição clara do projeto, arquitetura utilizada, problema que resolve e resultado. Mencione tecnologias chave e link de acesso.",
            "tecnologias": "Tecnologia 1, Framework 1, Banco de Dados 1",
            "link": "https://link-do-projeto.com",
            "repo": "https://github.com/seu-usuario/projeto-1"
        },
        {
            "nome": "Nome do Projeto 2",
            "descricao": "Descrição do segundo projeto com destaque para impacto técnico e inovação aplicada.",
            "tecnologias": "Tecnologia 2, API X, Plataforma Y",
            "link": "",
            "repo": "https://github.com/seu-usuario/projeto-2"
        }
    ],
    "certificacoes": [
        "Nome do Certificado 1 — Instituição Emissora (Carga Horária)",
        "Nome do Certificado 2 — Instituição Emissora",
        "Idioma: Nível — Exame ou Escola"
    ],
    "preferencias": {
        "instrucoes_customizadas": "Sempre adote um tom profissional e focado em resultados tangíveis. Destaque [pontos fortes específicos do candidato]. Priorize experiências relacionadas a [área-alvo]. O currículo final deve caber em no máximo 2 páginas, sem inventar informações."
    }
}

# ─────────────────────────────────────────────────────────────────────────────
# CSS customizado - Estética Premium (Streamlit Style com Emojis)
# ─────────────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
    /* Faixa de destaque no topo (Streamlit Signature Bar) */
    .stApp::before {
        content: "";
        position: fixed;
        top: 0;
        left: 0;
        right: 0;
        height: 6px;
        background: linear-gradient(90deg, #ff4b4b 0%, #ff758c 50%, #ff9f43 100%);
        z-index: 999999;
    }

    /* Fundo geral escuro e sofisticado */
    .stApp {
        background-color: #0e1117 !important;
        color: #ffffff !important;
        font-family: 'Inter', -apple-system, sans-serif;
    }

    /* Ajuste de cabeçalho e menu padrão (mantém header transparente para exibir botão de toggle do sidebar) */
    header { background: transparent !important; }
    footer { visibility: hidden; }
    #MainMenu { visibility: hidden; }

    /* Barra lateral customizada */
    [data-testid="stSidebar"] {
        background-color: #161b22 !important;
        border-right: 1px solid rgba(255, 255, 255, 0.08) !important;
    }
    [data-testid="stSidebar"] * {
        color: #ffffff !important;
    }

    /* Quebra de linha forçada em toda a sidebar */
    [data-testid="stSidebar"] p,
    [data-testid="stSidebar"] li,
    [data-testid="stSidebar"] span,
    [data-testid="stSidebar"] div,
    [data-testid="stSidebar"] label {
        word-wrap: break-word !important;
        overflow-wrap: break-word !important;
        word-break: break-word !important;
        white-space: normal !important;
        max-width: 100% !important;
    }

    /* Código inline na sidebar — quebra palavras longas */
    [data-testid="stSidebar"] code {
        display: inline-block !important;
        max-width: 100% !important;
        word-break: break-all !important;
        white-space: normal !important;
    }

    /* Estilo do Bloco Principal (Card Central) */
    div.block-container {
        max-width: 950px !important;
        padding: 3rem 4rem !important;
        background-color: #1f2937 !important;
        border: 1px solid rgba(255, 255, 255, 0.08) !important;
        border-radius: 12px !important;
        box-shadow: 0 8px 30px rgba(0, 0, 0, 0.35) !important;
        margin-top: 40px !important;
        margin-bottom: 40px !important;
    }

    /* Título principal e subtítulo com cor sólida para manter emojis com cores originais */
    .main-title {
        font-size: 2.8rem;
        font-weight: 800;
        letter-spacing: -0.04rem;
        color: #ffffff;
        margin-bottom: 8px;
        display: flex;
        align-items: center;
        gap: 12px;
    }

    .main-subtitle {
        color: #dde3ee;
        font-size: 1.1rem;
        font-weight: 400;
        margin-bottom: 24px;
        line-height: 1.6;
    }

    /* Estilo para blocos de código inline (markdown `code`) */
    code {
        background-color: rgba(255, 255, 255, 0.08) !important;
        color: #ff758c !important;
        padding: 2px 6px !important;
        border-radius: 4px !important;
        font-size: 0.9em !important;
        border: 1px solid rgba(255, 255, 255, 0.1) !important;
        font-family: monospace !important;
    }

    /* Caixas de entrada (Textarea e Inputs) */
    div[data-testid="stTextInput"] input, div[data-testid="stTextArea"] textarea {
        background-color: #0d1117 !important;
        border: 1px solid rgba(255, 255, 255, 0.1) !important;
        border-radius: 8px !important;
        color: #ffffff !important;
        font-size: 1rem !important;
        padding: 12px !important;
        box-shadow: inset 0 2px 4px rgba(0,0,0,0.2) !important;
    }
    div[data-testid="stTextInput"] input:focus, div[data-testid="stTextArea"] textarea:focus {
        border-color: #ff4b4b !important;
        box-shadow: 0 0 0 2px rgba(255, 75, 75, 0.2) !important;
    }

    /* Botão primário customizado (Streamlit Red) */
    .stButton > button[kind="primary"] {
        background: linear-gradient(135deg, #ff4b4b, #ff758c) !important;
        border: none !important;
        border-radius: 8px !important;
        color: white !important;
        font-weight: 700 !important;
        padding: 12px 24px !important;
        font-size: 1.05rem !important;
        width: 100%;
        transition: all 0.2s ease-in-out !important;
        box-shadow: 0 4px 12px rgba(255, 75, 75, 0.3) !important;
    }
    .stButton > button[kind="primary"]:hover {
        transform: translateY(-2px) !important;
        box-shadow: 0 6px 16px rgba(255, 75, 75, 0.5) !important;
        opacity: 0.95 !important;
    }
    .stButton > button[kind="primary"]:active {
        transform: translateY(0) !important;
    }

    /* Botões secundários da página */
    .stButton > button[kind="secondary"] {
        background-color: #21262d !important;
        border: 1px solid rgba(255, 255, 255, 0.15) !important;
        border-radius: 8px !important;
        color: #ffffff !important;
        font-weight: 600 !important;
        width: 100%;
        transition: all 0.2s ease-in-out !important;
    }
    .stButton > button[kind="secondary"]:hover {
        background-color: #30363d !important;
        border-color: #ff4b4b !important;
        color: #ffffff !important;
    }

    /* Botão de Download de Destaque */
    .stDownloadButton > button {
        background: linear-gradient(135deg, #10b981, #059669) !important;
        border: none !important;
        border-radius: 8px !important;
        color: white !important;
        font-weight: 700 !important;
        padding: 12px 24px !important;
        font-size: 1.05rem !important;
        width: 100% !important;
        box-shadow: 0 4px 12px rgba(16, 185, 129, 0.3) !important;
        transition: all 0.2s ease-in-out !important;
    }
    .stDownloadButton > button:hover {
        transform: translateY(-2px) !important;
        box-shadow: 0 6px 16px rgba(16, 185, 129, 0.5) !important;
    }

    /* Estilo dos Expanders de comparação (Clean para o currículo) */
    div[data-testid="stExpander"] {
        background-color: #1f2937 !important;
        border: 1px solid rgba(255, 255, 255, 0.08) !important;
        border-radius: 8px !important;
        margin-bottom: 10px !important;
    }
    div[data-testid="stExpander"] summary {
        color: #ffffff !important;
        font-weight: 600 !important;
    }
    div[data-testid="stExpander"] div[role="region"] {
        background-color: #161b22 !important;
        border-top: 1px solid rgba(255, 255, 255, 0.08) !important;
        padding: 16px !important;
        color: #ffffff !important;
        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif !important;
    }

    /* Badges */
    .bloco-badge {
        display: inline-block;
        background: #2e3b4e;
        color: #dde3ee;
        border: 1px solid rgba(255, 255, 255, 0.1);
        border-radius: 6px;
        padding: 2px 10px;
        font-size: 0.75rem;
        font-weight: 600;
        margin-bottom: 6px;
    }

    /* Garante que todo texto genérico do Streamlit seja branco */
    .stApp p, .stApp span, .stApp label,
    .stApp li, .stApp td, .stApp th,
    .stApp .stMarkdown, .stApp .stText,
    [data-testid="stMarkdownContainer"] p,
    [data-testid="stMarkdownContainer"] li,
    [data-testid="stMarkdownContainer"] span {
        color: #ffffff !important;
    }
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────────────────
# Barra Lateral (Sidebar) — Estética Streamlit
# ─────────────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## 👤 Perfil Ativo")
    
    dados = st.session_state["perfil_edicao"]
    pessoal = dados.get("dados_pessoais", {})
    nome_candidato = pessoal.get("nome", "Usuário")
    cargo_candidato = pessoal.get("cargo", "Cargo não especificado")
    
    st.markdown(f"### **{nome_candidato}**")
    st.markdown(f"*{cargo_candidato}*")
    
    st.divider()
    
    st.markdown("### 📊 Dados Carregados")
    skills_dev = dados.get("habilidades", {}).get("dev_ia", "")
    skills_tools = dados.get("habilidades", {}).get("ferramentas", "")
    num_skills_dev = len([s for s in skills_dev.split(",") if s.strip()]) if skills_dev else 0
    num_skills_tools = len([s for s in skills_tools.split(",") if s.strip()]) if skills_tools else 0
    num_experiencias = len(dados.get("experiencias", []))
    num_projetos = len(dados.get("projetos", []))
    num_certificacoes = len(dados.get("certificacoes", []))
    num_educacao = len(dados.get("educacao", []))
    
    st.markdown(f"💼 **Experiências:** {num_experiencias}")
    st.markdown(f"🚀 **Projetos:** {num_projetos}")
    st.markdown(f"🎓 **Formações:** {num_educacao}")
    st.markdown(f"💻 **Habilidades Dev/IA:** {num_skills_dev}")
    st.markdown(f"🛠️ **Habilidades Ferramentas:** {num_skills_tools}")
    st.markdown(f"🏆 **Certificações:** {num_certificacoes}")
    
    st.divider()
    
    st.markdown("### 🌐 Redes & Contatos")
    email_cand = pessoal.get("email")
    github_cand = pessoal.get("github")
    linkedin_cand = pessoal.get("linkedin")
    
    if email_cand:
        st.markdown(f"✉️ **Email:** {email_cand}")
    if github_cand:
        st.markdown(f"💻 **GitHub:** [{github_cand.split('/')[-1]}]({github_cand})")
    if linkedin_cand:
        st.markdown(f"👔 **LinkedIn:** [Ver Perfil]({linkedin_cand})")
        
    st.divider()
    
    st.markdown("### 💡 Instruções de Configuração")
    st.markdown("""
    Para adaptar a aplicação ao seu próprio currículo, edite a estrutura JSON na aba correspondente:
    
    1. **`dados_pessoais`**: Nome e contatos. Nome e e-mail serão inseridos diretamente no topo do documento.
    2. **`dados_pessoais.github`**, **`linkedin`** e **`website`**: As URLs fornecidas substituirão os links do template Word original.
    3. **`resumo`**: O texto base do seu resumo profissional que a IA adaptará.
    4. **`experiencias`** e **`projetos`**: Adicione suas atuações anteriores. O modelo Sabiá-4 selecionará e adaptará estes dados de acordo com a vaga de destino.
    5. **`preferencias.instrucoes_customizadas`**: Diretrizes de tom ou foco técnico que a IA deve priorizar ao gerar as descrições.
    
    *Nota: Mantenha a mesma estrutura de chaves JSON.*
    """)
    
    # Botão para baixar o template DOCX vazio
    template_vazio_path = os.path.join(os.path.dirname(__file__), "TemplateVazio.docx")
    if os.path.exists(template_vazio_path):
        try:
            with open(template_vazio_path, "rb") as f:
                template_vazio_bytes = f.read()
            st.download_button(
                label="📄 Baixar Template DOCX Vazio",
                data=template_vazio_bytes,
                file_name="Template_CV_Vazio.docx",
                mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                use_container_width=True
            )
        except Exception:
            pass
            
    st.markdown("<br><p style='text-align: center; color: rgba(255,255,255,0.25); font-size: 0.8rem;'>© 2026 PietroTy</p>", unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────────────────────
# Funções auxiliares
# ─────────────────────────────────────────────────────────────────────────────

def converter_docx_para_pdf(docx_bytes: bytes) -> bytes | None:
    import subprocess
    import tempfile
    import os
    try:
        # Tenta encontrar soffice ou libreoffice no PATH do Linux
        binario = None
        for cmd in ["soffice", "libreoffice"]:
            if subprocess.run(["which", cmd], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).returncode == 0:
                binario = cmd
                break
        
        if not binario:
            return None
            
        with tempfile.TemporaryDirectory() as tmpdir:
            docx_path = os.path.join(tmpdir, "curriculo.docx")
            with open(docx_path, "wb") as f:
                f.write(docx_bytes)
                
            # Executa a conversão headless
            process = subprocess.run([
                binario,
                "--headless",
                "--convert-to", "pdf",
                "--outdir", tmpdir,
                docx_path
            ], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            
            if process.returncode != 0:
                return None
                
            pdf_path = os.path.join(tmpdir, "curriculo.pdf")
            if os.path.exists(pdf_path):
                with open(pdf_path, "rb") as f:
                    return f.read()
    except Exception:
        pass
    return None


def get_api_key() -> str | None:
    return os.environ.get("MARITACA_API_KEY")


def formatar_nome_bloco(chave: str) -> str:
    mapa = {
        "tagline":      "🎯 Tagline / Perfil",
        "resumo":       "📝 Resumo",
        "skills_dev":   "💻 Skills — Dev & IA",
        "skills_tools": "🛠️ Skills — Ferramentas",
    }
    if chave in mapa:
        return mapa[chave]
    if chave.startswith("exp_") and chave.endswith("_titulo"):
        n = int(chave.split("_")[1]) + 1
        return f"💼 Experiência {n} — Cargo & Empresa"
    if chave.startswith("exp_") and chave.endswith("_bullets"):
        n = int(chave.split("_")[1]) + 1
        return f"💼 Experiência {n} — Bullets"
    if chave.startswith("proj_") and chave.endswith("_title"):
        n = int(chave.split("_")[1]) + 1
        return f"🚀 Projeto {n} — Título & Tecnologias"
    if chave.startswith("proj_") and chave.endswith("_desc"):
        n = int(chave.split("_")[1]) + 1
        return f"🚀 Projeto {n} — Descrição"
    return chave


def renderizar_bloco(chave: str, original, adaptado):
    nome = formatar_nome_bloco(chave)
    with st.expander(nome, expanded=False):
        col_orig, col_adap = st.columns(2)
        with col_orig:
            st.markdown("<p style='color: #94a3b8; font-weight: 600;'>Original</p>", unsafe_allow_html=True)
            if isinstance(original, list):
                for b in original:
                    st.markdown(f"• {b}")
            else:
                st.markdown(original or "_vazio_")
        with col_adap:
            st.markdown("<p style='color: #60a5fa; font-weight: 600;'>✨ Adaptado</p>", unsafe_allow_html=True)
            if isinstance(adaptado, list):
                for b in adaptado:
                    st.markdown(f"• {b}")
            else:
                st.markdown(adaptado or "_sem alteração_")


# ─────────────────────────────────────────────────────────────────────────────
# Conteúdo Principal (Single Page ultra-clean)
# ─────────────────────────────────────────────────────────────────────────────

# Container Centralizado

# Cabeçalho do App com botão de configuração
col_header_title, col_header_btn = st.columns([3, 1])
with col_header_title:
    st.markdown('<h1 class="main-title">🎯 CV Adapter</h1>', unsafe_allow_html=True)
    st.markdown('<p class="main-subtitle">Cole a descrição da vaga e gere instantaneamente seu currículo cirurgicamente personalizado com IA. ⚡</p>', unsafe_allow_html=True)
with col_header_btn:
    show_editor = st.toggle(
        "⚙️ Editar Perfil JSON",
        value=False,
        help="Abra a experiência JSON completa para retirar o perfil atual e colocar o seu!"
    )

# ─────────────────────────────────────────────────────────────────────────────
# Componente do Editor de Perfil JSON (se ativado)
# ─────────────────────────────────────────────────────────────────────────────
if show_editor:
    import json
    st.markdown("### 📝 Editor de Perfil Profissional (JSON) ⚙️")
    st.markdown("""
    💡 **Seu perfil fica salvo apenas no cache do seu navegador** — nunca no servidor.
    Cole aqui o seu próprio JSON e clique em **Salvar**. Na próxima visita neste mesmo navegador, 
    seu perfil será restaurado automaticamente.
    """)

    dados_str = json.dumps(st.session_state["perfil_edicao"], indent=2, ensure_ascii=False)

    novo_json = st.text_area(
        "Edite a estrutura JSON do seu currículo:",
        value=dados_str,
        height=420,
        help="Certifique-se de manter a sintaxe JSON correta com aspas duplas."
    )

    col_save, col_template, col_clear = st.columns(3)

    with col_save:
        if st.button("💾 Salvar no Navegador", type="primary", use_container_width=True, key="btn_save_json"):
            try:
                dados_novos = json.loads(novo_json)
                if "dados_pessoais" not in dados_novos or "nome" not in dados_novos["dados_pessoais"]:
                    st.error("❌ O JSON deve conter a chave 'dados_pessoais' com um 'nome' válido!")
                else:
                    # Salva APENAS na session_state — nunca no disco
                    st.session_state["perfil_edicao"] = dados_novos
                    # Codifica em base64 para o localStorage/URL
                    _payload = _base64.b64encode(
                        json.dumps(dados_novos, ensure_ascii=False).encode()
                    ).decode()
                    # Injeta JS para gravar no localStorage e na URL (cache do navegador)
                    st.components.v1.html(f"""
                    <script>
                        const payload = "{_payload}";
                        localStorage.setItem('cvadapter_perfil', payload);
                        const url = new URL(window.parent.location.href);
                        url.searchParams.set('p', payload);
                        window.parent.history.replaceState(null, '', url.toString());
                    </script>
                    """, height=0)
                    st.success("✅ Perfil salvo no seu navegador! Ele será restaurado automaticamente na próxima visita. 🎉")
                    st.rerun()
            except json.JSONDecodeError as e:
                st.error(f"❌ JSON Inválido: {e}")

    with col_template:
        if st.button("📋 Carregar Template Genérico", use_container_width=True, key="btn_load_template"):
            st.session_state["perfil_edicao"] = PERFIL_TEMPLATE_DUMMY
            st.success("✅ Template genérico carregado! Preencha com seus dados e salve. 📋")
            st.rerun()

    with col_clear:
        if st.button("🗑️ Limpar Cache do Navegador", use_container_width=True, key="btn_clear_profile"):
            st.session_state["perfil_edicao"] = PERFIL_TEMPLATE_DUMMY
            # Remove do localStorage e da URL
            st.components.v1.html("""
            <script>
                localStorage.removeItem('cvadapter_perfil');
                const url = new URL(window.parent.location.href);
                url.searchParams.delete('p');
                window.parent.history.replaceState(null, '', url.toString());
            </script>
            """, height=0)
            st.success("✅ Cache limpo! Insira seu JSON e salve novamente. 🗑️")
            st.rerun()

    # Restore do localStorage ao carregar a página (JS → query param → Python no próximo rerun)
    st.components.v1.html("""
    <script>
        (function() {
            const stored = localStorage.getItem('cvadapter_perfil');
            if (!stored) return;
            const url = new URL(window.parent.location.href);
            if (url.searchParams.get('p') === stored) return;
            url.searchParams.set('p', stored);
            window.parent.history.replaceState(null, '', url.toString());
        })();
    </script>
    """, height=0)

    st.divider()

# Caixa de Texto para a vaga
st.markdown("### 📝 Requisitos / Descrição da Vaga Alvo 💼")
descricao_vaga = st.text_area(
    label="descricao_vaga",
    label_visibility="collapsed",
    height=240,
    placeholder="Cole aqui os requisitos ou a descrição completa da vaga (LinkedIn, Gupy, etc.)... 🔍",
)

st.markdown("<br>", unsafe_allow_html=True)

# Escolha do Idioma
col_lang, _ = st.columns([1, 1])
with col_lang:
    idioma = st.selectbox(
        "🌐 Idioma do Currículo Gerado",
        options=["Português (PT-BR)", "Inglês (EN-US)"],
        index=0,
        key="idioma_resume"
    )

st.markdown("<br>", unsafe_allow_html=True)

# Botão de Adaptação
adaptar_btn = st.button("✨ Adaptar Currículo com Sabiá-4 ⚡", type="primary", use_container_width=True)

# Local do Template Padrão
template_path = os.path.join(os.path.dirname(__file__), "CurrículoVbra.docx")
api_key = get_api_key()

if adaptar_btn:
    # Recarrega o perfil do disco para garantir que alterações manuais no JSON sejam lidas
    st.session_state["perfil_edicao"] = carregar_perfil()
    api_key = get_api_key()

    # Validações
    erros = []
    if not api_key:
        erros.append("❌ Chave API da Maritaca não encontrada. Configure a variável MARITACA_API_KEY no seu arquivo .env.")
    if not descricao_vaga.strip():
        erros.append("❌ Cole a descrição da vaga antes de continuar.")
    if not os.path.exists(template_path):
        erros.append("❌ Arquivo de template 'CurrículoVbra.docx' não encontrado na pasta raiz.")

    if erros:
        for e in erros:
            st.error(e)
        st.stop()

    # Executa a adaptação com feedbacks visuais elegantes
    status_placeholder = st.empty()
    progress_bar = st.progress(0)
    passos = [
        "📄 Lendo estrutura do currículo template...",
        "🔍 Mapeando seções do currículo...",
        "🤖 Sabiá-4 está adaptando o currículo...",
        "✏️ Aplicando adaptações no documento...",
        "📦 Gerando arquivo final..."
    ]

    def atualizar_status(msg: str):
        status_placeholder.info(msg)
        if msg in passos:
            idx = passos.index(msg)
            progress_bar.progress(int((idx + 1) / len(passos) * 100))

    try:
        from modules.xml_adapter import extrair_blocos_editaveis, adaptar_via_claude, aplicar_blocos_no_xml
        import zipfile
        import io as _io

        # Lê os bytes do template
        with open(template_path, "rb") as f:
            template_bytes = f.read()

        atualizar_status(passos[0])
        with zipfile.ZipFile(_io.BytesIO(template_bytes), "r") as z:
            xml_bytes = z.read("word/document.xml")

        atualizar_status(passos[1])
        blocos_originais = extrair_blocos_editaveis(xml_bytes)

        # Compila o contexto do perfil a partir do Banco JSON
        atualizar_status(passos[2])
        perf_dados_atuais = st.session_state["perfil_edicao"]
        perfil_completo_contexto = compilar_perfil_para_prompt(perf_dados_atuais)

        # Chama a API da Maritaca
        blocos_adaptados = adaptar_via_claude(
            blocos_originais, descricao_vaga, perfil_completo_contexto, api_key,
            idioma=idioma,
            status_cb=lambda m: atualizar_status(m)
        )

        atualizar_status(passos[3])
        arquivos = {}
        with zipfile.ZipFile(_io.BytesIO(template_bytes), "r") as zin:
            for name in zin.namelist():
                arquivos[name] = zin.read(name)

        # Passa perfil_dados para substituir Nome e Email no XML
        xml_novo = aplicar_blocos_no_xml(xml_bytes, blocos_originais, blocos_adaptados, idioma=idioma, perfil_dados=perf_dados_atuais)

        # Atualiza os links e hiperlinks no arquivo .rels se fornecidos no perfil
        rels_name = "word/_rels/document.xml.rels"
        if rels_name in arquivos:
            rels_str = arquivos[rels_name].decode("utf-8", errors="ignore")
            pessoal = perf_dados_atuais.get("dados_pessoais", {})
            if pessoal.get("github"):
                rels_str = rels_str.replace("https://github.com/PietroTy", pessoal["github"])
            if pessoal.get("website"):
                rels_str = rels_str.replace("https://pietroty.github.io/PietroTy/", pessoal["website"])
            if pessoal.get("linkedin"):
                rels_str = rels_str.replace("https://www.linkedin.com/in/pietro-turci-2a419229a/", pessoal["linkedin"])
                rels_str = rels_str.replace("https://br.linkedin.com/in/pietro-turci-2a419229a", pessoal["linkedin"])
            arquivos[rels_name] = rels_str.encode("utf-8")

        atualizar_status(passos[4])
        buf_out = _io.BytesIO()
        with zipfile.ZipFile(buf_out, "w", zipfile.ZIP_DEFLATED) as zout:
            for name, data in arquivos.items():
                if name == "word/document.xml":
                    zout.writestr(name, xml_novo)
                else:
                    zout.writestr(name, data)
        docx_bytes = buf_out.getvalue()

        progress_bar.progress(100)
        status_placeholder.success("✅ Currículo adaptado com sucesso!")

        # Guarda na session_state
        st.session_state["docx_bytes"]       = docx_bytes
        st.session_state["blocos_originais"] = blocos_originais
        st.session_state["blocos_adaptados"] = blocos_adaptados
        if "pdf_bytes" in st.session_state:
            del st.session_state["pdf_bytes"]

    except Exception as e:
        progress_bar.empty()
        status_placeholder.error(f"❌ Erro durante a adaptação: {e}")
        with st.expander("Ver detalhes do erro"):
            st.exception(e)
        st.stop()

# ─────────────────────────────────────────────────────────────────────────────
# Exibição de Resultados (Download & Comparação)
# ─────────────────────────────────────────────────────────────────────────────
if "docx_bytes" in st.session_state:
    st.divider()
    
    st.markdown("<h2 style='text-align: center; margin-bottom: 20px;'>📥 Download do Currículo</h2>", unsafe_allow_html=True)
    
    # Tenta converter/carregar PDF se disponível
    if "pdf_bytes" not in st.session_state:
        with st.spinner("📄 Convertendo documento para PDF..."):
            st.session_state["pdf_bytes"] = converter_docx_para_pdf(st.session_state["docx_bytes"])
            
    pdf_bytes = st.session_state.get("pdf_bytes")
    
    if pdf_bytes:
        col_word, col_pdf = st.columns(2)
        with col_word:
            st.download_button(
                label="⬇️ Baixar em Word (.docx)",
                data=st.session_state["docx_bytes"],
                file_name="curriculo_adaptado.docx",
                mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                use_container_width=True,
            )
        with col_pdf:
            st.download_button(
                label="⬇️ Baixar em PDF (.pdf)",
                data=pdf_bytes,
                file_name="curriculo_adaptado.pdf",
                mime="application/pdf",
                use_container_width=True,
            )
    else:
        col_dl_btn, col_info = st.columns([1, 1])
        with col_dl_btn:
            st.download_button(
                label="⬇️ Baixar em Word (.docx)",
                data=st.session_state["docx_bytes"],
                file_name="curriculo_adaptado.docx",
                mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                use_container_width=True,
            )
        with col_info:
            st.markdown("""
            <div style='background: rgba(239, 68, 68, 0.08); border: 1px solid rgba(239, 68, 68, 0.2); border-radius: 10px; padding: 16px; color: #f87171; font-size: 0.9rem;'>
                💡 <b>Dica de Ouro: Quer baixar direto em PDF?</b><br>
                Instale o <b>LibreOffice Writer</b> no seu Linux para habilitar a exportação direta em PDF com 100% de fidelidade. Execute no seu terminal:<br>
                <code style='color: #fff; background: #000; padding: 2px 6px; border-radius: 4px; display: inline-block; margin-top: 4px;'>sudo apt update && sudo apt install -y libreoffice-writer</code>
            </div>
            """, unsafe_allow_html=True)

    st.markdown("<br><h3 style='margin-bottom: 12px;'>🔍 Comparação: Original × Adaptado</h3>", unsafe_allow_html=True)
    st.caption("Confira abaixo as alterações cirúrgicas efetuadas em cada seção:")

    blocos_orig = st.session_state.get("blocos_originais", {})
    blocos_adap = st.session_state.get("blocos_adaptados", {})

    # Ordenação lógica de visualização das seções
    ordem = ["tagline", "resumo", "skills_dev", "skills_tools"]
    for i in range(10):
        ordem.append(f"exp_{i}_titulo")
        ordem.append(f"exp_{i}_bullets")
    for i in range(10):
        ordem.append(f"proj_{i}_title")
        ordem.append(f"proj_{i}_desc")

    chaves_para_mostrar = [k for k in ordem if k in blocos_adap]
    for k in blocos_adap:
        if k not in chaves_para_mostrar:
            chaves_para_mostrar.append(k)

    for chave in chaves_para_mostrar:
        renderizar_bloco(chave, blocos_orig.get(chave), blocos_adap.get(chave))

# ─────────────────────────────────────────────────────────────────────────────
# Rodapé / Créditos
# ─────────────────────────────────────────────────────────────────────────────
st.markdown("<br><hr style='border: 0; border-top: 1px solid rgba(255,255,255,0.05); margin-top: 40px; margin-bottom: 20px;'><p style='text-align: center; color: rgba(255,255,255,0.3); font-size: 0.85rem;'>Desenvolvido por <b>PietroTy 2026</b></p>", unsafe_allow_html=True)
