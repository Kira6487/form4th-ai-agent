from app.core.config import Settings


def test_settings_defaults_and_origin_parsing() -> None:
    settings = Settings(_env_file=None, allowed_origins="http://localhost:3000, https://admin.example.com")

    assert settings.app_name == "form4th-ai-agent"
    assert settings.gemini_model == "gemini-3.7-flash"
    assert settings.cors_origins == ["http://localhost:3000", "https://admin.example.com"]


def test_settings_do_not_require_optional_services() -> None:
    settings = Settings(_env_file=None)

    assert settings.database_url is None
    assert settings.gemini_api_key is None
