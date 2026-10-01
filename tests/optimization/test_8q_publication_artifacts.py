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


def test_8q_source_of_truth_has_no_manual_result_placeholders():
    manifest, _ = generate(project_root())
    assert manifest["artifacts"]
    for artifact in manifest["artifacts"]:
        assert artifact["source_path"]
        assert artifact["source_sha256"]
        assert artifact["generation_script"]
