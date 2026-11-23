"""Shared LaTeX layout and typography settings for generated reports."""

PAGE_MARGIN_IN = 1
TABLE_COLUMN_PADDING_PT = 6
TABLE_ROW_STRETCH = 1.12
LONGTABLE_PRE_SKIP_PT = 0
LONGTABLE_POST_SKIP_PT = 6
TABLE_RULE_WIDTH_PT = 0.5
TABLE_EXTRA_ROW_HEIGHT_PT = 0.6
HEADER_HEIGHT_PT = 18
FOOTER_SKIP_PT = 36
OSDAG_GREEN = "#91B014"
UTILIZATION_THRESHOLD = 1.0
UTILIZATION_THRESHOLD_COLOR = "#d62728"
CHART_BACKGROUND_COLOR = "#ffffff"
CHART_TEXT_COLOR = "#222222"
CHART_MUTED_COLOR = "#666666"
CHART_AXIS_COLOR = "#555555"
CHART_GRID_COLOR = "#dddddd"
CHART_FONT_SIZE = 32
CHART_TITLE_FONT_SIZE = 38
CHART_SMALL_FONT_SIZE = 28
UTILIZATION_CHART_PANEL_HEIGHT = 430


def report_styles(project_name, job_number, report_date, report_version):
    """Return shared page, table, and footer formatting commands."""
    return r"""
\numberwithin{table}{chapter}
\numberwithin{figure}{chapter}
\setlength{\tabcolsep}{""" + str(TABLE_COLUMN_PADDING_PT) + r"""pt}
\renewcommand{\arraystretch}{""" + str(TABLE_ROW_STRETCH) + r"""}
\setlength{\LTpre}{""" + str(LONGTABLE_PRE_SKIP_PT) + r"""pt}
\setlength{\LTpost}{""" + str(LONGTABLE_POST_SKIP_PT) + r"""pt}
\setlength{\arrayrulewidth}{""" + str(TABLE_RULE_WIDTH_PT) + r"""pt}
\setlength{\extrarowheight}{""" + str(TABLE_EXTRA_ROW_HEIGHT_PT) + r"""pt}
\setlength{\headheight}{""" + str(HEADER_HEIGHT_PT) + r"""pt}
\setlength{\footskip}{""" + str(FOOTER_SKIP_PT) + r"""pt}

\BeforeBeginEnvironment{table}{\needspace{5\baselineskip}}
\BeforeBeginEnvironment{longtable}{\needspace{5\baselineskip}}

\definecolor{osdagGreen}{HTML}{""" + OSDAG_GREEN.lstrip("#") + r"""}
\newbool{hasSDonPage}
\boolfalse{hasSDonPage}
\newcommand{\markSD}{\global\booltrue{hasSDonPage}}
\newcommand{\ReportFooterLeft}{%
  \parbox[b]{0.70\textwidth}{%
    \ifbool{hasSDonPage}{\footnotesize\textit{* Software default value}\\}{}%
    \footnotesize Osdag $|$ FOSSEE $|$ Indian Institute of Technology Bombay}}

\fancypagestyle{main}{
  \fancyhf{}
  \fancyhead[L]{""" + project_name + r""" $|$ """ + job_number + r"""}
  \fancyhead[R]{""" + report_date + r""" $|$ """ + report_version + r"""}
  \fancyfoot[L]{\ReportFooterLeft}
  \fancyfoot[R]{Page \thepage\ of \pageref{LastPage}}
  \renewcommand{\headrule}{\color{osdagGreen}\hrule width\headwidth height 1pt \vspace{2pt}}
  \renewcommand{\footrule}{\color{osdagGreen}\hrule width\headwidth height 1pt}
}
\fancypagestyle{plain}{
  \fancyhf{}
  \fancyhead[L]{""" + project_name + r""" $|$ """ + job_number + r"""}
  \fancyhead[R]{""" + report_date + r""" $|$ """ + report_version + r"""}
  \fancyfoot[L]{\ReportFooterLeft}
  \fancyfoot[R]{Page \thepage\ of \pageref{LastPage}}
  \renewcommand{\headrule}{\color{osdagGreen}\hrule width\headwidth height 1pt \vspace{2pt}}
  \renewcommand{\footrule}{\color{osdagGreen}\hrule width\headwidth height 1pt}
}
\fancypagestyle{firstpage}{
  \fancyhf{}
  \renewcommand{\headrule}{}
  \fancyfoot[L]{\footnotesize Osdag $|$ FOSSEE $|$ Indian Institute of Technology Bombay}
  \fancyfoot[R]{Page \thepage\ of \pageref{LastPage}}
  \renewcommand{\footrule}{\color{osdagGreen}\hrule width\headwidth height 1pt}
}
\pagestyle{main}
\setstretch{1.15}

\newcommand{\placeholder}[1]{\textit{\textless #1\textgreater}}
\newcommand{\todo}[1]{\colorbox{yellow}{TODO: #1}}
\newcolumntype{L}[1]{>{\raggedright\arraybackslash}p{#1}}
\newcolumntype{C}[1]{>{\centering\arraybackslash}p{#1}}
\newcolumntype{R}[1]{>{\raggedleft\arraybackslash}p{#1}}
\newcommand{\sdstar}{\textsuperscript{*}}
\renewcommand{\sdstar}{\textsuperscript{*}\markSD{}}
\AddToHook{shipout/before}{\global\boolfalse{hasSDonPage}}
"""


def toc_styles():
    """Return shared chapter and table-of-contents heading styles."""
    return r"""
\titleformat{\chapter}[block]
  {\normalfont\Large\bfseries\centering}{\thechapter}{1em}{}
\titlespacing*{\chapter}{0pt}{0pt}{10pt}
\setcounter{tocdepth}{2}
\titlecontents{chapter}[1.5em]
  {\normalfont\vspace{2pt}}
  {\contentslabel{1.5em}}
  {\hspace*{-1.5em}}
  {\hfill\contentspage}
\titlecontents{section}[3.8em]
  {\normalfont}
  {\contentslabel{2.3em}}
  {\hspace*{-2.3em}}
  {\hfill\contentspage}
\titlecontents{subsection}[7.0em]
  {\normalfont}
  {\contentslabel{3.2em}}
  {\hspace*{-3.2em}}
  {\hfill\contentspage}
"""
