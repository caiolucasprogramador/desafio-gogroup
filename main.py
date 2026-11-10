"""Ponto de entrada da Vercel (ela procura `app` em main.py na raiz).

Localmente: uvicorn main:app --reload
"""
from atendimento.api.app import app  # noqa: F401
