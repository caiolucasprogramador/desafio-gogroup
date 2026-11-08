"""Limite de requisições em memória: protege as cotas gratuitas dos LLMs.

Duas travas: por IP (janela deslizante de 1 minuto) e global por dia.
Em memória porque o deploy é um processo só; reiniciar zera os contadores.
"""
import time
from collections import defaultdict, deque
from threading import Lock


class Limitador:
    def __init__(self, por_minuto: int = 6, por_dia: int = 300):
        self.por_minuto, self.por_dia = por_minuto, por_dia
        self._ips: dict[str, deque] = defaultdict(deque)
        self._dia, self._hoje = "", 0
        self._lock = Lock()

    def permitir(self, ip: str) -> str | None:
        """None se pode seguir; senão, o motivo da recusa."""
        agora = time.time()
        with self._lock:
            dia = time.strftime("%Y-%m-%d")
            if dia != self._dia:
                self._dia, self._hoje = dia, 0
            if self._hoje >= self.por_dia:
                return "limite diário da demonstração atingido; tente amanhã"
            janela = self._ips[ip]
            while janela and agora - janela[0] > 60:
                janela.popleft()
            if len(janela) >= self.por_minuto:
                return f"muitas requisições; aguarde {int(60 - (agora - janela[0])) + 1}s"
            janela.append(agora)
            self._hoje += 1
            return None
