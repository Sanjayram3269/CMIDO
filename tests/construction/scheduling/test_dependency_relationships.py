from src.construction.scheduling.backward_pass import calculate_backward_pass
from src.construction.scheduling.forward_pass import calculate_forward_pass


def project_for(relationship: str) -> dict:
    return {
        "project": {"project_id": "REL", "project_name": "relationship test"},
        "activities": [
            {"activity_id": "A", "activity_name": "A", "duration_days": 5},
            {"activity_id": "B", "activity_name": "B", "duration_days": 3},
        ],
        "dependencies": [
            {
                "dependency_id": "D1",
                "project_id": "REL",
                "predecessor_id": "A",
                "successor_id": "B",
                "relationship_type": relationship,
                "lag_days": 0,
            }
        ],
    }


def test_forward_pass_supports_all_dependency_relationships():
    expected_es = {"FS": 5, "SS": 0, "FF": 2, "SF": 0}

    for relationship, expected in expected_es.items():
        results = calculate_forward_pass(project_for(relationship))
        by_id = {item["activity_id"]: item for item in results}
        assert by_id["B"]["es"] == expected


def test_backward_pass_supports_all_dependency_relationships():
    expected_ls = {"FS": 0, "SS": -3, "FF": 0, "SF": 5}
    expected_lf = {"FS": 5, "SS": 2, "FF": 5, "SF": 10}

    for relationship in ("FS", "SS", "FF", "SF"):
        results = calculate_backward_pass(project_for(relationship))
        by_id = {item["activity_id"]: item for item in results}
        assert by_id["A"]["ls"] == expected_ls[relationship]
        assert by_id["A"]["lf"] == expected_lf[relationship]


def test_forward_relationship_constraints_are_preserved():
    for relationship in ("FS", "SS", "FF", "SF"):
        project = project_for(relationship)
        results = calculate_forward_pass(project)
        by_id = {item["activity_id"]: item for item in results}
        a = by_id["A"]
        b = by_id["B"]

        if relationship == "FS":
            assert b["es"] >= a["ef"]
        elif relationship == "SS":
            assert b["es"] >= a["es"]
        elif relationship == "FF":
            assert b["ef"] >= a["ef"]
        elif relationship == "SF":
            assert b["ef"] >= a["es"]
