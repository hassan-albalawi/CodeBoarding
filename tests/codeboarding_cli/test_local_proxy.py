import os

from codeboarding_cli import local_proxy


def test_local_proxy_disabled_by_default(monkeypatch):
    calls = []
    monkeypatch.delenv("CODEBOARDING_USE_LOCAL_PROXY", raising=False)
    monkeypatch.setattr(local_proxy, "_ensure_running", lambda: calls.append("running"))

    local_proxy.bootstrap_local_proxy()

    assert calls == []


def test_local_proxy_configures_openai_compatible_endpoint(monkeypatch):
    monkeypatch.setenv("CODEBOARDING_USE_LOCAL_PROXY", "1")
    monkeypatch.setenv("CODEBOARDING_LOCAL_PROXY_BASE_URL", "http://127.0.0.1:8317/v1")
    monkeypatch.setenv("CODEBOARDING_LOCAL_PROXY_API_KEY", "local-key")
    monkeypatch.setenv("CODEBOARDING_LOCAL_PROXY_MODEL", "gpt-5.5(medium)")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant")
    monkeypatch.setenv("LITELLM_BASE_URL", "http://localhost:4000")
    monkeypatch.setattr(local_proxy, "_is_healthy", lambda timeout=1.0: True)

    local_proxy.bootstrap_local_proxy()

    assert os.environ["OPENAI_BASE_URL"] == "http://127.0.0.1:8317/v1"
    assert os.environ["OPENAI_API_KEY"] == "local-key"
    assert os.environ["AGENT_MODEL"] == "gpt-5.5(medium)"
    assert "ANTHROPIC_API_KEY" not in os.environ
    assert "LITELLM_BASE_URL" not in os.environ


def test_local_proxy_requires_binary_or_directory_when_starting(monkeypatch):
    monkeypatch.setenv("CODEBOARDING_USE_LOCAL_PROXY", "1")
    monkeypatch.delenv("CODEBOARDING_LOCAL_PROXY_DIR", raising=False)
    monkeypatch.delenv("CODEBOARDING_LOCAL_PROXY_BIN", raising=False)
    monkeypatch.setattr(local_proxy, "_is_healthy", lambda timeout=1.0: False)

    try:
        local_proxy.bootstrap_local_proxy()
    except RuntimeError as exc:
        assert "CODEBOARDING_LOCAL_PROXY_DIR" in str(exc)
    else:
        raise AssertionError("Expected RuntimeError")
