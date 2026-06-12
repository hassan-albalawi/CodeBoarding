from __future__ import annotations

import os
import subprocess
import time
import urllib.request
from pathlib import Path


PROVIDER_ENV_VARS = {
    "OPENAI_API_KEY",
    "ANTHROPIC_API_KEY",
    "GOOGLE_API_KEY",
    "VERCEL_API_KEY",
    "AWS_BEARER_TOKEN_BEDROCK",
    "CEREBRAS_API_KEY",
    "DEEPSEEK_API_KEY",
    "GLM_API_KEY",
    "KIMI_API_KEY",
    "OLLAMA_BASE_URL",
    "OPENROUTER_API_KEY",
    "LITELLM_API_KEY",
}

PROVIDER_BASE_URL_ENV_VARS = {
    "OPENAI_BASE_URL",
    "VERCEL_BASE_URL",
    "DEEPSEEK_BASE_URL",
    "GLM_BASE_URL",
    "KIMI_BASE_URL",
    "OPENROUTER_BASE_URL",
    "LITELLM_BASE_URL",
}


def bootstrap_local_proxy() -> None:
    if not _enabled():
        return
    _ensure_running()
    _configure_env()


def _enabled() -> bool:
    return os.environ.get("CODEBOARDING_USE_LOCAL_PROXY", "").lower() in {"1", "true", "yes", "on"}


def _proxy_dir() -> Path | None:
    value = os.environ.get("CODEBOARDING_LOCAL_PROXY_DIR")
    return Path(value).expanduser() if value else None


def _proxy_bin() -> Path:
    value = os.environ.get("CODEBOARDING_LOCAL_PROXY_BIN")
    if value:
        return Path(value).expanduser()
    directory = _proxy_dir()
    if directory is None:
        raise RuntimeError(
            "Set CODEBOARDING_LOCAL_PROXY_DIR or CODEBOARDING_LOCAL_PROXY_BIN when local proxy is enabled"
        )
    return directory / "bin" / "cli-proxy-api"


def _proxy_config() -> Path:
    value = os.environ.get("CODEBOARDING_LOCAL_PROXY_CONFIG")
    if value:
        return Path(value).expanduser()
    directory = _proxy_dir()
    if directory is None:
        raise RuntimeError(
            "Set CODEBOARDING_LOCAL_PROXY_DIR or CODEBOARDING_LOCAL_PROXY_CONFIG when local proxy is enabled"
        )
    return directory / "config.local.yaml"


def _proxy_host() -> str:
    return os.environ.get("CODEBOARDING_LOCAL_PROXY_HOST", "127.0.0.1")


def _proxy_port() -> int:
    return int(os.environ.get("CODEBOARDING_LOCAL_PROXY_PORT", "8317"))


def _proxy_base_url() -> str:
    return os.environ.get("CODEBOARDING_LOCAL_PROXY_BASE_URL", f"http://{_proxy_host()}:{_proxy_port()}/v1")


def _proxy_api_key() -> str:
    return os.environ.get("CODEBOARDING_LOCAL_PROXY_API_KEY", "codeboarding-local-proxy-key")


def _proxy_model() -> str:
    return os.environ.get("CODEBOARDING_LOCAL_PROXY_MODEL", "gpt-5.5(medium)")


def _proxy_parsing_model() -> str:
    return os.environ.get("CODEBOARDING_LOCAL_PROXY_PARSING_MODEL", _proxy_model())


def _proxy_log() -> Path:
    value = os.environ.get("CODEBOARDING_LOCAL_PROXY_LOG")
    return Path(value).expanduser() if value else Path.home() / ".cli-proxy-api" / "runner.log"


def _health_url() -> str:
    return f"http://{_proxy_host()}:{_proxy_port()}/healthz"


def _is_healthy(timeout: float = 1.0) -> bool:
    try:
        with urllib.request.urlopen(_health_url(), timeout=timeout) as response:
            return 200 <= response.status < 300
    except Exception:
        return False


def _ensure_running() -> None:
    if _is_healthy():
        return

    proxy_bin = _proxy_bin()
    proxy_config = _proxy_config()
    if not proxy_bin.exists():
        raise RuntimeError(f"CLIProxyAPI binary not found: {proxy_bin}")
    if not proxy_config.exists():
        raise RuntimeError(f"CLIProxyAPI config not found: {proxy_config}")

    proxy_log = _proxy_log()
    proxy_log.parent.mkdir(parents=True, exist_ok=True)
    log_file = proxy_log.open("ab")
    subprocess.Popen(
        [str(proxy_bin), "-config", str(proxy_config)],
        cwd=str(proxy_bin.parent.parent),
        stdout=log_file,
        stderr=subprocess.STDOUT,
        start_new_session=True,
    )

    deadline = time.time() + 12
    while time.time() < deadline:
        if _is_healthy(timeout=0.5):
            return
        time.sleep(0.25)
    raise RuntimeError(f"CLIProxyAPI did not become healthy at {_health_url()}")


def _configure_env() -> None:
    for key in PROVIDER_ENV_VARS | PROVIDER_BASE_URL_ENV_VARS:
        os.environ.pop(key, None)
    os.environ["OPENAI_BASE_URL"] = _proxy_base_url()
    os.environ["OPENAI_API_KEY"] = _proxy_api_key()
    os.environ.setdefault("AGENT_MODEL", _proxy_model())
    os.environ.setdefault("PARSING_MODEL", _proxy_parsing_model())
