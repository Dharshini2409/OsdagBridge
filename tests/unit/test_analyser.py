import ospgrillage as og
import pytest

from osdagbridge.core.bridge_types.plate_girder.analyser import BridgeGrillageModel
from osdagbridge.core.utils.codes.irc6_2017 import IRC6_2017
from osdagbridge.core.utils.common import KEY_LL_IRC_CLASS_FATIGUE


class DummyModel:
    def __init__(self):
        self.load_cases = []

    def add_load_case(self, load_case, load_factor=1):
        self.load_cases.append((load_case, load_factor))


def test_fatigue_helper_geometry_and_axle_totals():
    fatigue = IRC6_2017.cl_204_6_fatigue_load()

    assert fatigue["x"] == pytest.approx([0.0, 4.5, 5.9])
    assert max(fatigue["x"]) - min(fatigue["x"]) == pytest.approx(5.9)
    assert fatigue["z"] == pytest.approx([-0.840, 0.840])
    assert [load / (1000 * 9.81) for load in fatigue["wheel_loads"]] == pytest.approx([12.0, 14.0, 14.0])


def test_fatigue_vehicle_wheel_coordinates_and_splitting():
    bridge = BridgeGrillageModel()
    vehicle = bridge.create_fatigue_vehicle()

    wheels = [
        item.load_point_1
        for item in vehicle.compound_load_obj_list
    ]

    assert len(wheels) == 6
    assert [wheel.x for wheel in wheels] == pytest.approx([0.0, 0.0, 4.5, 4.5, 5.9, 5.9])
    assert sorted(set(wheel.z for wheel in wheels)) == pytest.approx([3.410, 5.090])
    assert [wheel.p for wheel in wheels] == pytest.approx([
        12 * 1000 * 9.81 / 2,
        12 * 1000 * 9.81 / 2,
        14 * 1000 * 9.81 / 2,
        14 * 1000 * 9.81 / 2,
        14 * 1000 * 9.81 / 2,
        14 * 1000 * 9.81 / 2,
    ])
    assert sum(wheel.p for wheel in wheels) == pytest.approx(40 * 1000 * 9.81)


def test_fatigue_moving_case_disabled_and_enabled_are_separate():
    bridge = BridgeGrillageModel()
    bridge.L = 30.0
    model = DummyModel()

    disabled = bridge.create_fatigue_moving_load_case(
        model=model,
        span=30.0,
        enabled=False,
    )
    assert disabled is None
    assert model.load_cases == []
    assert bridge.fatigue_moving_load_case is None
    assert bridge.vehicle_moving_loads_by_case == {}

    enabled = bridge.create_fatigue_moving_load_case(
        model=model,
        span=30.0,
        enabled=True,
    )
    assert enabled is bridge.fatigue_moving_load_case
    assert enabled.name == "Moving Fatigue Vehicle"
    assert len(model.load_cases) == 1
    assert model.load_cases[0][1] == 1
    assert bridge.vehicle_moving_loads_by_case == {}

    path = enabled.common_path
    assert path.start_point == og.Point(-5.9, 0.0, 0.0)
    assert path.end_point == og.Point(35.9, 0.0, 0.0)


@pytest.mark.parametrize(
    ("input_dict", "expected"),
    [
        ({KEY_LL_IRC_CLASS_FATIGUE: True}, True),
        ({KEY_LL_IRC_CLASS_FATIGUE: False}, False),
        ({KEY_LL_IRC_CLASS_FATIGUE: "true"}, True),
        ({KEY_LL_IRC_CLASS_FATIGUE: "false"}, False),
        ({}, False),
    ],
)
def test_fatigue_checkbox_handling(input_dict, expected):
    assert BridgeGrillageModel.is_fatigue_vehicle_enabled(input_dict) is expected


def test_fatigue_case_does_not_change_ordinary_vehicle_collections():
    bridge = BridgeGrillageModel()
    bridge.L = 30.0

    class_a_vehicle = object()
    class_70r_vehicle = object()
    bridge.vehicle_moving_loads_by_case = {
        1: [class_a_vehicle],
        2: [class_70r_vehicle],
    }
    bridge.vehicle_type_map = {
        id(class_a_vehicle): "ClassA",
        id(class_70r_vehicle): "Class70R",
    }
    bridge.vehicle_moving_loads = [class_a_vehicle, class_70r_vehicle]

    ordinary_collections = {
        "by_case": {
            key: list(value)
            for key, value in bridge.vehicle_moving_loads_by_case.items()
        },
        "type_map": dict(bridge.vehicle_type_map),
        "flat_list": list(bridge.vehicle_moving_loads),
    }

    model = DummyModel()
    class_a_load_case = og.create_load_case(name="Case1 ClassA")
    class_70r_load_case = og.create_load_case(name="Case2 Class70R")
    class_a_load_case.add_load(class_a_vehicle, load_factor=0.75)
    class_70r_load_case.add_load(class_70r_vehicle, load_factor=1.0)
    model.load_cases.extend([
        (class_a_load_case, 1.1),
        (class_70r_load_case, 1.2),
    ])
    model.load_combination_dict = {
        "1.35DL + 1.5ClassA": [
            {"loadcase": class_a_load_case, "load_factor": 1.5},
        ],
        "1.35DL + 1.5Class70R": [
            {"loadcase": class_70r_load_case, "load_factor": 1.5},
        ],
    }

    ordinary_load_factors_before = {
        load_case.name: {
            "case_factor": case_factor,
            "vehicle_factors": [
                load_group["factor"] for load_group in load_case.load_groups
            ],
        }
        for load_case, case_factor in model.load_cases
    }
    ordinary_combinations_before = {
        name: [
            (term["loadcase"].name, term["load_factor"])
            for term in combination
        ]
        for name, combination in model.load_combination_dict.items()
    }

    bridge.create_fatigue_moving_load_case(
        model=model,
        span=30.0,
        enabled=True,
    )

    assert {
        "by_case": {
            key: list(value)
            for key, value in bridge.vehicle_moving_loads_by_case.items()
        },
        "type_map": dict(bridge.vehicle_type_map),
        "flat_list": list(bridge.vehicle_moving_loads),
    } == ordinary_collections
    assert model.load_cases[:2] == [
        (class_a_load_case, 1.1),
        (class_70r_load_case, 1.2),
    ]
    assert model.load_cases[2][1] == 1
    assert {
        load_case.name: {
            "case_factor": case_factor,
            "vehicle_factors": [
                load_group["factor"] for load_group in load_case.load_groups
            ],
        }
        for load_case, case_factor in model.load_cases[:2]
    } == ordinary_load_factors_before
    assert {
        name: [
            (term["loadcase"].name, term["load_factor"])
            for term in combination
        ]
        for name, combination in model.load_combination_dict.items()
    } == ordinary_combinations_before
