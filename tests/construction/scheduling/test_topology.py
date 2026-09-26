import json

import pytest

from src.construction.scheduling.topology import (
    topological_order,
)


def load_project():
    with open(
        "data/projects/cmido_demo_project.json",
        encoding="utf-8",
    ) as file:
        return json.load(file)


def test_topological_order_contains_all_activities():
    project = load_project()

    order = topological_order(project)

    assert len(order) == 11
    assert len(set(order)) == 11


def test_topological_order_respects_dependencies():
    project = load_project()

    order = topological_order(project)
    position = {
        activity_id: index
        for index, activity_id in enumerate(order)
    }

    for dependency in project["dependencies"]:
        predecessor = dependency["predecessor_id"]
        successor = dependency["successor_id"]

        assert position[predecessor] < position[successor]


def test_cycle_is_rejected():
    project = load_project()

    project["dependencies"].append(
        {
            "predecessor_id": "A011",
            "successor_id": "A001",
        }
    )

    with pytest.raises(
        ValueError,
        match="cycle",
    ):
        topological_order(project)