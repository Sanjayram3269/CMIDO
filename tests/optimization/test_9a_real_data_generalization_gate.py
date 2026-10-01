from pathlib import Path

from src.optimization.cmido_9a_real_data_generalization_gate import run_gate


ROOT = Path(__file__).resolve().parents[2]


def test_9a_gate_passes():
    result = run_gate(ROOT)
    assert result["status"] == "PASS"
    assert result["checks_passed"] == result["checks_total"]


def test_9a_contract_contains_generalization_requirements():
    text = (ROOT / "src/optimization/cmido_9a_real_data_generalization_gate.py").read_text(encoding="utf-8")
    required = [
        "CMIDO 9A",
        "INGESTION_SCHEMA_VERSION",
        "explicit_mapping_ingestion",
        "duration_unit_normalization",
        "dependency_integrity",
        "provenance_present",
        "source_row_counts_present",
        "rejected_record_reporting",
        "deterministic_fingerprint",
        "CMIDO_9A_REAL_DATA_GENERALIZATION_MANIFEST.json",
    ]
    for element in required:
        assert element in text


def test_9a_fixture_has_explicit_mapping():
    mapping = ROOT / "examples/9A_real_data/mapping.json"
    assert mapping.exists()
    text = mapping.read_text(encoding="utf-8")
    assert '"schema_version": "9A-1.0"' in text
    assert '"source_format": "csv_bundle"' in text
    assert '"duration_unit_column": "unit"' in text
