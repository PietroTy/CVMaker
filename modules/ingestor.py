"""
modules/ingestor.py — Ingestão de Documentos (PDF, DOCX, TXT)
"""

import hashlib
import io
from typing import Optional

try:
    import PyPDF2
    _HAS_PYPDF2 = True
except ImportError:
    _HAS_PYPDF2 = False

try:
    import docx as python_docx
    _HAS_DOCX = True
except ImportError:
    _HAS_DOCX = False


class IngestorResult:
    def __init__(self, texto: str, hash_conteudo: str, nome_arquivo: str):
        self.texto         = texto
        self.hash_conteudo = hash_conteudo
        self.nome_arquivo  = nome_arquivo
        self.total_chars   = len(texto)


def _extrair_pdf(file_bytes: bytes) -> str:
    if not _HAS_PYPDF2:
        raise ImportError("PyPDF2 não instalado. Execute: pip install PyPDF2")
    texto = ""
    leitor = PyPDF2.PdfReader(io.BytesIO(file_bytes))
    for i, pagina in enumerate(leitor.pages):
        t = pagina.extract_text()
        if t:
            texto += f"\n[PÁGINA {i+1}]\n{t}\n"
    return texto.strip()


def _extrair_docx(file_bytes: bytes) -> str:
    if not _HAS_DOCX:
        raise ImportError("python-docx não instalado. Execute: pip install python-docx")
    doc = python_docx.Document(io.BytesIO(file_bytes))
    return "\n".join([p.text for p in doc.paragraphs if p.text.strip()])


def _extrair_txt(file_bytes: bytes) -> str:
    return file_bytes.decode("utf-8", errors="ignore").strip()


def ingest_document(file_bytes: bytes, nome_arquivo: str) -> IngestorResult:
    ext = nome_arquivo.lower().rsplit(".", 1)[-1]

    if ext == "pdf":
        texto = _extrair_pdf(file_bytes)
    elif ext == "docx":
        texto = _extrair_docx(file_bytes)
    elif ext == "txt":
        texto = _extrair_txt(file_bytes)
    else:
        raise ValueError(f"Formato não suportado: .{ext}")

    hash_conteudo = hashlib.sha256(file_bytes).hexdigest()
    return IngestorResult(texto=texto, hash_conteudo=hash_conteudo, nome_arquivo=nome_arquivo)
