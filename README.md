# CV Adapter

Adapta seu currículo `.docx` para vagas específicas usando Claude AI.  
**Formatação 100% preservada** — só os textos mudam.

## Como funciona

1. Sobe seu currículo `.docx` padrão (ou usa o template embutido)
2. Cola a descrição da vaga
3. Claude analisa, adapta e devolve o `.docx` pronto para baixar

## Instalação

```bash
pip install -r requirements.txt
streamlit run app.py
```

## API Key

Coloque sua chave na sidebar, ou crie `.streamlit/secrets.toml`:

```toml
ANTHROPIC_API_KEY = "sk-ant-..."
```

## Estrutura

```
curriculo-adapter/
├── app.py                  # Interface Streamlit
├── modules/
│   └── xml_adapter.py      # Lógica de adaptação XML
├── CurrículoVbra.docx      # Template padrão embutido
└── requirements.txt
```
