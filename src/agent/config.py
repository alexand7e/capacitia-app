import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_API_KEY or OPENAI_API_KEY == "sk-sua-chave-aqui":
    raise ValueError(
        "OPENAI_API_KEY não configurada. Edite o arquivo .env na raiz do projeto "
        "com sua chave: OPENAI_API_KEY=sk-..."
    )

OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL", "https://api.sobdemanda.mandu.piaui.pro/v1")

LLM_MODEL = "Qwen/Qwen3.6-35B-A3B"
LLM_TEMPERATURE = 0.1
EMBEDDING_MODEL = "BAAI/bge-m3"

CHROMA_DIR = Path(".data") / "chroma"
CHROMA_COLLECTION = "capacitia_servidores"

PROCESSED_DIR = Path(".data") / "processed"
