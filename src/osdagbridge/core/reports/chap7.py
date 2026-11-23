from pylatex import LongTable, NoEscape


_BILL_OF_MATERIALS = (
    ("1", "Structural Steel (IS 2062) for Girders", "steel_girders"),
    ("2(a)", "Cross Bracing - Top Chord", "bracing_top"),
    ("2(b)", "Cross Bracing - Bottom Chord", "bracing_bot"),
    ("2(c)", "Cross Bracing - Diagonal Chord", "bracing_diag"),
    ("2(d)", "End Diaphragms", "end_diaphragms"),
    ("3", "Concrete (M40) for Deck Slab", "concrete_deck"),
    ("4", "Reinforcement Steel (Fe 500)", "rebar_deck"),
    ("5", "Shear Stud Connectors", "shear_studs"),
    ("6", "Crash Barrier", "crash_barrier"),
)

_HEADERS = (
    r"\textbf{S.N.}",
    r"\textbf{Item Description}",
    r"\textbf{Volume}",
    r"\textbf{Quantity}",
    r"\textbf{Total Volume}",
    r"\textbf{Weight (MT)}",
    r"\textbf{Total Weight (MT)}",
)

_TABLE_SPEC = (
    "|C{1.0cm}|L{3.8cm}|C{2.6cm}|C{1.8cm}|C{1.8cm}|C{1.8cm}|C{1.8cm}|"
)


def _cell(value):
    return NoEscape(str(value))


def _material_table(input_dict):
    table = LongTable(_TABLE_SPEC, width=len(_HEADERS), row_height=1.12)
    header = [_cell(value) for value in _HEADERS]
    table.add_hline()
    table.add_row(header, escape=False)
    table.add_hline()
    table.append(NoEscape(r"\endfirsthead"))
    table.add_row(header, escape=False)
    table.add_hline()
    table.end_table_header()

    for number, description, prefix in _BILL_OF_MATERIALS:
        table.add_row(
            [
                _cell(number),
                _cell(description),
                _cell(input_dict.get(f"{prefix}_vol_formula", "N.A.")),
                _cell(input_dict.get(f"{prefix}_qty", "N.A.")),
                _cell(input_dict.get(f"{prefix}_vol_total", "N.A.")),
                _cell(input_dict.get(f"{prefix}_wt_single", "N.A.")),
                _cell(input_dict.get(f"{prefix}_wt_total", "N.A.")),
            ],
            escape=False,
        )
        table.add_hline()
    return table.dumps()


def ch7_quantities(input_dict, figure_paths=None):
    chart_path = (figure_paths or {}).get("material_quantities")
    chart = ""
    if chart_path:
        chart = (
            r"""
\begin{figure}[H]
\centering
\includegraphics[width=\textwidth]{""" + chart_path + r"""}
\caption{Material volumes and weights from the Chapter 7 bill of materials.}
\label{fig:material-quantities}
\end{figure}
\noindent\textit{Note: Material volumes ($\text{m}^3$) and weights ($\text{MT}$) are plotted on separate independent scales. Items with unavailable takeoff data (End Diaphragms and Reinforcement Steel, marked N.A. in Table 7.1) are excluded from numerical plotting.}
"""
        )

    return r"""
\chapter{Material Take-off \& Quantity Summary}
\label{ch:material-takeoff}

""" + chart + r"""
\noindent\textbf{Table 7.1  Bill of Materials (Steel, Concrete, and Reinforcement Quantities)}

\begingroup
\setlength{\tabcolsep}{3.5pt}
""" + _material_table(input_dict) + r"""
\endgroup
"""
