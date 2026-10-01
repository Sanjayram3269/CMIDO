from src.construction.dashboard_view import (
    build_dependency_3d_data,
    build_kpi_state,
    scenario_options,
)


def project_fixture():
    return {
        "project": {"project_id": "P1", "project_name": "Demo", "location": "Bengaluru"},
        "activities": [
            {"activity_id": "A1", "activity_name": "Start", "duration_days": 2},
            {"activity_id": "A2", "activity_name": "Finish", "duration_days": 3},
        ],
        "dependencies": [
            {"predecessor_id": "A1", "successor_id": "A2"},
        ],
    }


def test_dependency_3d_data_is_deterministic():
    data = build_dependency_3d_data(project_fixture())
    assert data["ids"] == ["A1", "A2"]
    assert data["z"] == [2.0, 3.0]
    assert data["edge_x"] == [0.0, 1.0, None]


def test_scenario_options_preserve_activity_contract():
    options = scenario_options(project_fixture())
    assert options == [
        {"activity_id": "A1", "activity_name": "Start", "duration_days": 2},
        {"activity_id": "A2", "activity_name": "Finish", "duration_days": 3},
    ]


def test_kpi_state_normalizes_unified_dashboard():
    dashboard = {
        "overview": {
            "project_duration_days": 74,
            "critical_activities": 8,
            "total_activities": 11,
            "total_material_types": 9,
        },
        "resources": {
            "summary": {
                "shortage_resources": 2,
                "feasible_resources": 7,
            }
        },
        "status": "RESOURCE_SHORTAGE",
    }
    assert build_kpi_state(dashboard) == {
        "duration": 74,
        "critical": 8,
        "activities": 11,
        "materials": 9,
        "resource_shortages": 2,
        "resource_feasible": 7,
        "status": "RESOURCE_SHORTAGE",
    }
