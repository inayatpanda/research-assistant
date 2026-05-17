from pathlib import Path

from research_api.settings import Settings


def test_settings_load_defaults(monkeypatch, tmp_path):
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    monkeypatch.setenv("SQLITE_URL", f"sqlite+aiosqlite:///{tmp_path}/test.db")
    s = Settings(_env_file=None)
    assert s.gemini_api_key == "test-key"
    assert s.data_dir == Path(str(tmp_path))
    assert s.ai_provider_default == "gemini"
    assert s.storage_backend == "local"
    assert s.local_user_id == "local-user"


def test_settings_missing_key_falls_back(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    s = Settings(_env_file=None)
    assert s.gemini_api_key is None
