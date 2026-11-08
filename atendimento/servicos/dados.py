"""Acesso aos CSVs do case (carregados uma vez, em memória)."""
from functools import lru_cache
from pathlib import Path

import pandas as pd

PASTA = Path(__file__).resolve().parents[2] / "case_atendimento"


@lru_cache
def pedidos() -> pd.DataFrame:
    return pd.read_csv(PASTA / "pedidos.csv", parse_dates=["data_pedido"]).set_index("order_id")


@lru_cache
def conversas() -> pd.DataFrame:
    return pd.read_csv(PASTA / "conversas.csv", parse_dates=["data_abertura"])


@lru_cache
def mensagens() -> pd.DataFrame:
    return pd.read_csv(PASTA / "mensagens.csv", parse_dates=["timestamp"]).sort_values("timestamp")


def entrada_do_grafo(conversation_id: str) -> dict:
    """Estado inicial do grafo para uma conversa do histórico."""
    c = conversas().set_index("conversation_id").loc[conversation_id]
    msgs = mensagens()
    return {
        "conversation_id": conversation_id, "customer_id": c.customer_id, "order_id": c.order_id,
        "canal": c.canal, "marca": c.marca, "data_abertura": str(c.data_abertura), "status_conversa": c.status,
        "mensagens_cliente": msgs[(msgs.conversation_id == conversation_id) & (msgs.autor == "cliente")].texto.tolist(),
        "trilha": [],
    }
