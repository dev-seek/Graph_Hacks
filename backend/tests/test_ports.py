def test_five_ports_importable() -> None:
    from app import ports

    assert set(ports.__all__) == {
        "AuthPort",
        "ConsentPort",
        "EmbeddingPort",
        "ExportPort",
        "LLMPort",
        "NotifierPort",
    }


def test_llm_config_models_only_in_yaml() -> None:
    from pathlib import Path

    import yaml

    cfg = yaml.safe_load(Path("config/llm.yaml").read_text())
    assert cfg["profiles"]["fast"]["model"] == "claude-haiku-5-5"
