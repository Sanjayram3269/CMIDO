from src.optimization.cmido_8q_publication_artifacts import generate, project_root


def test_8q_generator_resolves_repo_root():
    root = project_root()
    assert (root / "results").exists()


def test_8q_generator_uses_source_artifacts():
    manifest, checks = generate(project_root())
    assert manifest["stage"] == "8Q"
    assert manifest["artifacts"]
    names = {row["check"] for row in checks}
    assert "T5_pairwise_source_exists" in names
    assert "T6_primary_source_exists" in names
    assert "T4_stress_source_exists" in names
    assert "T4_robustness_source_exists" in names


def test_8q_t4_stress_robustness_table():
    manifest, checks = generate(project_root())
    assert manifest["status"] == "PASS", manifest
    names = {row["check"] for row in checks}
    for required in (
        "T4_shared_metric_columns",
        "T4_stress_rows",
        "T4_robustness_rows",
        "T4_expected_rows",
        "T4_four_controllers",
        "T4_no_nan_values",
    ):
        assert required in names, required
    t4 = next((a for a in manifest["artifacts"] if a["artifact"] == "T4_RO3_stress_robustness.csv"), None)
    assert t4 is not None, "T4 must be registered as a manifest artifact"
    assert t4["source_path"].endswith("RO3_step37_stress_summary.csv")
    # T4 is built from two frozen upstreams; both hashes are recorded.
    assert t4["secondary_source_path"].endswith("RO3_step38_holding_rate_summary.csv")
    assert t4["source_sha256"] and t4["secondary_source_sha256"]
    import pandas as pd

    out = project_root() / "results" / "8Q_publication_artifacts"
    t4_df = pd.read_csv(out / "T4_RO3_stress_robustness.csv")
    assert len(t4_df) == 28
    assert set(t4_df["scenario_family"]) == {"duration_stress", "holding_rate_robustness"}
    assert set(t4_df["controller"]) == {"O1", "O2", "O3", "O4"}


def test_8q_source_of_truth_has_no_manual_result_placeholders():
    manifest, _ = generate(project_root())
    assert manifest["artifacts"]
    for artifact in manifest["artifacts"]:
        assert artifact["source_path"]
        assert artifact["source_sha256"]
        assert artifact["generation_script"]
