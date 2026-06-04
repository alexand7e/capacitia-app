import pandas as pd
import chromadb
from langchain_openai import OpenAIEmbeddings
from langchain_chroma import Chroma
from langchain.schema import Document
from pathlib import Path

from .config import CHROMA_DIR, CHROMA_COLLECTION, EMBEDDING_MODEL, PROCESSED_DIR, OPENAI_BASE_URL


def _load_and_chunk() -> list[Document]:
    docs = []

    dados = pd.read_parquet(PROCESSED_DIR / "dados.parquet")
    secretarias = pd.read_parquet(PROCESSED_DIR / "secretarias.parquet")
    visao = pd.read_parquet(PROCESSED_DIR / "visao_aberta.parquet")
    cargos = pd.read_parquet(PROCESSED_DIR / "cargos.parquet")

    # — chunks por evento/ano
    for (ano, evento), grp in dados.groupby(["ano", "evento"]):
        inscritos = len(grp)
        certificados = (grp["certificado"] == "Sim").sum()
        taxa = round(certificados / inscritos * 100, 1) if inscritos else 0
        orgaos = grp["orgao"].dropna().unique().tolist()
        formatos = grp["formato"].dropna().unique().tolist()
        txt = (
            f"Evento '{evento}' ({ano}): {inscritos} inscritos, "
            f"{certificados} certificados (taxa {taxa}%). "
            f"Órgãos: {', '.join(orgaos)}. Formato: {', '.join(formatos)}."
        )
        docs.append(Document(page_content=txt, metadata={"ano": ano, "evento": evento, "tipo": "evento"}))

    # — chunks por órgão/ano
    for (ano, orgao), grp in dados.groupby(["ano", "orgao"]):
        inscritos = len(grp)
        certificados = (grp["certificado"] == "Sim").sum()
        taxa = round(certificados / inscritos * 100, 1) if inscritos else 0
        txt = (
            f"Órgão {orgao} ({ano}): {inscritos} servidores inscritos, "
            f"{certificados} certificados (taxa {taxa}%)."
        )
        docs.append(Document(page_content=txt, metadata={"ano": ano, "orgao": orgao, "tipo": "orgao"}))

    # — secretarias
    if not secretarias.empty:
        for _, row in secretarias.iterrows():
            sec = row.get("secretaria_orgao", row.get("SECRETARIA/ÓRGÃO", ""))
            n_ins = row.get("n_inscritos", row.get("Nº INSCRITOS", 0))
            n_cert = row.get("n_certificados", row.get("Nº CERTIFICADOS", 0))
            txt = f"Secretaria/Órgão {sec}: {n_ins} inscritos, {n_cert} certificados."
            docs.append(Document(page_content=txt, metadata={"orgao": sec, "tipo": "secretaria"}))

    # — visão geral
    if not visao.empty:
        for _, row in visao.iterrows():
            txt = f"{row.get('evento', '')}: {row.to_dict()}"
            docs.append(Document(page_content=str(txt), metadata={"tipo": "visao_geral"}))

    # — cargos
    if not cargos.empty:
        for _, row in cargos.iterrows():
            cargo = row.get("cargo", "")
            if pd.notna(cargo):
                txt = f"Cargo {cargo}: {row.to_dict()}"
                docs.append(Document(page_content=str(txt), metadata={"cargo": cargo, "tipo": "cargo"}))

    return docs


def get_vector_store() -> Chroma:
    embeddings = OpenAIEmbeddings(model=EMBEDDING_MODEL, base_url=OPENAI_BASE_URL)
    CHROMA_DIR.mkdir(parents=True, exist_ok=True)

    if list(CHROMA_DIR.iterdir()):
        return Chroma(
            collection_name=CHROMA_COLLECTION,
            embedding_function=embeddings,
            persist_directory=str(CHROMA_DIR),
        )

    docs = _load_and_chunk()
    print(f"[vector_store] Gerando {len(docs)} chunks no ChromaDB...")
    store = Chroma.from_documents(
        documents=docs,
        embedding=embeddings,
        collection_name=CHROMA_COLLECTION,
        persist_directory=str(CHROMA_DIR),
    )
    store.persist()
    print("[vector_store] ChromaDB persistido.")
    return store
