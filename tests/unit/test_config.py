"""US5: required configuration is checked before anything else (FR-031)."""

import pytest

from claim_intake.config import ConfigError, load_settings

SETUP_MESSAGE = (
    "Setup needed: OPENROUTER_API_KEY and MODEL_NAME must be set in .env (see .env.example)."
)


@pytest.mark.parametrize(
    "environ",
    [
        {},
        {"OPENROUTER_API_KEY": "sk-test"},
        {"MODEL_NAME": "deepseek/deepseek-v4-flash-0731"},
        {"OPENROUTER_API_KEY": "  ", "MODEL_NAME": "deepseek/deepseek-v4-flash-0731"},
    ],
)
def test_ac_5_7_missing_key_or_model_raises_config_error_with_setup_message(environ):
    with pytest.raises(ConfigError) as raised:
        load_settings(environ)

    assert str(raised.value) == SETUP_MESSAGE


def test_ac_5_7_complete_configuration_loads():
    settings = load_settings(
        {"OPENROUTER_API_KEY": "sk-test", "MODEL_NAME": "deepseek/deepseek-v4-flash-0731"}
    )

    assert settings.model_name == "deepseek/deepseek-v4-flash-0731"


def test_ac_5_7_model_name_without_provider_prefix_raises_config_error():
    with pytest.raises(ConfigError) as raised:
        load_settings({"OPENROUTER_API_KEY": "sk-test", "MODEL_NAME": "flash"})

    assert str(raised.value) == SETUP_MESSAGE
