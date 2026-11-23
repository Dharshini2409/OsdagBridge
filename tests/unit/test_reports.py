from io import BytesIO
from pathlib import Path

import pytest
from PIL import Image

from osdagbridge.core.boq.boq_generator import calculate_material_quantities
from osdagbridge.core.reports.chap2 import _bracing_tables, _girder_tables
from osdagbridge.core.reports.chap4 import ch4_analysis
from osdagbridge.core.reports.chap3 import ch3_loads
from osdagbridge.core.reports.chap6 import ch6_drawings
from osdagbridge.core.reports.chap5 import ch5_design_checks
from osdagbridge.core.reports.chap7 import ch7_quantities
from osdagbridge.core.reports.executive_summary import executive_summary
from osdagbridge.core.reports.report_utils import (
    _fig_embed,
    _fig_or_placeholder,
    _tex,
    repeat_longtable_headers,
)
from osdagbridge.core.reports.charts import (
    material_quantity_chart,
    material_quantity_series,
    utilization_ratio_chart,
    utilization_ratio_series,
    _format_quantity,
    _utilization_label_lines,
)
from osdagbridge.core.reports.report_generator import (
    ReportFigures,
    ReportMetadata,
    ReportOptions,
    ReportPayload,
    ReportDataBridge,
    ReportRequest,
    build_report_payload,
    generate_report,
    preamble,
    title_page,
)
from osdagbridge.core.utils.common import (
    KEY_CB_AREA,
    KEY_CB_DENSITY,
    KEY_DESIGN_MODE,
    KEY_FOOTPATH,
    KEY_LL_IRC_CLASS_A,
    KEY_MP_CB_BRACING_SECTION_DESIGNATION,
    KEY_MP_CB_MEMBER_ID,
    KEY_MP_CB_SELECT_GIRDERS,
    KEY_MP_GIRDER_BOTTOM_FLANGE_THICKNESS,
    KEY_MP_GIRDER_BOTTOM_FLANGE_WIDTH,
    KEY_MP_GIRDER_DEPTH,
    KEY_MP_GIRDER_TOP_FLANGE_THICKNESS,
    KEY_MP_GIRDER_TOP_FLANGE_WIDTH,
    KEY_MP_GIRDER_WEB_THICKNESS,
    KEY_MATERIAL_DECK_DENSITY,
    KEY_SPAN,
    KEY_TS_DECK_THICKNESS,
    KEY_TS_FOOTPATH_WIDTH,
    KEY_TS_NO_OF_GIRDERS,
    KEY_WC_LD_LANE_TABLE_COUNT,
)


def _design_output():
    return {
        "design_results": {
            "per_girder": {
                "G1": {"checks": [{"dcr": 0.72}, {"dcr": 0.91}]},
                "G2": {"checks": [{"dcr": 1.04}]},
            }
        },
        "deck_design_results": {
            "ur_bot_uls": 0.83,
            "ur_top_uls": 0.94,
            "deck_thickness_mm": 250,
        },
        "crossbracing_design_results": {
            "G1-G2": {
                "diagonal": {
                    "tension": {"Member.efficiency": 0.45},
                    "compression": {"Optimum.UR": 0.68},
                }
            }
        },
        "end_diaphragm_design_results": {
            "G1-G2": {
                "chord": {
                    "compression": {"Member.efficiency": 0.77},
                }
            }
        },
    }


def test_utilization_series_uses_real_component_results():
    series = utilization_ratio_series(_design_output())

    assert series["Steel girders"] == [("G1", 0.91), ("G2", 1.04)]
    assert series["Concrete deck slab"] == [
        ("bot uls", 0.83),
        ("top uls", 0.94),
    ]
    assert series["Cross bracing"] == [
        ("G1-G2 diagonal (tension)", 0.45),
        ("G1-G2 diagonal (compression)", 0.68),
    ]
    assert series["End diaphragms"] == [
        ("G1-G2 chord (compression)", 0.77),
    ]


def test_charts_render_only_when_numeric_data_exists():
    assert utilization_ratio_chart({}) is None
    assert material_quantity_chart({}) is None

    quantities = {
        "steel_girders_vol_total": "12.50",
        "steel_girders_wt_total": "98.25",
        "concrete_deck_vol_total": "N.A.",
        "concrete_deck_wt_total": "N.A.",
    }
    ur_png = utilization_ratio_chart(_design_output())
    assert ur_png.startswith(b"\x89PNG\r\n\x1a\n")
    with Image.open(BytesIO(ur_png)) as image:
        red_threshold_pixels = sum(
            count
            for count, (red, green, blue) in image.convert("RGB").getcolors(
                maxcolors=image.width * image.height
            )
            if red > 180 and green < 80 and blue < 80
        )
    assert red_threshold_pixels > 100
    assert material_quantity_chart(quantities).startswith(b"\x89PNG\r\n\x1a\n")


def test_material_series_omits_unavailable_values():
    series = material_quantity_series(
        {
            "steel_girders_vol_total": "12.50",
            "steel_girders_wt_total": "98.25",
            "concrete_deck_vol_total": "N.A.",
            "concrete_deck_wt_total": None,
        }
    )

    assert series["Total volume (m³)"] == [("Structural steel - girders", 12.5)]
    assert series["Total weight (MT)"] == [("Structural steel - girders", 98.25)]


def test_end_diaphragm_quantity_is_marked_unavailable_without_bom_source():
    quantities = calculate_material_quantities({}, {})

    assert quantities["end_diaphragms_vol_total"] == "N.A."
    assert quantities["end_diaphragms_wt_total"] == "N.A."
    series = material_quantity_series(quantities)
    assert all(
        "End diaphragms" not in label
        for values in series.values()
        for label, _ in values
    )


def test_bom_uses_input_concrete_density_and_does_not_estimate_rebar_weight():
    inputs = {
        KEY_SPAN: 30,
        KEY_TS_NO_OF_GIRDERS: 4,
        KEY_TS_DECK_THICKNESS: 250,
        KEY_MATERIAL_DECK_DENSITY: 24.5,
        KEY_CB_AREA: 302282.768,
        KEY_CB_DENSITY: 25.0,
        "typical_section.overall_bridge_width": 8.4,
    }
    outputs = {
        "deck_design_results": {
            "rebar_bottom_dia": "12",
            "rebar_bottom_spacing": "185",
            "rebar_bottom_area": "611",
            "rebar_top_dia": "10",
            "rebar_top_spacing": "160",
            "rebar_top_area": "492",
        }
    }

    quantities = calculate_material_quantities(inputs, outputs)

    expected_concrete_mass_mt = 63.0 * 24.5 / 9.81
    assert quantities["concrete_deck_wt_total"] == f"{expected_concrete_mass_mt:.2f}"
    expected_barrier_mass_mt = (
        2 * (302282.768 / 1e6) * 30 * 25.0 / 9.81
    )
    assert quantities["crash_barrier_wt_total"] == f"{expected_barrier_mass_mt:.2f}"
    assert quantities["rebar_deck_vol_formula"] == "N.A."
    assert quantities["rebar_deck_vol_total"] == "N.A."
    assert quantities["rebar_deck_wt_total"] == "N.A."


def test_chapter_two_converts_internal_girder_metres_to_mm():
    input_dict = {
        f"{KEY_MP_GIRDER_DEPTH}.G1.M1": 1.67,
        f"{KEY_MP_GIRDER_WEB_THICKNESS}.G1.M1": 0.01,
        f"{KEY_MP_GIRDER_TOP_FLANGE_WIDTH}.G1.M1": 0.51,
        f"{KEY_MP_GIRDER_TOP_FLANGE_THICKNESS}.G1.M1": 0.022,
        f"{KEY_MP_GIRDER_BOTTOM_FLANGE_WIDTH}.G1.M1": 0.51,
        f"{KEY_MP_GIRDER_BOTTOM_FLANGE_THICKNESS}.G1.M1": 0.022,
    }

    latex = _girder_tables(input_dict, 1)

    assert "1670 mm & 10 mm & 510 mm, 22 mm & 510 mm, 22 mm" in latex


def test_chapter_two_collapses_single_cross_bracing_id_and_labels_input_section():
    suffix = "G1G2.B1M1"
    latex = _bracing_tables(
        {
            f"{KEY_MP_CB_SELECT_GIRDERS}.{suffix}": "G1 to G2",
            f"{KEY_MP_CB_MEMBER_ID}.{suffix}": "B1M1 to B1M1",
            f"{KEY_MP_CB_BRACING_SECTION_DESIGNATION}.{suffix}": "L100x100x10",
            KEY_DESIGN_MODE: "Optimized",
        },
        2,
    )

    cross_bracing_table = latex.split(
        r"\caption{\textbf{Member Properties: Cross Bracing Details}}", 1
    )[1].split(r"\end{longtable}", 1)[0]
    assert r"\textbf{Input Section}" in cross_bracing_table
    assert "B1M1 &" in cross_bracing_table
    assert "B1M1 to B1M1" not in cross_bracing_table
    assert "L100x100x10" in cross_bracing_table
    assert "sections used in design checks are reported in Chapter 5" in latex


def test_chapter_three_respects_boolean_vehicle_selections():
    base_inputs = {
        KEY_SPAN: 30,
        KEY_WC_LD_LANE_TABLE_COUNT: 2,
        KEY_FOOTPATH: "None",
        KEY_TS_FOOTPATH_WIDTH: 0,
    }

    for selected in (True, "true"):
        inputs = dict(base_inputs)
        inputs[KEY_LL_IRC_CLASS_A] = selected
        latex = ch3_loads(inputs)
        assert "Class A" in latex
        assert "Centrifugal Force (IRC 6)" in latex

    for unselected in (False, "false"):
        inputs = dict(base_inputs)
        inputs[KEY_LL_IRC_CLASS_A] = unselected
        latex = ch3_loads(inputs)
        assert "Class A" not in latex
        assert "N/A" in latex

    assert "Class A" not in ch3_loads(base_inputs)


def test_chapter_three_parses_integral_lane_count_strings_for_braking():
    inputs = {
        KEY_SPAN: 30,
        KEY_WC_LD_LANE_TABLE_COUNT: "2.0",
        KEY_FOOTPATH: "None",
        KEY_TS_FOOTPATH_WIDTH: 0,
        KEY_LL_IRC_CLASS_A: True,
    }

    latex = ch3_loads(inputs)

    assert "Impact Load Factor" in latex
    assert "Braking Load (IRC 6)" in latex
    assert "N/A" not in latex.split("Braking Load (IRC 6)", 1)[1].split(r"\\", 1)[0]


def test_chapter_four_reactions_table_uses_analysis_summary_values():
    from types import SimpleNamespace

    bridge = SimpleNamespace(
        input_dict={KEY_SPAN: 30},
        output_dict={},
    )
    latex = ch4_analysis(
        {
            "load_cases": {},
            "reactions": {
                "DL": {"left_kN": 123.4, "right_kN": 120.6},
                "1.0 LL": {"left_kN": 88.0, "right_kN": 90.0},
            },
        },
        {},
        bridge,
        30,
    )
    reaction_table = latex.split(
        r"\caption{\textbf{Reactions at Supports}}", 1
    )[1].split(r"\end{longtable}", 1)[0]

    assert "DL & 123.400 & 120.600" in reaction_table
    assert "1.0 LL & 88.000 & 90.000" in reaction_table


def test_support_reactions_use_upward_sign_and_convert_newtons_to_kn(monkeypatch):
    import numpy as np
    import xarray as xr
    from osdagbridge.core.bridge_types.plate_girder.analysis_results import (
        PlateGirderAnalysisResults,
        ops,
    )
    from osdagbridge.core.bridge_types.plate_girder.results_data import (
        build_forces_summary,
    )

    ds = xr.Dataset(
        {
            "forces": (
                ("Loadcase", "Element", "Component"),
                np.array([[[-100_000, -100_000, 0, 0],
                           [-100_000, -100_000, 0, 0]]], dtype=float),
            )
        },
        coords={
            "Loadcase": ["DL"],
            "Element": [101, 102],
            "Component": ["Vy_i", "Vy_j", "Mz_i", "Mz_j"],
        },
    )
    element_map = [(101, 10, 11), (102, 11, 12)]
    girders = {"G1": {"element_map": element_map, "elements": [101, 102]}}
    handler = PlateGirderAnalysisResults.__new__(PlateGirderAnalysisResults)
    handler.ds = ds
    handler.edge_dist = 0
    monkeypatch.setattr(
        handler,
        "build_grillage_connectivity",
        lambda: (
            {10: [0, 0, 0], 11: [5, 0, 0], 12: [10, 0, 0]},
            {},
            {},
        ),
    )
    monkeypatch.setattr(handler, "build_girders", lambda verbose=False: (girders, {}))
    monkeypatch.setattr(handler, "filter_girders", lambda value: value)
    monkeypatch.setattr(ops, "eleNodes", lambda eid: {101: [10, 11], 102: [11, 12]}[eid])

    reactions = handler._get_reactions_df("DL")
    summary = build_forces_summary(
        handler,
        {"G1": {"DL": {"Mz_max": 0.0, "Mz_min": 0.0, "Vy_max": 0.0, "Vy_min": 0.0}}},
    )

    assert reactions.loc[0, "Ra (kN)"] == 100.0
    assert reactions.loc[0, "Rb (kN)"] == 100.0
    assert summary["reactions"]["DL"] == {"left_kN": 100.0, "right_kN": 100.0}


def test_executive_summary_reflects_fatigue_failure_in_girder_outcome():
    output_dict = _design_output()
    output_dict["design_results"]["per_girder"]["G2"]["checks"] = [
        {"name": "Fatigue Normal Stress", "dcr": 1.54, "status": "FAIL"}
    ]

    latex = executive_summary({}, output_dict, {})

    assert "Overall Design Status" in latex
    assert "Fail (Fatigue Normal Stress)" in latex
    assert r"\textbf{Steel girders:} \textcolor{red}{FAIL} (Fatigue Normal Stress)" in latex
    assert "Girder design pass" not in latex
    assert "Concrete deck slab:} PASS" in latex
    assert "End diaphragms:} PASS" in latex


def test_chapter_six_missing_drawings_are_not_misleading_placeholders():
    latex = ch6_drawings({})

    assert "CAD source unavailable for this report" in latex
    assert "PLACEHOLDER" not in latex


def test_chapter_six_embeds_all_available_generated_view_keys():
    figure_keys = (
        "final_geometry",
        "cross_section",
        "girder_top",
        "girder_3d",
        "section_preview",
        "stiffener_preview",
        "cb_diagram",
        "cb_bracing",
        "cb_top_chord",
        "cb_bottom_chord",
        "ed_diagram",
        "ed_bracing",
        "ed_top_chord",
        "ed_bottom_chord",
    )
    latex = ch6_drawings({key: f"images/{key}.png" for key in figure_keys})

    assert latex.count(r"\includegraphics") == len(figure_keys)
    assert "CAD source unavailable" not in latex


def test_missing_report_figures_are_explicitly_unavailable():
    assert "Source image unavailable for this report" in _fig_or_placeholder(
        None, "Bridge plan"
    )
    assert "Analysis figure unavailable for this report" in _fig_embed(
        None, "Moment envelope"
    )


def test_material_chart_uses_wide_stacked_panels():
    chart = material_quantity_chart(
        {
            "steel_girders_vol_total": 12.5,
            "steel_girders_wt_total": 98.25,
        }
    )

    with Image.open(BytesIO(chart)) as image:
        assert image.width >= 1600
        assert image.height >= 500


def test_material_chart_number_format_avoids_unreadable_scientific_notation():
    assert _format_quantity(12500) == "12,500"
    assert _format_quantity(0.0005) == "0.0005"
    assert _format_quantity(0.00149) == "0.00149"
    assert _format_quantity(0.00004) == "4.00e-05"


def test_utilization_chart_labels_spell_out_member_and_force_types():
    assert _utilization_label_lines(
        "G1-G2 diagonal (compression)"
    ) == ("G1-G2", "Diagonal", "Compression")
    assert _utilization_label_lines("bot uls") == ("Bottom", "ULS")


def test_utilization_chart_has_horizontal_ur_threshold():
    chart = utilization_ratio_chart(_design_output())

    with Image.open(BytesIO(chart)) as image:
        pixels = image.convert("RGB").load()
        red_pixels_per_row = [
            sum(
                pixels[x, y][0] > 180
                and pixels[x, y][1] < 80
                and pixels[x, y][2] < 80
                for x in range(image.width)
            )
            for y in range(image.height)
        ]

    assert max(red_pixels_per_row) > 500


def test_longtable_headers_repeat_and_remain_idempotent():
    latex = r"""\begin{longtable}{|l|l|}
\caption{Example} \\
\hline
\textbf{Item} & \textbf{Value} \\
\hline
data & 1 \\
\end{longtable}"""

    rendered = repeat_longtable_headers(latex)

    assert rendered.count(r"\endfirsthead") == 1
    assert rendered.count(r"\endhead") == 1
    assert rendered.count(r"\textbf{Item}") == 2
    assert repeat_longtable_headers(rendered) == rendered


def test_longtable_empty_continuation_head_receives_column_headers():
    latex = r"""\begin{longtable}{|l|l|}
\caption{Example} \\
\hline
\textbf{Item} & \textbf{Value} \\
\hline
\endfirsthead
\endhead
data & 1 \\
\end{longtable}"""

    rendered = repeat_longtable_headers(latex)

    assert rendered.count(r"\textbf{Item}") == 2
    assert r"\textbf{Item} & \textbf{Value}" in rendered.split(
        r"\endfirsthead", 1
    )[1]


def test_end_diaphragm_report_tables_use_end_diaphragm_results():
    output_dict = {
        "crossbracing_forces_dict": {
            "pairs": {
                "G1-G2": {
                    "diag_compression_kN": 99.0,
                    "diag_compression_gov_lc": "CB-GOV",
                }
            }
        },
        "crossbracing_design_results": {
            "G1-G2": {
                "diagonal": {
                    "compression": {
                        "Member.efficiency": 0.1,
                        "Design.Strength": 990.0,
                        "Member.Slenderness": 10.0,
                        "Member.Length": "1000",
                    }
                }
            }
        },
        "end_diaphragm_forces_dict": {
            "pairs": {
                "G1-G2": {
                    "diag_compression_kN": 5.0,
                    "diag_compression_gov_lc": "ED-GOV",
                }
            }
        },
        "end_diaphragm_design_results": {
            "G1-G2": {
                "diagonal": {
                    "compression": {
                        "Member.efficiency": 0.75,
                        "Design.Strength": 6.67,
                        "Member.Slenderness": 25.0,
                        "Member.Length": "2000",
                    }
                }
            }
        },
    }
    bridge = ReportDataBridge(output_dict, {}, None)
    latex = ch5_design_checks({}, bridge)
    end_diaphragm_section = latex.split(
        r"\section{End Diaphragm Design}", 1
    )[1].split(r"\section{Overall Design Check Summary}", 1)[0]

    assert "ED-GOV" in end_diaphragm_section
    assert "5.000" in end_diaphragm_section
    assert "0.750" in end_diaphragm_section
    assert "CB-GOV" not in end_diaphragm_section
    assert "99.000" not in end_diaphragm_section


def test_tex_renders_less_equal_as_latex_math():
    assert _tex("Leg ≤ H_limit") == r"Leg \ensuremath{\leq} H\_\allowbreak{}limit"


def test_chapter_seven_uses_repeated_pylatex_longtable_header():
    latex = ch7_quantities(
        {"steel_girders_wt_total": "98.25"},
        {"material_quantities": "images/material_quantities.png"},
    )

    assert r"\begin{longtable}" in latex
    assert r"\endfirsthead" in latex
    assert r"\endhead" in latex
    assert "Structural Steel (IS 2062) for Girders" in latex
    assert "End Diaphragms" in latex
    assert r"\includegraphics[width=\textwidth]{images/material_quantities.png}" in latex
    assert r"\endgroup" in latex


def test_report_styles_use_shared_spacing_and_nonoverlapping_footer():
    latex = preamble("Project", "Job", "2026-01-01")

    assert r"\setlength{\footskip}{36pt}" in latex
    assert r"\setlength{\headheight}{18pt}" in latex
    assert r"\usepackage[a4paper, margin=1in]{geometry}" in latex
    assert r"\ReportFooterLeft" in latex
    assert r"\renewcommand{\headrule}{}" in latex
    assert r"\vspace{-20pt}" not in latex
    assert r"\vspace{-8pt}" not in latex


def test_report_cover_uses_the_same_default_version_as_the_header():
    metadata = ReportMetadata(
        project_name="Test",
        project_location="Test",
        designer="",
        client="",
        company="",
    )

    assert r"\textbf{Report Version} & Rev 0 \\" in title_page(
        metadata, None, None
    )


def test_report_generation_does_not_accept_a_stale_pdf_after_compile_failure(
    tmp_path, monkeypatch
):
    metadata = ReportMetadata(
        project_name="Test",
        project_location="Test",
        designer="Test",
        client="Test",
        company="Test",
        job_number="TEST",
        report_date="2026-01-01",
    )
    options = ReportOptions(
        sections=[],
        include_figures=False,
        include_toc=False,
        include_pdf=True,
    )
    payload = ReportPayload(
        metadata=metadata,
        options=options,
        inputs={},
        analysis_summary={},
        design_checks=[],
        figures=ReportFigures(),
    )
    request = ReportRequest(
        metadata=metadata,
        options=options,
        output_dir=str(tmp_path),
        file_stem="failed_compile",
    )
    stale_pdf = tmp_path / "failed_compile.pdf"
    stale_pdf.write_bytes(b"existing output")

    class FailedCompile:
        returncode = 1
        stdout = b"latex error"
        stderr = b""

    monkeypatch.setattr(
        "osdagbridge.core.reports.report_generator.subprocess.run",
        lambda *args, **kwargs: FailedCompile(),
    )

    result = generate_report(payload, request)

    assert result.pdf_path is None
    assert result.tex_path == str(tmp_path / "failed_compile.tex")
    assert Path(result.tex_path).is_file()
    assert stale_pdf.read_bytes() == b"existing output"


def test_report_generation_recompiles_until_references_stabilize(
    tmp_path, monkeypatch
):
    metadata = ReportMetadata(
        project_name="Test",
        project_location="Test",
        designer="Test",
        client="Test",
        company="Test",
        job_number="TEST",
        report_date="2026-01-01",
    )
    options = ReportOptions(
        sections=[],
        include_figures=False,
        include_toc=False,
        include_pdf=True,
    )
    payload = ReportPayload(
        metadata=metadata,
        options=options,
        inputs={},
        analysis_summary={},
        design_checks=[],
        figures=ReportFigures(),
    )
    request = ReportRequest(
        metadata=metadata,
        options=options,
        output_dir=str(tmp_path),
        file_stem="stable_references",
    )
    compile_passes = []

    class SuccessfulCompile:
        returncode = 0
        stdout = b""
        stderr = b""

    def fake_compile(command, cwd, **kwargs):
        compile_passes.append(command)
        reference_state = "page-54" if len(compile_passes) == 1 else "page-55"
        (Path(cwd) / "stable_references.aux").write_text(
            reference_state, encoding="utf-8"
        )
        (Path(cwd) / "stable_references.pdf").write_bytes(b"%PDF-1.7\n%%EOF")
        return SuccessfulCompile()

    monkeypatch.setattr(
        "osdagbridge.core.reports.report_generator.subprocess.run",
        fake_compile,
    )

    result = generate_report(payload, request)

    assert len(compile_passes) == 3
    assert result.pdf_path == str(tmp_path / "stable_references.pdf")
    assert Path(result.pdf_path).read_bytes().endswith(b"%%EOF")


def test_build_report_payload_rejects_empty_inputs():
    metadata = ReportMetadata(
        project_name="Test",
        project_location="Test",
        designer="Test",
        client="Test",
        company="Test",
    )
    options = ReportOptions(
        sections=[],
        include_figures=False,
        include_toc=False,
        include_pdf=True,
    )
    request = ReportRequest(
        metadata=metadata,
        options=options,
        output_dir=".",
        file_stem="test",
    )
    with pytest.raises(ValueError, match="input_dict is empty"):
        build_report_payload(request, {}, {})


def test_build_report_payload_propagates_exceptions_instead_of_silent_empty_payload(
    monkeypatch,
):
    metadata = ReportMetadata(
        project_name="Test",
        project_location="Test",
        designer="Test",
        client="Test",
        company="Test",
    )
    options = ReportOptions(
        sections=[],
        include_figures=False,
        include_toc=False,
        include_pdf=True,
    )
    request = ReportRequest(
        metadata=metadata,
        options=options,
        output_dir=".",
        file_stem="test",
    )

    def failing_format(_pl):
        raise RuntimeError("Geocode service failure")

    monkeypatch.setattr(
        "osdagbridge.core.reports.report_generator._format_project_location",
        failing_format,
    )

    with pytest.raises(RuntimeError, match="Failed to build report payload"):
        build_report_payload(request, {"span": 30}, {})


def test_plate_girder_bridge_generate_design_report_rejects_empty_state():
    from osdagbridge.core.bridge_types.plate_girder.plategirderbridge import (
        PlateGirderBridge,
    )

    bridge = PlateGirderBridge()
    metadata = ReportMetadata(
        project_name="Test",
        project_location="Test",
        designer="Test",
        client="Test",
        company="Test",
    )
    options = ReportOptions(
        sections=[],
        include_figures=False,
        include_toc=False,
        include_pdf=True,
    )
    request = ReportRequest(
        metadata=metadata,
        options=options,
        output_dir=".",
        file_stem="test",
    )
    with pytest.raises(
        ValueError, match="bridge inputs or design results are empty"
    ):
        bridge.generate_design_report(request, None)


def test_crash_barrier_boq_supports_both_mm2_and_m2_units():
    base_inputs = {
        KEY_SPAN: 30.0,
        KEY_TS_NO_OF_GIRDERS: 4,
        KEY_CB_DENSITY: 25.0,
    }
    # Test mm² input (e.g. from sample_bridge or default values)
    inp_mm2 = dict(base_inputs, **{KEY_CB_AREA: 302282.768})
    boq_mm2 = calculate_material_quantities(inp_mm2, {})
    assert boq_mm2["crash_barrier_vol_total"] == "18.14"
    assert boq_mm2["crash_barrier_wt_total"] == "46.22"

    # Test m² input (e.g. from Additional Inputs UI dialog)
    inp_m2 = dict(base_inputs, **{KEY_CB_AREA: 0.3023})
    boq_m2 = calculate_material_quantities(inp_m2, {})
    assert boq_m2["crash_barrier_vol_total"] == "18.14"
    assert boq_m2["crash_barrier_wt_total"] == "46.22"


def test_material_quantity_chart_renders_both_volume_and_weight():
    chart = material_quantity_chart(
        {
            "steel_girders_vol_total": "4.19",
            "steel_girders_wt_total": "32.89",
            "crash_barrier_vol_total": "18.14",
            "crash_barrier_wt_total": "46.22",
        }
    )
    assert chart is not None
    with Image.open(BytesIO(chart)) as image:
        assert image.width >= 1600
        assert image.height >= 500


def test_table_522_includes_transverse_shear_result():
    from osdagbridge.core.utils.common import KEY_SD_TS_VL, KEY_SD_TS_VRD

    output_dict = {
        "design_results": {
            "per_girder": {},
            "shear_connectors": {
                KEY_SD_TS_VL: 82.84,
                KEY_SD_TS_VRD: 999.28,
                "transverse_shear_ok": True,
            },
        },
        "deck_design_results": {},
    }
    bridge = ReportDataBridge(output_dict, {}, None)
    latex = ch5_design_checks({}, bridge)
    assert "Transverse Shear (slab)" in latex
    assert "82.84 kN/m" in latex
    assert "999.28 kN/m" in latex
    assert "0.08" in latex


def test_deflection_mapping_consistency_between_tables():
    from osdagbridge.core.reports.chap4 import ch4_analysis
    from osdagbridge.core.utils.common import KEY_SD_DEFL_LIVE, KEY_SD_DEFL_TOTAL, KEY_SPAN, KEY_TS_NO_OF_GIRDERS

    input_dict = {KEY_SPAN: "30.0", KEY_TS_NO_OF_GIRDERS: "2", "loading.dead_load.self_weight_factor": "1.0"}
    output_dict = {
        KEY_SD_DEFL_LIVE: 8.655,
        KEY_SD_DEFL_TOTAL: 22.870,
        f"{KEY_SD_DEFL_LIVE}.G1": 8.595,
        f"{KEY_SD_DEFL_TOTAL}.G1": 22.810,
        f"{KEY_SD_DEFL_LIVE}.G2": 8.655,
        f"{KEY_SD_DEFL_TOTAL}.G2": 22.870,
        "analysis_results.defl_live.G1": 19.252,
        "analysis_results.defl_total.G1": 51.090,
        "analysis_results.defl_live.G2": 19.385,
        "analysis_results.defl_total.G2": 51.225,
        "design_results": {
            "per_girder": {
                "G1": {
                    "checks": [
                        {"check_id": 13, "name": "SLS Deflection (Live)", "demand": 8.595, "capacity": 37.5, "dcr": 0.23, "status": "PASS"},
                        {"check_id": 14, "name": "SLS Deflection (Total)", "demand": 22.810, "capacity": 50.0, "dcr": 0.46, "status": "PASS"},
                    ]
                },
                "G2": {
                    "checks": [
                        {"check_id": 13, "name": "SLS Deflection (Live)", "demand": 8.655, "capacity": 37.5, "dcr": 0.23, "status": "PASS"},
                        {"check_id": 14, "name": "SLS Deflection (Total)", "demand": 22.870, "capacity": 50.0, "dcr": 0.46, "status": "PASS"},
                    ]
                },
            }
        },
        "deck_design_results": {},
    }
    bridge = ReportDataBridge(output_dict, input_dict, None)

    # Chapter 4 Analysis Results
    latex_ch4 = ch4_analysis({}, {}, bridge, 30.0)
    assert "22.870 mm" in latex_ch4
    assert "L/600 = 50.0 mm" in latex_ch4
    assert "Total Load Deflection Check Status} & PASS" in latex_ch4
    assert "composite action" in latex_ch4

    # Chapter 5 Design Checks
    latex_ch5 = ch5_design_checks({}, bridge)
    assert "22.810" in latex_ch5
    assert "22.870" in latex_ch5
    assert r"\textcolor{red}{FAIL}" not in latex_ch5  # Deflection passes in Table 5.10
    assert "Girder --- Deflection" in latex_ch5
    assert "50.00" in latex_ch5
    assert "0.46" in latex_ch5


def test_utilization_chart_dense_series_renders_without_overlap():
    dense_output = {
        "design_results": {
            "per_girder": {
                f"G{i}": {"checks": [{"dcr": 0.85 + i * 0.05}]} for i in range(1, 5)
            }
        },
        "deck_design_results": {
            "ur_bot_uls": 0.83,
            "ur_top_uls": 0.94,
        },
        "crossbracing_design_results": {
            f"G{i}-G{i+1}": {
                "diagonal": {
                    "tension": {"Member.efficiency": 0.15},
                    "compression": {"Member.efficiency": 0.08},
                },
                "chord": {
                    "tension": {"Member.efficiency": 0.12},
                    "compression": {"Member.efficiency": 0.06},
                },
            }
            for i in range(1, 4)
        },
        "end_diaphragm_design_results": {},
    }
    png_bytes = utilization_ratio_chart(dense_output)
    assert png_bytes is not None
    assert png_bytes.startswith(b"\x89PNG\r\n\x1a\n")

    with Image.open(BytesIO(png_bytes)) as img:
        assert img.width >= 1700
        assert img.height >= 1000



