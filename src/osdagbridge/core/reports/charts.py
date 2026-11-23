"""Charts built only from numeric design and quantity results."""

import math
from importlib.util import find_spec
from io import BytesIO
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from osdagbridge.core.bridge_types.plate_girder.results_data import (
    _extract_osdag_summary,
)
from osdagbridge.core.reports.styles import (
    CHART_BACKGROUND_COLOR,
    CHART_FONT_SIZE,
    CHART_GRID_COLOR,
    CHART_MUTED_COLOR,
    CHART_SMALL_FONT_SIZE,
    CHART_TEXT_COLOR,
    CHART_TITLE_FONT_SIZE,
    CHART_AXIS_COLOR,
    OSDAG_GREEN,
    UTILIZATION_THRESHOLD,
    UTILIZATION_THRESHOLD_COLOR,
    UTILIZATION_CHART_PANEL_HEIGHT,
)


_MATERIAL_ROWS = (
    ("Structural steel - girders", "steel_girders_vol_total", "steel_girders_wt_total"),
    ("Cross bracing - top chord", "bracing_top_vol_total", "bracing_top_wt_total"),
    ("Cross bracing - bottom chord", "bracing_bot_vol_total", "bracing_bot_wt_total"),
    ("Cross bracing - diagonals", "bracing_diag_vol_total", "bracing_diag_wt_total"),
    ("End diaphragms", "end_diaphragms_vol_total", "end_diaphragms_wt_total"),
    ("Concrete deck slab", "concrete_deck_vol_total", "concrete_deck_wt_total"),
    ("Deck reinforcement", "rebar_deck_vol_total", "rebar_deck_wt_total"),
    ("Shear studs", "shear_studs_vol_total", "shear_studs_wt_total"),
    ("Crash barriers", "crash_barrier_vol_total", "crash_barrier_wt_total"),
)


def _numeric_value(value):
    if isinstance(value, bool):
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(number) or number < 0:
        return None
    return number


def _format_quantity(value):
    magnitude = abs(value)
    if magnitude < 0.0001 and magnitude != 0:
        return f"{value:.2e}"
    if magnitude >= 1000:
        text = f"{value:,.2f}"
    elif magnitude >= 1:
        text = f"{value:.2f}"
    else:
        text = f"{value:.5f}"
    return text.rstrip("0").rstrip(".") if "." in text else text


def _member_efficiencies(designs):
    values = []
    if not isinstance(designs, dict):
        return values
    for pair, members in sorted(designs.items()):
        if not isinstance(members, dict):
            continue
        for member in ("diagonal", "chord"):
            forces = members.get(member)
            if not isinstance(forces, dict):
                continue
            for force_type in ("tension", "compression"):
                result = _extract_osdag_summary(forces.get(force_type) or {})
                value = _numeric_value(result.get("efficiency"))
                if value is not None:
                    values.append(
                        (f"{pair} {member} ({force_type})", value)
                    )
    return values


def utilization_ratio_series(output_dict):
    """Return actual UR/DCR results grouped by report component."""
    output_dict = output_dict or {}
    series = {
        "Steel girders": [],
        "Concrete deck slab": [],
        "Cross bracing": _member_efficiencies(
            output_dict.get("crossbracing_design_results")
        ),
        "End diaphragms": _member_efficiencies(
            output_dict.get("end_diaphragm_design_results")
        ),
    }

    design_results = output_dict.get("design_results") or {}
    per_girder = design_results.get("per_girder", {})
    if isinstance(per_girder, dict):
        for girder, result in sorted(per_girder.items()):
            if not isinstance(result, dict):
                continue
            ratios = [
                value
                for check in result.get("checks", [])
                if isinstance(check, dict)
                for value in [_numeric_value(check.get("dcr"))]
                if value is not None
            ]
            if not ratios:
                max_dcr = _numeric_value(result.get("max_dcr"))
                if max_dcr is not None:
                    ratios = [max_dcr]
            if ratios:
                series["Steel girders"].append((str(girder), max(ratios)))

    deck_results = output_dict.get("deck_design_results") or {}
    if isinstance(deck_results, dict):
        for key, raw_value in sorted(deck_results.items()):
            if not key.startswith("ur_"):
                continue
            value = _numeric_value(raw_value)
            if value is not None:
                label = key[3:].replace("_", " ")
                series["Concrete deck slab"].append((label, value))

    return series


def material_quantity_series(quantities):
    """Return BOM quantities already calculated for Chapter 7."""
    quantities = quantities or {}
    volume = []
    weight = []
    for label, volume_key, weight_key in _MATERIAL_ROWS:
        volume_value = _numeric_value(quantities.get(volume_key))
        weight_value = _numeric_value(quantities.get(weight_key))
        if volume_value is not None:
            volume.append((label, volume_value))
        if weight_value is not None:
            weight.append((label, weight_value))
    return {"Total volume (m³)": volume, "Total weight (MT)": weight}


def _chart_canvas(
    title,
    panel_values,
    columns=2,
    panel_width=900,
    fixed_panel_height=None,
):
    font_dir = Path(find_spec("matplotlib").origin).parent / "mpl-data" / "fonts" / "ttf"
    try:
        font = ImageFont.truetype(
            str(font_dir / "DejaVuSans.ttf"), CHART_FONT_SIZE
        )
        small_font = ImageFont.truetype(
            str(font_dir / "DejaVuSans.ttf"), CHART_SMALL_FONT_SIZE
        )
        title_font = ImageFont.truetype(
            str(font_dir / "DejaVuSans-Bold.ttf"), CHART_TITLE_FONT_SIZE
        )
    except OSError:
        font = ImageFont.load_default()
        small_font = font
        title_font = font
    panel_rows = max(1, (len(panel_values) + columns - 1) // columns)
    panel_height = fixed_panel_height or max(
        180,
        max((len(values) for _, values in panel_values), default=0) * 38 + 120,
    )
    image = Image.new(
        "RGB",
        (panel_width * columns + 100, panel_height * panel_rows + 155),
        CHART_BACKGROUND_COLOR,
    )
    draw = ImageDraw.Draw(image)
    draw.text((40, 25), title, fill=CHART_TEXT_COLOR, font=title_font)
    return image, draw, font, small_font, title_font, panel_width, panel_height


def _draw_panel(
    draw,
    font,
    title_font,
    x,
    y,
    width,
    height,
    title,
    values,
    threshold=None,
    label_width=355,
):
    draw.text((x, y), title, fill=CHART_TEXT_COLOR, font=title_font)
    plot_top = y + 55
    plot_bottom = y + height - 50
    plot_left = x + label_width
    plot_right = x + width - 18
    plot_width = plot_right - plot_left

    if not values:
        draw.text(
            (x + 12, plot_top + 24),
            "No numeric results available",
            fill=CHART_MUTED_COLOR,
            font=font,
        )
        return

    maximum = max(value for _, value in values)
    scale_max = (
        max(threshold * 1.1, maximum * 1.15)
        if threshold is not None
        else max(maximum * 1.15, 0.01)
    )
    for tick in range(6):
        x_tick = plot_left + plot_width * tick / 5
        draw.line(
            (x_tick, plot_top, x_tick, plot_bottom),
            fill=CHART_GRID_COLOR,
            width=1,
        )
        draw.text(
            (x_tick - 12, plot_bottom + 5),
            _format_quantity(scale_max * tick / 5),
            fill=CHART_AXIS_COLOR,
            font=font,
        )

    if threshold is not None:
        threshold_x = plot_left + plot_width * threshold / scale_max
        for y_line in range(plot_top, plot_bottom, 12):
            draw.line(
                (threshold_x, y_line, threshold_x, min(y_line + 7, plot_bottom)),
                fill=UTILIZATION_THRESHOLD_COLOR,
                width=2,
            )
        draw.text(
            (min(threshold_x + 4, plot_right - 50), plot_top),
            f"UR = {threshold:g}",
            fill=UTILIZATION_THRESHOLD_COLOR,
            font=font,
        )

    row_height = max(34, (plot_bottom - plot_top) // len(values))
    for index, (label, value) in enumerate(values):
        row_y = plot_top + index * row_height + 5
        text = str(label)
        while text and draw.textlength(text, font=font) > label_width - 12:
            text = text[:-4] + "..."
        draw.text((x, row_y), text, fill=CHART_TEXT_COLOR, font=font)
        bar_right = plot_left + plot_width * value / scale_max
        draw.rectangle(
            (plot_left, row_y, max(plot_left + 1, bar_right), row_y + 18),
            fill=OSDAG_GREEN,
        )
        value_label = f"{value:.3f}" if threshold is not None else _format_quantity(value)
        draw.text(
            (min(bar_right + 5, plot_right - 45), row_y),
            value_label,
            fill=CHART_TEXT_COLOR,
            font=font,
        )


def _utilization_label_lines(label):
    text = str(label)
    if " (" in text and text.endswith(")"):
        member, action = text.rsplit(" (", 1)
        member_parts = member.split()
        if len(member_parts) > 1:
            return (
                member_parts[0],
                member_parts[1].capitalize(),
                action[:-1].capitalize(),
            )
    parts = text.split()
    if len(parts) > 1:
        first = {"bot": "Bottom", "top": "Top"}.get(parts[0].lower(), parts[0])
        last = parts[-1].upper() if parts[-1].lower() in {"uls", "sls"} else parts[-1]
        return first, last
    return (text,)


def _draw_utilization_panel(
    draw,
    font,
    small_font,
    title_font,
    x,
    y,
    width,
    height,
    title,
    values,
    threshold,
):
    draw.text((x, y), title, fill=CHART_TEXT_COLOR, font=title_font)
    plot_top = y + 60
    plot_bottom = y + height - 120
    plot_left = x + 70
    plot_right = x + width - 18
    plot_height = plot_bottom - plot_top

    if not values:
        draw.text(
            (plot_left, plot_top + 24),
            "No numeric results available",
            fill=CHART_MUTED_COLOR,
            font=font,
        )
        return

    maximum = max(value for _, value in values)
    scale_max = max(threshold * 1.1, maximum * 1.15, 0.01)
    for tick in range(6):
        y_tick = plot_bottom - plot_height * tick / 5
        draw.line(
            (plot_left, y_tick, plot_right, y_tick),
            fill=CHART_GRID_COLOR,
            width=1,
        )
        draw.text(
            (x + 8, y_tick - 12),
            f"{scale_max * tick / 5:.2g}",
            fill=CHART_AXIS_COLOR,
            font=small_font,
        )

    threshold_y = plot_bottom - plot_height * threshold / scale_max
    for x_line in range(plot_left, plot_right, 16):
        draw.line(
            (x_line, threshold_y, min(x_line + 9, plot_right), threshold_y),
            fill=UTILIZATION_THRESHOLD_COLOR,
            width=3,
        )
    draw.text(
        (plot_right - 130, max(plot_top, threshold_y - 28)),
        f"UR = {threshold:g}",
        fill=UTILIZATION_THRESHOLD_COLOR,
        font=small_font,
    )

    slot_width = (plot_right - plot_left) / len(values)
    bar_width = min(68, max(16, slot_width * 0.58))

    font_dir = Path(find_spec("matplotlib").origin).parent / "mpl-data" / "fonts" / "ttf"

    # Scale label font to fit slot width and avoid overlaps
    max_line_len = 0.0
    for label, _ in values:
        for line in _utilization_label_lines(label):
            max_line_len = max(max_line_len, draw.textlength(line, font=small_font))

    if max_line_len > (slot_width - 8):
        scale = min(1.0, (slot_width - 10) / max_line_len)
        eff_label_size = max(14, int(28 * scale))
        try:
            lbl_font = ImageFont.truetype(str(font_dir / "DejaVuSans.ttf"), eff_label_size)
        except Exception:
            lbl_font = small_font
    else:
        eff_label_size = 28
        lbl_font = small_font

    line_height = int(eff_label_size * 1.25)

    # Scale value label font if slots are narrow
    val_size = min(28, max(16, int(slot_width * 0.38)))
    if val_size < 28:
        try:
            val_font = ImageFont.truetype(str(font_dir / "DejaVuSans.ttf"), val_size)
        except Exception:
            val_font = small_font
    else:
        val_font = small_font

    for index, (label, value) in enumerate(values):
        center_x = plot_left + slot_width * (index + 0.5)
        bar_top = plot_bottom - plot_height * value / scale_max
        draw.rectangle(
            (
                center_x - bar_width / 2,
                bar_top,
                center_x + bar_width / 2,
                plot_bottom,
            ),
            fill=OSDAG_GREEN,
        )
        value_label = f"{value:.3f}"
        value_width = draw.textlength(value_label, font=val_font)
        if bar_top - val_size - 6 < plot_top:
            val_y = bar_top + 4
            val_fill = "#ffffff"
        else:
            val_y = bar_top - val_size - 4
            val_fill = CHART_TEXT_COLOR

        draw.text(
            (center_x - value_width / 2, val_y),
            value_label,
            fill=val_fill,
            font=val_font,
        )
        for line_index, line in enumerate(_utilization_label_lines(label)):
            text_width = draw.textlength(line, font=lbl_font)
            draw.text(
                (center_x - text_width / 2, plot_bottom + 8 + line_index * line_height),
                line,
                fill=CHART_TEXT_COLOR,
                font=lbl_font,
            )


def _chart_bytes(image):
    stream = BytesIO()
    image.save(stream, format="PNG", dpi=(300, 300))
    return stream.getvalue()


def utilization_ratio_chart(output_dict):
    """Render UR bars for available design results; omit unavailable values."""
    series = utilization_ratio_series(output_dict)
    if not any(series.values()):
        return None

    panels = list(series.items())
    image, draw, font, small_font, title_font, panel_width, panel_height = _chart_canvas(
        "Design Utilization Ratios",
        panels,
        columns=1,
        panel_width=1700,
        fixed_panel_height=UTILIZATION_CHART_PANEL_HEIGHT,
    )
    for index, (title, values) in enumerate(panels):
        x = 35
        y = 75 + index * (panel_height + 10)
        _draw_utilization_panel(
            draw,
            font,
            small_font,
            title_font,
            x,
            y,
            panel_width,
            panel_height,
            title,
            values,
            threshold=UTILIZATION_THRESHOLD,
        )
    return _chart_bytes(image)


def material_quantity_chart(quantities):
    """Render volume and weight from the existing Chapter 7 BOM results."""
    series = material_quantity_series(quantities)
    if not any(series.values()):
        return None

    panels = list(series.items())
    image, draw, font, small_font, title_font, panel_width, panel_height = _chart_canvas(
        "Material Take-off Quantities", panels, columns=1, panel_width=1700
    )
    for index, (title, values) in enumerate(panels):
        x = 35
        y = 75 + index * (panel_height + 10)
        _draw_panel(
            draw,
            font,
            title_font,
            x,
            y,
            panel_width,
            panel_height,
            title,
            values,
            label_width=600,
        )
    return _chart_bytes(image)
