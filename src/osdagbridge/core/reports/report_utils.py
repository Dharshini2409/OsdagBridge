import re

from osdagbridge.core.utils.common import (
    KEY_MP_GD_MEMBER_ID,
    KEY_MP_GD_SELECT_GIRDER,
    KEY_MP_GIRDER_DEPTH,
    KEY_TS_NO_OF_GIRDERS
)


_LONGTABLE_PATTERN = re.compile(
    r"\\begin\{longtable\}.*?\\end\{longtable\}", re.DOTALL
)


def repeat_longtable_headers(latex):
    """Add the first-page column header to each longtable continuation head."""
    def repeat_header(match):
        table = match.group(0)
        first_head = table.find(r"\endfirsthead")
        end_head = table.find(r"\endhead")
        if (first_head < 0) != (end_head < 0):
            raise ValueError("Longtable has an incomplete continuation header.")

        header_limit = first_head if first_head >= 0 else len(table)
        first_rule = table.find(r"\hline")
        second_rule = table.find(r"\hline", first_rule + len(r"\hline"))
        if first_rule < 0 or second_rule < 0 or second_rule >= header_limit:
            raise ValueError("Longtable is missing a recognizable column header.")

        header = table[first_rule:second_rule + len(r"\hline")]
        if not re.search(r"\\textbf\s*\{", header):
            raise ValueError("Longtable column header must contain bold labels.")

        if first_head >= 0:
            repeated_header = table[first_head + len(r"\endfirsthead"):end_head]
            if re.search(r"\\textbf\s*\{", repeated_header):
                return table
            insertion = first_head + len(r"\endfirsthead")
            return (
                table[:insertion]
                + "\n\n"
                + header
                + "\n\n"
                + table[insertion:]
            )

        insertion = second_rule + len(r"\hline")
        return (
            table[:insertion]
            + "\n\\endfirsthead\n\n"
            + header
            + "\n\\endhead\n"
            + table[insertion:]
        )

    return _LONGTABLE_PATTERN.sub(repeat_header, latex)


def _tex(value):
    """Escape a Python value for safe LaTeX embedding."""
    s = str(value) if value is not None else ''
    if not s:
        return r''
    # Normalise non-ASCII glyphs from section designations (e.g. "∠ 100 ⅹ 100ⅹ 10")
    # that pdflatex cannot render.
    for uni, ascii_ in [('∠', 'L'), ('ⅹ', 'x'), ('×', 'x')]:
        s = s.replace(uni, ascii_)
    s = s.replace('\\', r'\textbackslash{}')
    for ch, esc in [('&', r'\&'), ('%', r'\%'), ('$', r'\$'), ('#', r'\#'),
                    ('{', r'\{'), ('}', r'\}'),          
                    ('_', r'\_\allowbreak{}'),            
                    ('~', r'\textasciitilde{}'), ('^', r'\^{}')]:
        s = s.replace(ch, esc)
    s = s.replace(':', r':\allowbreak{}')
    s = s.replace('≤', r'\ensuremath{\leq}')
    return s


def _render_value(source_dict, key, unit=""):
    val = source_dict.get(key)
    if val in ("", None):
        return ""
    return _tex(val) + unit


def get_girder_entries(input_dict):
    """
    Retrieve all girder labels and member IDs from backend keys.

    Usage Example:
    --------------------------
    girder_entries = get_girder_entries(bridge.input_dict)
    
    # 1. Fallback handling (if backend hasn't populated keys yet)
    if not girder_entries:
        n = int(bridge.input_dict.get(KEY_TS_NO_OF_GIRDERS, 1))
        girder_entries = [(f"Girder {i}", f"M1") for i in range(1, n + 1)]
        
    # 2. Get total number of girders safely
    n_girders = len(girder_entries)
    
    # 3. Iterate over the girders to build table rows
    for lbl, mid in girder_entries:
        # lbl will be e.g., "G1", mid will be e.g., "G1M1"
        # Access girder specific keys dynamically:
        # val = input_dict.get(f"{KEY_MP_GIRDER_DEPTH}.{lbl}.{mid}")
        pass

    Returns:
        List[Tuple[str, str]]
    """
    n = int(input_dict.get(KEY_TS_NO_OF_GIRDERS, 0))

    entries = []

    for i in range(1, n + 1):
        entries.append(
            (
                input_dict.get(f"{KEY_MP_GD_SELECT_GIRDER}.G{i}", ""),
                input_dict.get(f"{KEY_MP_GD_MEMBER_ID}.G{i}.M1", ""),
            )
        )

    return entries


def _fig_or_placeholder(path, caption, width=r'0.9\textwidth'):
    """Embed a figure or clearly identify the missing source image.
    path is the relative path as pdflatex will see it (e.g. 'assets/plan.png').
    """
    if path:
        p = path.replace('\\', '/')
        return (r'\begin{figure}[H]' + '\n'
                r'\centering' + '\n'
                r'\includegraphics[width=' + width + ']{' + p + '}\n'
                r'\caption*{' + caption + '}\n'
                r'\end{figure}')
    return (r'\begin{figure}[H]' + '\n'
            r'\centering' + '\n'
            r'\fbox{\parbox{0.97\textwidth}{' + '\n'
            r'\textit{Source image unavailable for this report: ' + caption + r'}' + '\n'
            r'}}' + '\n'
            r'\caption*{' + caption + '}\n'
            r'\end{figure}')

def _fig_embed(path, caption, width=r'\textwidth', height=None):
    """Embed a real figure or clearly identify the missing source image."""
    if path:
        p = path.replace('\\', '/')
        opts = 'width=' + width
        if height:
            opts += ',height=' + height + ',keepaspectratio'
        return (r'\begin{figure}[H]' + '\n'
                r'\vspace{-0.5em}' + '\n'
                r'\centering' + '\n'
                r'\includegraphics[' + opts + ']{' + p + '}\n'
                r'\vspace{0.5em}' + '\n'
                r'\caption*{\small ' + caption + '}\n'
                r'\vspace{-0.5em}' + '\n'
                r'\end{figure}')
    return (r'\noindent\fbox{\parbox{0.97\textwidth}{' + '\n'
            r'\textit{Analysis figure unavailable for this report: ' + caption + r'}' + '\n'
            r'}}')


