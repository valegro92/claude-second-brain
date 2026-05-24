"""Interfaccia astratta per i provider LLM del wiki-toolkit.

Step 3 — modalità on-premise. Il toolkit deve poter usare Claude attraverso:

* ``anthropic_api``: API standard di Anthropic (default, identico a Step 2);
* ``bedrock``: Claude ospitato su AWS Bedrock dell'account cliente, per
  clienti che richiedono la non-uscita del dato dal proprio perimetro AWS;
* qualsiasi futuro provider wrappato dietro questa stessa interfaccia.

I caller (categorizers/claude.py, reconcilers/schede.py) NON istanziano più
``anthropic.Anthropic`` direttamente: ricevono un ``LLMClient`` da
:func:`wiki.llm.get_llm_client` e chiamano ``client.complete(...)``.

Convenzioni:

* :meth:`LLMClient.complete` accetta una lista di messaggi user/assistant
  (formato OpenAI-like) e un parametro ``system`` opzionale (kwarg). Ritorna
  ``(text, usage)`` dove ``usage`` è ``{"input_tokens": int, "output_tokens": int}``.
* :attr:`LLMClient.models` è un dict di alias logici → model id specifici
  del provider. Le chiavi standard sono ``"fast"`` (Haiku-class) e
  ``"smart"`` (Sonnet-class). I caller passano l'alias o il model id reale:
  l'implementazione risolve.
* :meth:`LLMClient.vision` è opzionale (per OCR Step 3+). Default: solleva
  ``NotImplementedError``.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any


class LLMClient(ABC):
    """Contratto comune di tutti i provider LLM usati dal toolkit."""

    #: Mapping alias logico → model id specifico del provider.
    #: Almeno ``"fast"`` e ``"smart"`` devono essere definiti.
    models: dict[str, str] = {}

    @abstractmethod
    def complete(
        self,
        messages: list[dict[str, Any]],
        model: str | None = None,
        max_tokens: int = 1024,
        **kwargs: Any,
    ) -> tuple[str, dict[str, int]]:
        """Esegue una chiamata di completion testuale.

        Args:
            messages: lista di messaggi nel formato
                ``[{"role": "user"|"assistant", "content": "..."}]``.
            model: alias (``"fast"``, ``"smart"``) o model id specifico.
                Se ``None``, usa ``self.models["fast"]``.
            max_tokens: limite di token in output.
            **kwargs: passati al backend (es. ``system`` per Anthropic).

        Returns:
            Tupla ``(text, usage)``:
              * ``text``: stringa di risposta del modello;
              * ``usage``: ``{"input_tokens": N, "output_tokens": N}``.

        Raises:
            RuntimeError: se il provider non è configurato correttamente
                (credenziali mancanti, SDK non installato, ecc.).
        """
        raise NotImplementedError

    def vision(
        self,
        image_path: Path,
        prompt: str,
        model: str | None = None,
        **kwargs: Any,
    ) -> tuple[str, dict[str, int]]:
        """Esegue una chiamata vision su un'immagine.

        Default: non implementato. I provider che supportano vision (es.
        Claude su API standard, Claude su Bedrock con il modello giusto)
        sovrascrivono questo metodo.

        Args:
            image_path: path al file immagine (PNG/JPEG).
            prompt: prompt testuale che accompagna l'immagine.
            model: alias o model id specifico.
            **kwargs: passati al backend.

        Returns:
            ``(text, usage)`` come :meth:`complete`.

        Raises:
            NotImplementedError: se il provider non supporta vision.
        """
        raise NotImplementedError(
            f"Il provider {self.__class__.__name__} non supporta chiamate vision"
        )

    def resolve_model(self, model: str | None) -> str:
        """Risolve un alias (``"fast"``, ``"smart"``) in model id reale.

        Se ``model`` è ``None`` ritorna l'alias ``"fast"``.
        Se ``model`` non è un alias noto, lo ritorna invariato (assumendo
        che il caller abbia passato un model id specifico del provider).
        """
        if model is None:
            return self.models.get("fast", "")
        if model in self.models:
            return self.models[model]
        return model


# Interfaccia "messages.create" simil-Anthropic mantenuta per compatibilità
# coi caller esistenti (categorizers/claude.py, reconcilers/schede.py)
# che fanno ``client.messages.create(model=..., max_tokens=..., system=...,
# messages=[...])``. Il client esposto da get_llm_client() deve presentare
# questa shape; le implementazioni concrete la realizzano via wrapper.


class _MessagesNamespace:
    """Wrapper che espone ``.messages.create(...)`` sopra :class:`LLMClient`.

    Mantiene la backward compatibility con i caller che chiamano
    ``client.messages.create(...)`` come se fosse l'SDK Anthropic. La firma
    accettata è la stessa: ``model``, ``max_tokens``, ``system``,
    ``messages``. Ritorna un oggetto con attributi ``content`` (lista di
    blocchi con ``.text``) e ``usage`` (con ``.input_tokens`` e
    ``.output_tokens``), compatibile con
    :func:`categorizers.claude._extract_text` e ``_extract_usage``.
    """

    def __init__(self, llm: LLMClient) -> None:
        self._llm = llm

    def create(
        self,
        *,
        model: str,
        max_tokens: int = 1024,
        messages: list[dict[str, Any]],
        system: str | None = None,
        **kwargs: Any,
    ) -> Any:
        """Adapter verso :meth:`LLMClient.complete`."""
        extra: dict[str, Any] = dict(kwargs)
        if system is not None:
            extra["system"] = system
        text, usage = self._llm.complete(
            messages=messages,
            model=model,
            max_tokens=max_tokens,
            **extra,
        )
        return _LLMResponse(text=text, usage=usage)


class _LLMResponse:
    """Shape compatibile con la response dell'SDK Anthropic.

    Espone:

    * ``response.content[0].text`` → stringa;
    * ``response.usage.input_tokens`` / ``response.usage.output_tokens``.
    """

    def __init__(self, text: str, usage: dict[str, int]) -> None:
        self.content = [_TextBlock(text=text)]
        self.usage = _Usage(
            input_tokens=int(usage.get("input_tokens", 0)),
            output_tokens=int(usage.get("output_tokens", 0)),
        )


class _TextBlock:
    def __init__(self, text: str) -> None:
        self.text = text


class _Usage:
    def __init__(self, input_tokens: int, output_tokens: int) -> None:
        self.input_tokens = input_tokens
        self.output_tokens = output_tokens


class AnthropicCompatibleMixin:
    """Mixin che aggiunge il namespace ``.messages`` ai client concreti.

    Va combinato con :class:`LLMClient`. Esempio:

    .. code-block:: python

        class AnthropicApiClient(AnthropicCompatibleMixin, LLMClient):
            ...
    """

    @property
    def messages(self) -> _MessagesNamespace:
        # Costruito on-demand: niente stato condiviso, niente init manuale.
        return _MessagesNamespace(self)  # type: ignore[arg-type]


__all__ = [
    "AnthropicCompatibleMixin",
    "LLMClient",
    "_LLMResponse",
    "_MessagesNamespace",
]
