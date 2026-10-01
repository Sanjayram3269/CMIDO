from src.construction.experiments import build_metadata, stable_hash


def test_hash_is_stable():
    payload = {"seed": 42, "parameters": {"delay": 3}}
    assert stable_hash(payload) == stable_hash(payload)


def test_metadata_contains_fingerprint():
    metadata = build_metadata("EXP-001", 42, {"delay": 3})
    assert metadata["experiment_id"] == "EXP-001"
    assert len(metadata["configuration_fingerprint"]) == 64
