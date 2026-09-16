# =========================================================
# config/api_keys.py
# 所有 API Key 统一在此管理，禁止在各 Straw 文件内硬编码
# =========================================================

import os


def _read_secret(name: str) -> str:
    """Read a secret from the environment or Streamlit Cloud secrets."""
    value = os.environ.get(name, "").strip()
    if value:
        return value

    try:
        import streamlit as st

        return str(st.secrets.get(name, "")).strip()
    except Exception:
        return ""


FMP_API_KEY  = _read_secret("FMP_API_KEY")
FMP_BASE     = "https://financialmodelingprep.com/stable"

FRED_API_KEY = _read_secret("FRED_API_KEY")
FRED_BASE    = "https://api.stlouisfed.org/fred/series/observations"

EIA_API_KEY  = _read_secret("EIA_API_KEY")
EIA_BASE     = "https://api.eia.gov/v2"
