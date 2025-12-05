import re
import unicodedata


def _normalize(s: str) -> str:
    if s is None:
        return ""
    s = str(s).strip().lower()
    s = unicodedata.normalize("NFKD", s)
    s = "".join(ch for ch in s if not unicodedata.combining(ch))
    s = re.sub(r"[^a-z0-9\s]", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s


# Mapeamentos canônicos (chaves devem ser normalizadas via _normalize)
ORGAO_MAP = {
    # Polícia Rodoviária Federal → PRF
    _normalize("Polícia Rodoviária Federal"): "PRF",
    _normalize("Policia Rodoviaria Federal"): "PRF",
    _normalize("PRF"): "PRF",
    _normalize("Polícia Rodoviária Federal - PRF"): "PRF",
    # DETRAN variantes → DETRAN
    _normalize("DETRAN"): "DETRAN",
    _normalize("DETRAN-PI"): "DETRAN",
    _normalize("DETRAN/PI"): "DETRAN",
    _normalize("DETRAN/TI"): "DETRAN",
    # Câmara Municipal de Teresina
    _normalize("Câmara Municipal de Teresina"): "Câmara Municipal de Teresina",
    _normalize("CAMARA MUNICIPAL DE TERESINA"): "Câmara Municipal de Teresina",
    # MPPI e variações
    _normalize("MPPI"): "MPPI",
    _normalize("MP-PI"): "MPPI",
    _normalize("MPE-PI"): "MPPI",
    _normalize("MPE PI"): "MPPI",
    _normalize("MPEPI"): "MPPI",
    _normalize("Ministerio Publico do Estado do Piaui"): "MPPI",
    _normalize("Ministério Público do Estado do Piauí"): "MPPI",
    _normalize("Ministerio Publico do Piaui"): "MPPI",
    _normalize("Ministério Público do Piauí"): "MPPI",
    _normalize("SAD"): "SEAD",
}

CARGO_MAP = {
    # Exemplos podem ser adicionados conforme necessidade
}

VINCULO_MAP = {
    # Exemplos podem ser adicionados conforme necessidade
}


def canonical_orgao(value: str) -> str:
    key = _normalize(value)
    if key in ORGAO_MAP:
        return ORGAO_MAP[key]
    if "prf" in key or "policia rodoviaria federal" in key:
        return "PRF"
    return str(value).strip()


def canonical_cargo(value: str) -> str:
    key = _normalize(value)
    return CARGO_MAP.get(key, str(value).strip())


def canonical_vinculo(value: str) -> str:
    key = _normalize(value)
    return VINCULO_MAP.get(key, str(value).strip())
