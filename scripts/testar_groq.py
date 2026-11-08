"""Valida a GROQ_API_KEY e lista os modelos disponíveis."""
import os

from dotenv import load_dotenv
from groq import Groq

load_dotenv()
client = Groq(api_key=os.environ["GROQ_API_KEY"])
for m in sorted(client.models.list().data, key=lambda m: m.id):
    print(f"{m.id:50} ctx={getattr(m, 'context_window', '?')}")
