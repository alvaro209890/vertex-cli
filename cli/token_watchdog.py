"""Token watchdog: mantém o Firebase JWT atualizado em background.

Rodando como daemon thread, chama get_valid_token() periodicamente
para garantir que o proxy local sempre tenha um token fresco para
as requisições de forwarding ao servidor remoto.
"""

from __future__ import annotations

import threading
import time
from dataclasses import dataclass, field

from loguru import logger

from vertex_auth import get_valid_token

_REFRESH_INTERVAL_SECONDS = 1800  # 30 minutos (bem antes dos 60 min de expiração)


@dataclass
class TokenWatchdog:
    """Daemon thread que refresca o token Firebase periodicamente.

    Attributes:
        refresh_interval: Intervalo entre refreshes em segundos (padrão 1800).
    """

    refresh_interval: float = _REFRESH_INTERVAL_SECONDS

    _stop_event: threading.Event = field(default_factory=threading.Event)
    _thread: threading.Thread | None = None
    _token: str | None = None
    _lock: threading.Lock = field(default_factory=threading.Lock)

    def start(self) -> None:
        """Inicia a thread de watchdog em background."""
        if self._thread is not None and self._thread.is_alive():
            logger.debug("TokenWatchdog já está rodando.")
            return
        self._stop_event.clear()
        self._thread = threading.Thread(
            target=self._run,
            name="token-watchdog",
            daemon=True,
        )
        self._thread.start()
        logger.info(
            "TokenWatchdog iniciado (refresh a cada {}s)", self.refresh_interval
        )

    def stop(self) -> None:
        """Para a thread de watchdog."""
        self._stop_event.set()
        logger.info("TokenWatchdog parado.")

    @property
    def token(self) -> str | None:
        """Retorna o token atual (thread-safe)."""
        with self._lock:
            return self._token

    def refresh_now(self) -> str | None:
        """Força refresh do token e retorna o novo valor.

        Returns:
            O novo token JWT, ou None se o refresh falhar.
        """
        fresh = get_valid_token()
        with self._lock:
            old = self._token
            self._token = fresh
        if fresh:
            if fresh != old:
                logger.info("Token Firebase renovado com sucesso.")
            else:
                logger.debug("Token ainda válido, nenhuma renovação necessária.")
        else:
            logger.warning("Falha ao renovar token Firebase.")
        return fresh

    def _run(self) -> None:
        """Loop principal: refresca o token em intervalos regulares."""
        # Faz refresh imediato ao iniciar
        self.refresh_now()

        while not self._stop_event.is_set():
            # Espera o intervalo ou até ser parado
            if self._stop_event.wait(self.refresh_interval):
                break
            self.refresh_now()
