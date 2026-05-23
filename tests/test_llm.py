"""Test dell'astrazione LLM (wiki/llm/).

Step 3 — modalità on-premise. Tutti i call LLM sono **mockati**: nessun test
contatta API esterne (Anthropic, AWS Bedrock).

Copertura:
  * ``get_llm_client`` ritorna l'istanza giusta per provider.
  * Costruzione mocked di anthropic_api e bedrock (no chiamate reali).
  * Safe-mode redact: email/CF/IBAN/telefono mascherati pre-call,
    de-mascherati post-call.
  * Mappa redact salvata su disco in ``_status/audit/redact-map.json``.
  * Placeholder progressivi e stabili: 3 email → ``<email-1>``, ``<email-2>``,
    ``<email-3>``.
"""
from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from wiki.llm import (
    AnthropicApiClient,
    BedrockClient,
    RedactMap,
    SafeModeClient,
    get_llm_client,
    redact_text,
    unredact_text,
)
from wiki.llm.safe_mode import _redact_messages


# =========================================================== fixture utili
def _mock_sdk(text: str = "ok", in_tok: int = 10, out_tok: int = 5) -> MagicMock:
    """Mock di un SDK Anthropic con ``messages.create`` configurabile."""
    sdk = MagicMock()
    sdk.messages.create.return_value = SimpleNamespace(
        content=[SimpleNamespace(text=text)],
        usage=SimpleNamespace(input_tokens=in_tok, output_tokens=out_tok),
    )
    return sdk


# ============================================================ get_llm_client
class TestGetLLMClient:
    def test_default_provider_anthropic_api(self, monkeypatch):
        """Senza config → anthropic_api di default."""
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test-xxxx")
        # Stub del modulo anthropic per evitare import reale.
        import sys
        import types as _types

        fake_anthropic = _types.SimpleNamespace(
            Anthropic=lambda api_key=None: _mock_sdk()
        )
        monkeypatch.setitem(sys.modules, "anthropic", fake_anthropic)

        client = get_llm_client({})
        assert isinstance(client, AnthropicApiClient)
        assert "fast" in client.models
        assert "smart" in client.models

    def test_provider_esplicito_anthropic_api(self, monkeypatch):
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")
        import sys
        import types as _types

        monkeypatch.setitem(
            sys.modules,
            "anthropic",
            _types.SimpleNamespace(Anthropic=lambda api_key=None: _mock_sdk()),
        )
        client = get_llm_client({"llm": {"provider": "anthropic_api"}})
        assert isinstance(client, AnthropicApiClient)

    def test_provider_bedrock(self, monkeypatch):
        """Provider bedrock con region: ritorna BedrockClient."""
        import sys
        import types as _types

        fake_anthropic = _types.SimpleNamespace(
            AnthropicBedrock=lambda aws_region: _mock_sdk()
        )
        monkeypatch.setitem(sys.modules, "anthropic", fake_anthropic)
        config = {
            "llm": {
                "provider": "bedrock",
                "bedrock": {
                    "region": "eu-west-1",
                    "model_overrides": {
                        "fast": "anthropic.claude-haiku-4-5-test",
                        "smart": "anthropic.claude-sonnet-4-5-test",
                    },
                },
            }
        }
        client = get_llm_client(config)
        assert isinstance(client, BedrockClient)
        assert client.models["fast"] == "anthropic.claude-haiku-4-5-test"

    def test_bedrock_senza_region_errore(self):
        with pytest.raises(RuntimeError, match="region"):
            get_llm_client({"llm": {"provider": "bedrock", "bedrock": {}}})

    def test_provider_sconosciuto_errore(self):
        with pytest.raises(ValueError, match="sconosciuto"):
            get_llm_client({"llm": {"provider": "ollama-on-prem"}})

    def test_redact_pii_attiva_safe_mode(self, monkeypatch, tmp_path):
        """Con `redact_pii: true` il client torna wrappato in SafeModeClient."""
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")
        import sys
        import types as _types

        monkeypatch.setitem(
            sys.modules,
            "anthropic",
            _types.SimpleNamespace(Anthropic=lambda api_key=None: _mock_sdk()),
        )
        config = {"llm": {"provider": "anthropic_api", "redact_pii": True}}
        client = get_llm_client(config, state_dir=tmp_path)
        assert isinstance(client, SafeModeClient)

    def test_redact_pii_false_no_wrapper(self, monkeypatch):
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")
        import sys
        import types as _types

        monkeypatch.setitem(
            sys.modules,
            "anthropic",
            _types.SimpleNamespace(Anthropic=lambda api_key=None: _mock_sdk()),
        )
        client = get_llm_client({"llm": {"provider": "anthropic_api"}})
        assert not isinstance(client, SafeModeClient)


# ============================================================ AnthropicApiClient
class TestAnthropicApiClient:
    def test_complete_passa_through(self):
        sdk = _mock_sdk(text="risposta ok", in_tok=42, out_tok=8)
        client = AnthropicApiClient(sdk_client=sdk)
        text, usage = client.complete(
            messages=[{"role": "user", "content": "ciao"}],
            model="fast",
        )
        assert text == "risposta ok"
        assert usage == {"input_tokens": 42, "output_tokens": 8}
        # Modello risolto da alias.
        kwargs = sdk.messages.create.call_args.kwargs
        assert kwargs["model"] == "claude-haiku-4-5"
        assert kwargs["max_tokens"] == 1024
        assert kwargs["messages"] == [{"role": "user", "content": "ciao"}]

    def test_complete_passa_system(self):
        sdk = _mock_sdk()
        client = AnthropicApiClient(sdk_client=sdk)
        client.complete(
            messages=[{"role": "user", "content": "x"}],
            model="smart",
            system="sei un assistente",
        )
        kwargs = sdk.messages.create.call_args.kwargs
        assert kwargs["system"] == "sei un assistente"
        assert kwargs["model"] == "claude-sonnet-4-5"

    def test_model_id_diretto_non_alias(self):
        """Se passi un model id non-alias, viene usato tale e quale."""
        sdk = _mock_sdk()
        client = AnthropicApiClient(sdk_client=sdk)
        client.complete(
            messages=[{"role": "user", "content": "x"}],
            model="claude-custom-9000",
        )
        assert sdk.messages.create.call_args.kwargs["model"] == "claude-custom-9000"

    def test_model_overrides(self):
        sdk = _mock_sdk()
        client = AnthropicApiClient(
            sdk_client=sdk,
            model_overrides={"fast": "claude-haiku-custom"},
        )
        client.complete(messages=[{"role": "user", "content": "x"}], model="fast")
        assert sdk.messages.create.call_args.kwargs["model"] == "claude-haiku-custom"

    def test_messages_namespace_compat(self):
        """Backward-compat: client.messages.create funziona come SDK Anthropic."""
        sdk = _mock_sdk(text='[{"sha":"x","cat":"VIVO","conf":0.9,"why":""}]')
        client = AnthropicApiClient(sdk_client=sdk)
        response = client.messages.create(
            model="claude-haiku-4-5",
            max_tokens=512,
            system="sys",
            messages=[{"role": "user", "content": "hello"}],
        )
        assert response.content[0].text.startswith("[")
        assert response.usage.input_tokens == 10

    def test_api_key_mancante_errore(self, monkeypatch):
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        import sys
        import types as _types

        # Stub anthropic per evitare import error mascherato.
        monkeypatch.setitem(
            sys.modules,
            "anthropic",
            _types.SimpleNamespace(Anthropic=lambda api_key=None: _mock_sdk()),
        )
        with pytest.raises(RuntimeError, match="ANTHROPIC_API_KEY"):
            AnthropicApiClient()


# ============================================================ BedrockClient
class TestBedrockClient:
    def test_complete_passa_through(self):
        sdk = _mock_sdk(text="bedrock ok", in_tok=50, out_tok=20)
        client = BedrockClient(region="eu-west-1", sdk_client=sdk)
        text, usage = client.complete(
            messages=[{"role": "user", "content": "x"}],
            model="fast",
        )
        assert text == "bedrock ok"
        assert usage == {"input_tokens": 50, "output_tokens": 20}
        # Default model id è il prefissato anthropic.
        called_model = sdk.messages.create.call_args.kwargs["model"]
        assert called_model.startswith("anthropic.claude-haiku")

    def test_model_overrides_bedrock(self):
        sdk = _mock_sdk()
        client = BedrockClient(
            region="eu-west-1",
            sdk_client=sdk,
            model_overrides={
                "fast": "anthropic.claude-haiku-4-5-20251001-v1:0",
                "smart": "anthropic.claude-sonnet-4-5-20251022-v2:0",
            },
        )
        client.complete(messages=[{"role": "user", "content": "x"}], model="smart")
        assert (
            sdk.messages.create.call_args.kwargs["model"]
            == "anthropic.claude-sonnet-4-5-20251022-v2:0"
        )

    def test_messages_namespace_compat_bedrock(self):
        sdk = _mock_sdk(text="risposta")
        client = BedrockClient(region="us-east-1", sdk_client=sdk)
        response = client.messages.create(
            model=client.models["fast"],
            max_tokens=128,
            messages=[{"role": "user", "content": "ping"}],
        )
        assert response.content[0].text == "risposta"


# ============================================================ safe_mode redact
class TestRedactPatterns:
    def test_email_singola(self):
        m = RedactMap(state_dir=None)
        out = redact_text("scrivimi a m.rossi@bianchi.it grazie", m)
        assert "m.rossi@bianchi.it" not in out
        assert "<email-1>" in out

    def test_3_email_progressive(self):
        """3 email distinte → <email-1>, <email-2>, <email-3>."""
        m = RedactMap(state_dir=None)
        text = "contatti: a@x.it, b@y.it, c@z.it — risposte a a@x.it"
        out = redact_text(text, m)
        # a@x.it appare 2 volte, ma deve avere lo stesso placeholder.
        assert out.count("<email-1>") == 2
        assert "<email-2>" in out
        assert "<email-3>" in out
        # Le 3 email reali sono sparite.
        for email in ("a@x.it", "b@y.it", "c@z.it"):
            assert email not in out

    def test_codice_fiscale(self):
        m = RedactMap(state_dir=None)
        out = redact_text("CF: RSSMRA80A01H501U valido", m)
        assert "RSSMRA80A01H501U" not in out
        assert "<cf-1>" in out

    def test_iban(self):
        m = RedactMap(state_dir=None)
        out = redact_text("Bonifico su IT60X0542811101000000123456", m)
        assert "IT60X0542811101000000123456" not in out
        assert "<iban-1>" in out

    def test_iban_con_spazi(self):
        m = RedactMap(state_dir=None)
        out = redact_text("IT60 X054 2811 1010 0000 0123 456", m)
        assert "<iban-1>" in out

    def test_telefono_italiano(self):
        m = RedactMap(state_dir=None)
        out = redact_text("Telefono +39 02 12345678 fisso", m)
        assert "02 12345678" not in out
        assert "<phone-1>" in out

    def test_mix_pii(self):
        m = RedactMap(state_dir=None)
        text = (
            "Mario Rossi (mario@rossi.it, CF RSSMRA80A01H501U) "
            "tel +39 02 12345678 IBAN IT60X0542811101000000123456"
        )
        out = redact_text(text, m)
        for original in (
            "mario@rossi.it",
            "RSSMRA80A01H501U",
            "IT60X0542811101000000123456",
        ):
            assert original not in out
        assert "<email-1>" in out
        assert "<cf-1>" in out
        assert "<iban-1>" in out

    def test_unredact_inversa(self):
        m = RedactMap(state_dir=None)
        original = "mail a giovanna@x.it cf RSSMRA80A01H501U"
        redacted = redact_text(original, m)
        # Il modello risponde citando i placeholder.
        model_answer = f"Ho ricevuto: {redacted}. Confermo."
        result = unredact_text(model_answer, m)
        assert "giovanna@x.it" in result
        assert "RSSMRA80A01H501U" in result

    def test_placeholder_stabili_tra_chiamate(self, tmp_path):
        """Stessa email tra due RedactMap caricate dallo stesso file → stesso placeholder."""
        # Prima istanza scrive la mappa.
        audit_dir = tmp_path / "audit"
        audit_dir.mkdir()
        m1 = RedactMap(state_dir=tmp_path)
        redact_text("contatto a@x.it", m1)
        m1.save()
        # Seconda istanza la rilegge e re-applica.
        m2 = RedactMap(state_dir=tmp_path)
        out = redact_text("ancora a@x.it", m2)
        assert "<email-1>" in out
        # Nessun <email-2> generato (la mappa è stata riusata).
        assert "<email-2>" not in out


class TestRedactMapPersistence:
    def test_redact_map_salvata_in_audit(self, tmp_path):
        """La mappa viene scritta in `_status/audit/redact-map.json`."""
        sdk = _mock_sdk(text="ok")
        inner = AnthropicApiClient(sdk_client=sdk)
        client = SafeModeClient(inner, state_dir=tmp_path)
        client.complete(
            messages=[{"role": "user", "content": "mail a a@x.it"}],
            model="fast",
        )
        map_path = tmp_path / "audit" / "redact-map.json"
        assert map_path.exists()
        data = json.loads(map_path.read_text())
        assert "a@x.it" in data["forward"]
        assert data["forward"]["a@x.it"] == "<email-1>"
        assert data["counters"]["email"] == 1

    def test_state_dir_none_no_persist(self):
        """Senza state_dir, la mappa vive solo in memoria (no crash)."""
        m = RedactMap(state_dir=None)
        redact_text("mail a@x.it", m)
        m.save()  # no-op atteso, niente eccezione.

    def test_redact_messages_lista_blocchi(self):
        """_redact_messages tollera content sia stringa che lista di blocchi."""
        m = RedactMap(state_dir=None)
        msgs = [
            {"role": "user", "content": "email a@x.it"},
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": "altra email b@y.it"},
                    {"type": "image", "source": {"data": "binario"}},
                ],
            },
        ]
        out = _redact_messages(msgs, m)
        assert "a@x.it" not in out[0]["content"]
        assert "<email-1>" in out[0]["content"]
        # Blocco image non toccato.
        assert out[1]["content"][1]["type"] == "image"
        # Blocco text dentro lista redacted.
        assert "b@y.it" not in out[1]["content"][0]["text"]


# ============================================================ SafeModeClient e2e
class TestSafeModeClientE2E:
    def test_pre_call_redact_post_call_unredact(self):
        """Il modello non vede mai la PII reale; la risposta torna ri-espansa."""
        sdk = MagicMock()
        # Simula un modello che cita il placeholder nella risposta.
        sdk.messages.create.return_value = SimpleNamespace(
            content=[
                SimpleNamespace(
                    text="Confermo: ho ricevuto il messaggio per <email-1>."
                )
            ],
            usage=SimpleNamespace(input_tokens=20, output_tokens=10),
        )
        inner = AnthropicApiClient(sdk_client=sdk)
        client = SafeModeClient(inner, state_dir=None)

        text, _ = client.complete(
            messages=[{"role": "user", "content": "rispondi a mario@rossi.it"}],
            model="fast",
        )

        # 1. Il modello ha visto il placeholder, non la PII reale.
        sent = sdk.messages.create.call_args.kwargs["messages"][0]["content"]
        assert "mario@rossi.it" not in sent
        assert "<email-1>" in sent

        # 2. La risposta torna con la PII ri-espansa.
        assert "mario@rossi.it" in text
        assert "<email-1>" not in text

    def test_system_prompt_redacted(self):
        sdk = _mock_sdk(text="ok")
        inner = AnthropicApiClient(sdk_client=sdk)
        client = SafeModeClient(inner, state_dir=None)
        client.complete(
            messages=[{"role": "user", "content": "x"}],
            model="fast",
            system="contatta a@x.it se serve",
        )
        sent_system = sdk.messages.create.call_args.kwargs["system"]
        assert "a@x.it" not in sent_system
        assert "<email-1>" in sent_system

    def test_models_eredita_da_inner(self):
        sdk = _mock_sdk()
        inner = AnthropicApiClient(
            sdk_client=sdk, model_overrides={"fast": "modello-custom"}
        )
        client = SafeModeClient(inner, state_dir=None)
        assert client.models["fast"] == "modello-custom"

    def test_safe_mode_messages_compat(self):
        """SafeModeClient esporrà anche .messages.create per i caller legacy."""
        sdk = _mock_sdk(
            text='[{"sha":"x","cat":"VIVO","conf":0.9,"why":"mail a a@x.it"}]'
        )
        inner = AnthropicApiClient(sdk_client=sdk)
        client = SafeModeClient(inner, state_dir=None)
        response = client.messages.create(
            model="claude-haiku-4-5",
            max_tokens=256,
            messages=[{"role": "user", "content": "ciao a@x.it"}],
        )
        # Sent al modello: redacted.
        sent = sdk.messages.create.call_args.kwargs["messages"][0]["content"]
        assert "a@x.it" not in sent
        # Risposta: re-espansa (il modello aveva ricitato <email-1>... ma qui
        # non lo cita; verifichiamo solo che il flusso messages funzioni).
        assert response.content[0].text.startswith("[")
        assert response.usage.input_tokens > 0


# =============================================== integrazione con caller legacy
class TestIntegrazioneCallerLegacy:
    """Verifica che `categorizers.claude.categorize_batch` accetti un
    client costruito via wiki.llm (interfaccia messages.create rispettata)."""

    def test_categorize_batch_accetta_llm_client(self, tmp_path):
        from datetime import datetime, timedelta, timezone

        from categorizers import claude as claude_mod
        from scanners._base import FileRecord

        record = FileRecord(
            source="nas",
            source_id="nas://x.pdf",
            path="generica/x.pdf",
            name="x.pdf",
            size=1000,
            mtime=datetime.now(timezone.utc) - timedelta(days=10),
            mime="application/pdf",
            extras={},
            sha256="aa" + "0" * 62,
        )
        sdk = _mock_sdk(
            text=json.dumps(
                [{"sha": record.sha256, "cat": "VIVO", "conf": 0.8, "why": "test"}]
            ),
            in_tok=100,
            out_tok=20,
        )
        client = AnthropicApiClient(sdk_client=sdk)

        out = claude_mod.categorize_batch(
            [record],
            mode="safe",
            state_dir=tmp_path,
            client=client,
        )
        assert len(out) == 1
        assert out[0]["cat"] == "vivo"
