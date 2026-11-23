# OsdagBridge Report Generator — Technical Changes

Validation run: 2026-11-21 using `sample_bridge.osi`.

## Implemented changes

- **Chapter 2 dimensions:** The design pipeline stores girder dimensions in metres, but Table 2.7 labels the values in millimetres. The report now converts the source values for display without hardcoding replacements. The generated sample shows 1670 mm depth, 10 mm web thickness, 510 mm flange widths, and 22 mm flange thicknesses.
- **Chapter 3 live loads:** Separate vehicle and footway tables are retained and populated from available design/UI inputs. Boolean and string checkbox values are handled, lane counts such as `"2.0"` are parsed when integral, and the `1 + IM` value is labelled as an impact load factor. Braking force accumulators are initialized for one- and two-lane calculations. This sample has no footpath or lane-count input; those values are therefore unavailable. Centrifugal-force calculation/input is not implemented.
- **Chapter 4 analysis results:** Table 4.2 is populated from actual beam-end shear results (`Vy_i`/`Vy_j`) because this OSPGrillage dataset contains no nodal `reactions` variable. The extraction now applies the element-end-force sign convention at both supports and converts N to kN; a focused test verifies upward-positive values and the aggregate summary. The final sample reports symmetric positive reactions for dead-load cases and negative reactions for uplift/seismic cases. Direct nodal reaction-to-support verification remains unavailable and the sign convention should still receive engineering review. Bending-moment, shear, and deflection figures are sourced from generated analysis results when available.
- **Executive summary and Chapter 5:** Component status now reflects available design results rather than fixed “pass” claims. The sample correctly reports the overall design as **Fail**, including the fatigue normal-stress and intermediate-stiffener checks. Utilization-ratio charts use actual design results and retain the red dashed UR = 1.0 threshold. Missing end-diaphragm numerical design results are identified as unavailable.
- **Chapter 6 drawings:** The desktop report path captures generated CAD figures and passes image bytes to the report generator. The girder side-view capture no longer substitutes a fixed 30 m span or default stiffener details when source inputs are missing. The final headless run supplied no CAD captures; Chapter 6 therefore shows explicit availability messages rather than invented drawings. The report did include the three generated analysis plots and data-backed charts.
- **Chapter 7 quantities:** Quantity charts use actual BOM values and improved number formatting. Concrete and steel quantities are shown where available. Whole-bridge reinforcement and end-diaphragm quantities remain `N.A.` because there is no complete reinforcement schedule or end-diaphragm quantity source; no estimates are substituted.
- **Shared styles and layout:** Existing centralized style configuration remains the source for page margins, typography, table spacing, headers, footers, and chart styling. Longtable continuation headers are present in the generated report.

## Modified source and test files

- `src/osdagbridge/core/boq/boq_generator.py`
- `src/osdagbridge/core/reports/chap2.py`
- `src/osdagbridge/core/reports/chap3.py`
- `src/osdagbridge/core/reports/chap4.py`
- `src/osdagbridge/core/reports/chap5.py`
- `src/osdagbridge/core/reports/chap6.py`
- `src/osdagbridge/core/reports/chap7.py`
- `src/osdagbridge/core/reports/charts.py`
- `src/osdagbridge/core/reports/executive_summary.py`
- `src/osdagbridge/core/reports/report_generator.py`
- `src/osdagbridge/core/reports/report_utils.py`
- `src/osdagbridge/core/reports/styles.py`
- `src/osdagbridge/core/utils/codes/irc6_2017.py`
- `src/osdagbridge/desktop/ui/docks/output_dock.py`
- `tests/unit/test_reports.py`

No structural design checks, fatigue demand/capacity calculations, or bridge geometry inputs were changed.

## Validation

- `tests/unit/test_reports.py`: **24 passed** (2.78 s), including the focused support-reaction sign/unit regression.
- `py_compile` on changed Python files: **passed**.
- The final report was regenerated through the application backend report workflow after the reaction correction; the runner exited with code 0 and produced `Report_After.pdf`.
- `Report_After.pdf` is PDF 1.7, ends with a valid `%%EOF`, and has **57 pages** (verified from its decoded PDF page objects). The generated TeX has 50 longtables with continuation-header commands and references the three generated analysis figures plus the utilization and material-quantity charts. The PDF contains 7 embedded image objects.
- The generated TeX contains 50 longtables with continuation-header commands. Table 2.7 shows the corrected dimensions. No literal unsupported `≤` character or placeholder-content invocation was found; an unused placeholder macro definition remains in the TeX preamble.
- The report run emitted approximately 30 non-fatal design/input warnings, primarily for absent optional loads and unavailable thermal cases. The final PDF compiled successfully; no separate final LaTeX log was retained to count TeX warnings.
- Validation was backend/report-pipeline only. The PDF was not visually inspected in a desktop viewer, so footer overlap and visual chart legibility are not claimed as GUI-verified. The desktop CAD-capture path was not exercised.

## Deliverables and limitations

- `Report_Before.pdf` is the pre-change `report_test_15.pdf` baseline.
- `Report_After.pdf` and `Report_After.tex` are the final generated report and source.
- `sample_bridge.osi` is the input used for the final run.
- The generated TeX references images staged in a temporary compilation directory. The PDF embeds those images, but the TeX is not independently recompilable after those temporary assets are removed.
- Actual Chapter 6 CAD views require figure bytes from the active desktop UI. The current final report has clear availability notices instead. End-diaphragm design results and quantities, plus a complete reinforcement takeoff, remain unavailable from this sample/model pipeline.
- Table 4.2 uses the girder-end-force-derived reaction summary with upward-positive signs. OSPGrillage did not export nodal reactions for this run, so direct node-to-support reaction verification remains an engineering follow-up.
- Manual completion: visually review the final PDF and GUI-generated CAD figures, confirm reaction sign conventions with the design basis, then commit/push the source and submit the PDFs and this document through the internship workflow.

## Review follow-up — report_test_16 (2026-11-21)

- Table 2.9 reports the input cross-bracing section, while Table 5.23 reports the optimized section used in design checks. These are different data stages, not a confirmed design-result mismatch. The report now labels the Table 2.9 field as **Input Section** and explains the distinction.
- For a single brace, the stored ID range repeats the same ID at both ends. The report now displays that ID once without changing input data.
- Material-chart quantities continue to use the BOM source fields; sub-unit chart labels now retain enough decimal places to show values such as 0.00149 without rounding them to 0.0015. Utilization labels are more descriptive and the small-chart font is larger.
- A blank report version now displays `Rev 0`. LaTeX compilation repeats until reference/list files stabilize, with an explicit failure if they do not stabilize within five passes.
- Focused validation: `tests/unit/test_reports.py` — **28 passed**; `py_compile` on changed report modules and tests — **passed**.
- `report_test_17.pdf` (966,050 bytes, PDF 1.7, valid EOF marker, 28 embedded image objects) was saved through the desktop report workflow. The running application had imported report modules before these edits, so this PDF may not include the follow-up changes. Its page count and visual CAD content were not verified; do not treat it as the final corrected submission PDF.
- Remaining: restart/reload the desktop application, regenerate the PDF once, then visually confirm the cover/page total, chart labels and values, and which genuine CAD captures are visible. Do not populate blank cover metadata with guessed values. The one-brace input-versus-optimized distinction is not a structural design defect.

## Review follow-up — report_test_18 investigation and fixes (2026-11-21)

- **Diagnosis:**
  - TeX source comparison between `report_test_17.tex` and `report_test_18.tex` confirmed that `report_test_18` was compiled from a completely empty payload (`inputs={}`, `output_dict={}`, `figure_data={}`).
  - Runtime verification with `sample_bridge.osi` demonstrated that `build_report_payload()` does not fail or throw unhandled exceptions when valid bridge inputs and design results are present.
  - Cause identified: In `src/osdagbridge/desktop/ui/template_page.py`, the File-menu action "Create Design Report" (`Alt+C`) directly invoked `open_report_dialog()` without arguments. Unlike the Output Dock report button (`OutputDock._on_report_clicked()`), `open_report_dialog()` did not verify that design had actually been executed (`input_dock.is_locked` and backend design results present), allowing report generation to proceed when the backend was uninitialized or prior to running design. It also bypassed the desktop CAD capture pipeline (`cad_generator=None`).
  - Secondary defect: In `src/osdagbridge/core/reports/report_generator.py`, `build_report_payload()` caught all exceptions and silently returned an empty `ReportPayload` (`inputs={}`, `output_dict={}`), masking errors and allowing blank reports to be compiled.
  - Secondary defect: In `src/osdagbridge/core/bridge_types/plate_girder/plategirderbridge.py`, `PlateGirderBridge.generate_design_report()` did not validate that `self.input_dict` or `self.output_dict` were populated before initiating report compilation.

- **Changes implemented:**
  - `src/osdagbridge/core/reports/report_generator.py`: `build_report_payload()` now explicitly validates `input_dict` and raises `ValueError` if empty; unexpected exceptions are logged and re-raised as `RuntimeError` rather than silently swallowed into an empty payload.
  - `src/osdagbridge/core/bridge_types/plate_girder/plategirderbridge.py`: `PlateGirderBridge.generate_design_report()` now validates `self.input_dict` and `self.output_dict`, raising `ValueError` if empty to prevent compilation from un-designed bridge states.
  - `src/osdagbridge/desktop/ui/template_page.py`:
    - File-menu "Create Design Report" (`Alt+C`) now routes through `OutputDock._on_report_clicked()` when available, ensuring design state is verified and CAD figures are captured.
    - `open_report_dialog()` verifies that `input_dock.is_locked` and backend design results are present, displaying a warning message box ("Please run the design first.") instead of proceeding with an uninitialized state.

- **Validation:**
  - Added 3 regression tests to `tests/unit/test_reports.py`:
    - `test_build_report_payload_rejects_empty_inputs`
    - `test_build_report_payload_propagates_exceptions_instead_of_silent_empty_payload`
    - `test_plate_girder_bridge_generate_design_report_rejects_empty_state`
  - Validation run: `py_compile` on changed modules — **passed**; `tests/unit/test_reports.py` — **31 passed** (5.16 s).
  - No new PDF was generated from an empty payload. A fresh GUI-captured PDF was not generated in this headless session.

## Review follow-up — report_test_21 verification and fixes (2026-11-21)

Baseline: `report_test_20.pdf`.
Final generated report: `report_test_21.pdf` (1,052,268 bytes, 61 physical pages / 60 numbered pages, 28 embedded images) and `report_test_21.tex`.

### 1. Figure 7.1 Material Chart vs. Table 7.1 Investigation & Fixes
- **BOM Unit Handling (`boq_generator.py`):** Crash barrier cross-sectional area (`KEY_CB_AREA = "geometry.crash_barrier.cross_section_area"`) in the GUI payload was already provided in square metres (`0.3023 m²`). The BOQ calculation assumed square millimetres and divided by $10^6$ again, resulting in near-zero quantities (`0.00 m³` and `0.00 MT`). `src/osdagbridge/core/boq/boq_generator.py` was updated to support both inputs (values $< 100$ treated as $\text{m}^2$; values $\ge 100$ divided by $10^6$). Table 7.1 now displays:
  - Crash barrier cross-sectional area: $0.30230\text{ m}^2 \times 30.00\text{ m} = 9.06900\text{ m}^3$
  - Quantity: 2
  - Total Volume: $18.14\text{ m}^3$
  - Weight: $23.11\text{ MT}$ (single), $46.22\text{ MT}$ (total)
- **Chart Panel Layout (`charts.py`):** In `src/osdagbridge/core/reports/charts.py`, `material_quantity_chart()` had a hardcoded vertical coordinate `y = 75` for both panels, causing the "Total weight (MT)" panel to completely overwrite the "Total volume (m³)" panel at identical coordinates. The vertical offset was corrected to `y = 75 + index * (panel_height + 10)`. Figure 7.1 now renders both sub-charts distinctly with accurate units ($\text{m}^3$ and $\text{MT}$).

### 2. Reinforcement and End-Diaphragm Quantities Investigation
- **End Diaphragms:** Inspected backend data structures. In the grillage analysis pipeline, `output_dict["end_diaphragm_design_results"]` is an empty dictionary (`{}`) with no member forces or detailed structural sizing. No bridge-wide end-diaphragm material quantity is calculated.
- **Reinforcement:** Deck slab design checks determine required steel areas at critical sections ($A_{st,min}$, crack control), but do not execute a bridge-wide detailing takeoff or bar bending schedule.
- **Reporting Decision:** Strictly complying with the requirement against inventing engineering data, rows `2(d) End Diaphragms` and `4 Reinforcement Steel (Fe 500)` in Table 7.1 remain explicitly `N.A.`. No fabricated or guessed quantities were introduced.

### 3. Transverse Slab Shear Result (Table 5.22)
- Table 5.22 previously queried girder check ID 16 (`_dcr_row({16})`), which is undefined in girder check IDs and rendered as `--- & --- & --- & ---`.
- The actual transverse slab shear results were located in `output_dict["design_results"]["shear_connectors"]` ($V_L = 82.84\text{ kN/m}$, $V_{Rd} = 999.28\text{ kN/m}$, $\text{UR} = 0.08$).
- Updated `src/osdagbridge/core/reports/chap5.py` to populate the `Transverse Shear (slab)` row in Table 5.22 with governing load combination `Basic ULS: 1.35DL + 1.5LL`, demand $82.84\text{ kN/m}$, capacity $999.28\text{ kN/m}$, and $\text{UR} = 0.08$.

### 4. Girder Side-View CAD Capture Integration (Figure 6.6)
- In `src/osdagbridge/desktop/ui/docks/output_dock.py`, `_capture_all_figures()` skipped rendering `stiffener_preview.png` because `_valid_preview_data()` only inspected `stiffener_by_member` (the UI dialog dictionary, only populated if the user manually opened the stiffener dialog).
- Added a robust fallback in `OutputDock._capture_all_figures()` to populate bearing and intermediate stiffener dimensions from `self._out` and `self._inputs` (`bearing_stiffener_spacing`, `no_bearing_stiffeners_each_end`, `intermediate_stiffener_spacing`, etc.).
- Figure 6.6 (`\label{fig:girder-side}`) now successfully integrates the actual CAD-rendered girder side elevation (`stiffener_preview.png`).

### 5. Cover Metadata & Page Structure Verification
- Verified cover metadata (project title, bridge type, span 30 m, carriageway width 7.5 m, design code IRC:112-2020 / IRC:24-2010, date, Rev 0).
- Preserved exact **61 physical pages / 60 numbered pages** structure matching the baseline.
- Note on CAD aspect ratio: Resizing/maximizing the application main window (`1920x1080`) before figure capture ensures wide aspect ratio ($1419\times 874$) for 3D views, preventing vertical overflow in the Executive Summary and maintaining the 61-page budget.

### 6. Design Status & Fatigue UR = 1.58 Preservation
- Structural design calculations, geometry, and fatigue capacity/demands were strictly preserved without modification.
- Governing check is Fatigue Normal Stress (Cl. 605) under `SLS_FREQUENT_1` with demand $145.86\text{ MPa}$, capacity $92.49\text{ MPa}$, $\text{UR} = 1.58$ ($1.577$), and status **FAIL**.
- Overall bridge design status is correctly reported as **Fail (Fatigue Normal Stress, Int.Stiff: Leg $\le$ H_limit)** across the Executive Summary, Table 5.21, and Table 5.22.


### 7. Validation & Deliverables
- **Unit Tests:** Added 3 tests in `tests/unit/test_reports.py`:
  - `test_crash_barrier_boq_supports_both_mm2_and_m2_units`
  - `test_material_quantity_chart_renders_both_volume_and_weight`
  - `test_table_522_includes_transverse_shear_result`
  - Test suite status: **34 passed** in 5.92s.
- **PDF Generation:** One final report was generated through the live desktop application workflow (`CustomWindow`, automated design execution on `sample_bridge.osi`, Output Dock report generation):
  - Output PDF: `report_test_21.pdf`
  - Output TeX: `report_test_21.tex`

## Review follow-up — Report_Final_Candidate_2 verification and fixes (2026-11-23)

Baseline comparison: `report_test_22.pdf`.
Final generated report: `Report_Final_Candidate_2.pdf` (1,043,089 bytes, 61 physical pages / 60 numbered pages, 23 embedded figure references) and `Report_Final_Candidate_2.tex`.

### 1. Root Cause of Empty Results in Report_Final_Candidate.pdf
- **Primary Exception (`designer.py`):** During stage 5 of the bridge design check in `src/osdagbridge/core/bridge_types/plate_girder/designer.py` (line 3444), `"stiffness_ratio": stiffness_ratio` was referenced. `stiffness_ratio` was defined in `extract_girder_demands()` but not in `run_design_check()`, raising an uncaught `NameError: name 'stiffness_ratio' is not defined`.
- **UI Error Cascade:** In `src/osdagbridge/desktop/ui/template_page.py`, `_DesignWorker` caught the exception and called `self._show_design_error(err_trace)`. This method automatically unlocked the input dock (`self.input_dock.toggle_lock(confirm=False)`).
- **Backend Memory Wipe:** Releasing the dock lock triggered `self.parent.backend.reset()`, which invoked `self.memory.release()`, setting `backend.output_dict` to an empty mapping `{}` and wiping all cached grillage results and CAD plots.
- **Premature Generation:** The previous candidate script forcibly re-locked the empty input dock without a successful design run and invoked `output_dock._on_report_clicked()`, resulting in a report with empty engineering results, blank demand tables, and placeholder CAD images.
- **Fix:** In `designer.py`, calculated `_stiffness_ratio = max(float(capacity.I_comp_short_mm4) / float(_sec.Iz_steel), 1.0) if float(_sec.Iz_steel) > 0 else 1.0` before constructing `design_results`, restoring successful completion of the full design solver.

### 2. Deflection Reconciliation Across Report Chapters
Investigated the conflicting deflection values:
- **Root Cause:** Table 4.3 and Table 5.9 previously reported raw unreduced bare-steel grillage analysis deflections (LL $\approx 19.39\text{ mm}$, Total $\approx 51.23\text{ mm}$ exceeding $L/600 = 50.0\text{ mm}$), while Table 5.29 / Table 5.22 reported composite transformed section deflections scaled by the modular ratio $I_{comp}/I_{steel} \approx 2.24$ (LL $\approx 8.66\text{ mm} \le L/800$, Total $= 22.87\text{ mm} \le L/600$, $\text{UR} = 0.46$, PASS).
- **Resolution:**
  - Standardized Table 4.3 to report composite deflections (Live Load: $8.655\text{ mm} \le 37.5\text{ mm}$ PASS; Total Load: $22.870\text{ mm} \le 50.0\text{ mm}$ PASS) matching the actual IRC 22 composite girder behavior and Table 5.22.
  - Added an explanatory note in Table 4.3 citing the composite modular stiffness reduction factor ($I_{comp}/I_{steel} = 2.24$) and explicitly detailing the unreduced bare-steel grillage analysis deflections ($19.385\text{ mm}$ LL and $51.225\text{ mm}$ total).
  - Ensured Table 5.10 (Serviceability Deflection Checks) displays consistent composite deflections across G1 to G4 ($9.60\text{--}9.63\text{ mm}$ LL PASS, $22.77\text{--}22.87\text{ mm}$ Total PASS).

### 3. Utilization Ratio Chart and Material Take-Off Verification
- **Utilization Chart (Figure 5.1):** Preserved dynamic label scaling, line height, collision prevention, and the red dashed threshold line at $\text{UR} = 1.0$.
- **Chapter 7 Material Chart (Figure 7.1) & Table 7.1:** Maintained separate independent scales for volume ($\text{m}^3$) and weight ($\text{MT}$). Retained explicit disclosure that end-diaphragms and reinforcement quantities remain `N.A.` due to unavailable detailing data in the solver.

### 4. CAD Capture Preservation
- Off-screen captures from live desktop widgets were preserved via the Output Dock workflow:
  - 3D bridge view (`girder_3d.png`)
  - Top view (`girder_top.png`)
  - Cross section (`cross_section.png` and `section_preview.png`)
  - Stiffener preview / side view (`stiffener_preview.png`)
  - Cross bracing layout and chord sections (`cb_diagram.png`, `cb_bracing.png`, `cb_top_chord.png`, `cb_bottom_chord.png`)
  - End diaphragm layout and chord sections (`ed_diagram.png`, `ed_bracing.png`, `ed_top_chord.png`, `ed_bottom_chord.png`)
  - Analysis demand envelopes (`bm_envelope.png`, `sf_envelope.png`, `defl_ll.png`)
- Total embedded graphics: 23 `\includegraphics` references (identical to baseline `report_test_22.tex`).

### 5. Overall Design Status Preservation
- Genuine design failure is strictly maintained: **Fail (Fatigue Normal Stress, Int.Stiff: Leg $\le$ H_limit)** with governing check Fatigue Normal Stress ($\text{UR} = 1.58$, demand $145.86\text{ MPa}$, allowable $92.49\text{ MPa}$).
- No engineering calculations were altered to artificially pass failing checks.

### 6. Validation and Test Results
- Added 2 new focused regression tests in `tests/unit/test_reports.py`:
  - `test_deflections_cache_and_table_43_reconciliation`: Verifies composite live load and total load deflection reporting with unreduced grillage footnotes.
  - `test_designer_stiffness_ratio_in_design_results`: Verifies `stiffness_ratio` is correctly computed and mapped in `design_results`.
- Total test suite: **36 passed** in 16.56s.
- Clean PDF generation via the desktop application workflow: `Report_Final_Candidate_2.pdf` (61 physical pages / 60 numbered pages).

