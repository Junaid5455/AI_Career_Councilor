"""
report_generator.py
===================
Three fully independent report generation pipelines:
  1. generate_career_report()      — personalised student report (multi-call)
  2. generate_field_scope_report() — general single-field overview (single call)
  3. generate_field_comparison_report() — side-by-side field comparison (single call)

Plus: all PDF export functions for each pipeline, using reportlab.
"""

import os
import re

from datetime import datetime

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors

from config import (
    MAX_RETRIES, REPORT_DIR,
    FIELD_SCOPE_PROMPT_FILE_PATH, FIELD_COMPARISON_PROMPT_FILE_PATH,
)
from api_client import call_api_for_section, call_with_retry, extract_response_text
from prompts import (
    build_system_prompt, build_user_prompt,
    build_field_scope_system_prompt, build_field_comparison_system_prompt,
)
from storage import ensure_reports_dir


# ============================================================================
# SECTION METADATA
# ============================================================================

SECTION_TITLES = {
    1: "Top 5 Career Recommendations",
    2: "Mathematics-Based Additional Suggestions",
    3: "Communication-Based Additional Suggestions",
    4: "Affordable Study Options",
    5: "Final Advice & Key Takeaways",
}
_CONDITIONAL_SECTIONS = {2, 3, 4}

FIELD_SCOPE_SECTION_TITLES = {
    1: "Field Overview",
    2: "Field Attributes",
    3: "Suggested Degrees & Entry Paths",
    4: "Required Subjects & Skill Roadmap",
    5: "Top Universities Worldwide",
    6: "Career Roles & Industry Demand",
    7: "Pros, Cons & AI Automation Risk",
    8: "Final Verdict & Who Should Consider This Field",
}

FIELD_COMPARISON_SECTION_TITLES = {
    1: "Fields at a Glance",
    2: "Head-to-Head Attribute Comparison",
    3: "Suggested Degrees & Entry Paths",
    4: "Required Subjects & Skill Roadmap",
    5: "Top Universities in Your Country",
    6: "Career Roles & Industry Demand",
    7: "Pros, Cons & AI Automation Risk",
    8: "Final Verdict — Who Should Choose Which Field",
}


# ============================================================================
# SECTION PARSERS
# ============================================================================

def parse_sections(report_text):
    """Splits the main career report into {section_number: text} (sections 1-5)."""
    import re as _re

    sections = {}
    if not report_text:
        return sections

    SECTION_KEYWORDS = {
        1: r'top\s+5\s+career|career\s+recommend',
        2: r'mathematics[- ]based|math[- ]based',
        3: r'communication[- ]based',
        4: r'affordable\s+study|affordable\s+options',
        5: r'final\s+advice|key\s+takeaway',
    }
    combined_parts = [
        rf'(?P<sec{num}>\*{{0,2}}\s*{num}\s*[\.\)]\s*\*{{0,2}}\s*(?:{kw})[^\n]*)'
        for num, kw in SECTION_KEYWORDS.items()
    ]
    master_pattern = _re.compile(
        r'^\s*(' + '|'.join(combined_parts) + r')\s*$',
        _re.MULTILINE | _re.IGNORECASE,
    )
    all_matches = list(master_pattern.finditer(report_text))

    def _get_num(m):
        for n in range(1, 6):
            if m.group(f'sec{n}') is not None:
                return n
        return None

    accepted = []
    last_num = 0
    for match in all_matches:
        num = _get_num(match)
        if num is not None and num > last_num:
            accepted.append((num, match))
            last_num = num

    for i, (num, match) in enumerate(accepted):
        start = match.end()
        end   = accepted[i + 1][1].start() if i + 1 < len(accepted) else len(report_text)
        sections[num] = report_text[start:end].strip()

    return sections


def _parse_8_sections(report_text):
    """Generic parser for any 8-section numbered report (field scope / comparison)."""
    import re as _re

    sections = {}
    if not report_text:
        return sections

    pattern = _re.compile(
        r'^\s*\*{0,2}\s*([1-8])\s*[\.\)]\s*\*{0,2}\s*[^\n]*$',
        _re.MULTILINE,
    )
    all_matches = list(pattern.finditer(report_text))

    accepted = []
    last_num = 0
    for match in all_matches:
        num = int(match.group(1))
        if num > last_num:
            accepted.append((num, match))
            last_num = num

    for i, (num, match) in enumerate(accepted):
        start = match.end()
        end   = accepted[i + 1][1].start() if i + 1 < len(accepted) else len(report_text)
        sections[num] = report_text[start:end].strip()

    return sections


def parse_field_scope_sections(report_text):
    """Splits a Field Scope report into {1..8: text}."""
    return _parse_8_sections(report_text)


def parse_field_comparison_sections(report_text):
    """Splits a Field Comparison report into {1..8: text}."""
    return _parse_8_sections(report_text)


def get_section_text(sections, number, fallback="Data not provided."):
    """Returns section text, or fallback if missing/empty."""
    text = sections.get(number, "").strip()
    return text if text else fallback


# ============================================================================
# CAREER REPORT GENERATOR  (multi-call, one per section/recommendation)
# ============================================================================

def generate_career_report(profile):
    """Assembles the full personalised report via multiple focused API calls.

    Splits generation into:
      - Report header             (1 call)
      - Section 1 introduction    (1 call)
      - Recommendation #1–#5      (5 calls)
      - Section 2: Maths          (1 call, conditional)
      - Section 3: Communication  (1 call, conditional)
      - Section 4: Affordable     (1 call, conditional)
      - Section 5: Final Advice   (1 call)
    """
    system_prompt = build_system_prompt()
    user_text     = build_user_prompt(profile)

    math_strong   = bool(profile.get("math_is_favourite")) and bool(profile.get("math_career_ok"))
    comm_skills   = profile.get("communication_skills") or {}
    comm_high     = bool(comm_skills) and (sum(comm_skills.values()) / len(comm_skills)) >= 7
    financial_need = profile.get("financial_status") in ("Need Scholarship", "Tight Budget")

    parts = []

    # Header
    parts.append(call_api_for_section(
        system_prompt, user_text,
        "Generate ONLY the report header block for this student. "
        "Output exactly:\n"
        "📋 AI CAREER COUNSELLING REPORT\n"
        "Student Name: [Name]  Date: [Current Date]  Report Version: 1.0\n"
        "Nothing else.",
        "Report Header",
    ))

    # Section 1 introduction
    parts.append(call_api_for_section(
        system_prompt, user_text,
        "Generate ONLY the Section 1 header and the introductory paragraph "
        "(Plans A through E listing). "
        "Do NOT generate any recommendation yet. "
        "Output format must start exactly with:\n"
        "1. Top 5 Career Recommendations\n"
        "Then the paragraph describing Plans A-E.",
        "Section 1 Introduction",
    ))

    # Recommendations 1-5
    plan_labels = [
        "A – Best Match", "B – Second Best Match",
        "C – Third Best Match", "D – Fourth Best Match", "E – Fifth Best Match",
    ]
    for rec_num in range(1, 6):
        parts.append(call_api_for_section(
            system_prompt, user_text,
            f"Generate ONLY Recommendation #{rec_num} (Plan {plan_labels[rec_num - 1]}) "
            f"for Section 1 of the career counselling report.\n\n"
            f"CRITICAL RULES FOR THIS OUTPUT:\n"
            f"1. Do NOT write 'After analyzing the information...' or list Plans A through E "
            f"— that introductory paragraph has ALREADY been written once and must NOT be repeated here.\n"
            f"2. Do NOT write any other recommendation number except #{rec_num}.\n"
            f"3. Start your output IMMEDIATELY with: Recommendation #{rec_num}: [Career Name]\n\n"
            f"You must output the FULL, COMPLETE, DETAILED content for this "
            f"single recommendation exactly as specified in the system prompt, "
            f"including ALL sub-sections:\n"
            f"  - The attribute table (knowledge, demand, stability, salaries, difficulty, AI risk)\n"
            f"  - WHY THIS CAREER SUITS YOU heading then 8-10 personalised bullet points\n"
            f"  - SUGGESTED DEGREE heading then duration, admission requirements\n"
            f"  - FUTURE JOB OPPORTUNITIES heading then table (home country + 5 top countries)\n"
            f"  - PROS and CONS headings\n"
            f"  - CURRENT RELEVANT SKILLS heading\n"
            f"  - TOP 5 UNIVERSITIES heading — each university name in ALL CAPS bold, then TABLE FORMAT\n"
            f"  - SUBJECT MAPPING table (previous subjects -> future courses + new subjects)\n"
            f"  - COMPLETE DEGREE ROADMAP heading then semester-by-semester single TABLE\n"
            f"  - INDUSTRY ROLE EXPLANATION heading with job titles, task type, and employers table\n"
            f"  - JOB MARKET ANALYSIS heading with 4 separate tables\n"
            f"  - AI AUTOMATION RISK ANALYSIS heading with risk table\n"
            f"Do NOT abbreviate, summarise, or skip any sub-section.\n"
            f"Use markdown table format (| col | col |) for ALL tables.",
            f"Recommendation #{rec_num}",
        ))

    # Section 2 — Maths (conditional)
    if math_strong:
        parts.append(call_api_for_section(
            system_prompt, user_text,
            "Generate ONLY Section 2 of the career counselling report. "
            "Start your output with exactly: 2. Mathematics-Based Additional Suggestions\n"
            "Then provide the full content as specified in the system prompt. "
            "Do not include any other section.",
            "Section 2 (Maths Suggestions)",
        ))

    # Section 3 — Communication (conditional)
    if comm_high:
        parts.append(call_api_for_section(
            system_prompt, user_text,
            "Generate ONLY Section 3 of the career counselling report. "
            "Start your output with exactly: 3. Communication-Based Additional Suggestions\n"
            "Then provide the full content as specified in the system prompt. "
            "Do not include any other section.",
            "Section 3 (Communication Suggestions)",
        ))

    # Section 4 — Affordable options (conditional)
    if financial_need:
        parts.append(call_api_for_section(
            system_prompt, user_text,
            "Generate ONLY Section 4 of the career counselling report. "
            "Start your output with exactly: 4. Affordable Study Options\n"
            "Then provide the full content as specified in the system prompt, "
            "including scholarship programs, affordable universities, online degrees, "
            "distance learning, part-time study, and financial aid. "
            "Do not include any other section.",
            "Section 4 (Affordable Study Options)",
        ))

    # Section 5 — Final advice (always)
    parts.append(call_api_for_section(
        system_prompt, user_text,
        "Generate ONLY Section 5 of the career counselling report. "
        "Start your output with exactly: 5. Final Advice & Key Takeaways\n"
        "Then provide the full closing content as specified in the system prompt. "
        "Do not include any other section.",
        "Section 5 (Final Advice)",
    ))

    full_report = "\n\n".join(p for p in parts if p and p.strip())
    return full_report if full_report.strip() else None


# ============================================================================
# FIELD SCOPE REPORT GENERATOR  (single API call)
# ============================================================================

def generate_field_scope_report(field_name):
    """Generates a general Field Scope report for a single named field.

    Uses the INDEPENDENT field-scope prompt — no student data involved.
    """
    system_prompt = build_field_scope_system_prompt()
    user_text = (
        f"Field/Career Name: {field_name}\n\n"
        f"Please generate the complete Field Scope Report for this field, "
        f"exactly as specified in your instructions, with all 8 sections, "
        f"all required tables, and no follow-up questions."
    )
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user",   "content": user_text},
    ]
    print(f"  >> Generating Field Scope Report for '{field_name}' ...", flush=True)
    try:
        response = call_with_retry(messages, retries=MAX_RETRIES)
        return extract_response_text(response)
    except (RuntimeError, KeyError) as e:
        print(f"  >> Warning: could not generate Field Scope Report: {e}")
        return None


# ============================================================================
# FIELD COMPARISON REPORT GENERATOR  (single API call)
# ============================================================================

def generate_field_comparison_report(field_names):
    """Generates a side-by-side Field Comparison report for 2+ fields.

    Uses the INDEPENDENT field-comparison prompt — no student data involved.
    field_names: list of strings already parsed from user input.
    """
    system_prompt  = build_field_comparison_system_prompt()
    fields_display = ", ".join(field_names)
    user_text = (
        f"Fields to Compare: {fields_display}\n\n"
        f"Please generate the complete Field Comparison Report for these fields, "
        f"exactly as specified in your instructions — all 8 sections, all "
        f"required comparison tables (one column per field), all country rows "
        f"in separate rows, and no follow-up questions."
    )
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user",   "content": user_text},
    ]
    print(f"  >> Generating Field Comparison Report for: {fields_display} ...", flush=True)
    try:
        response = call_with_retry(messages, retries=MAX_RETRIES)
        return extract_response_text(response)
    except (RuntimeError, KeyError) as e:
        print(f"  >> Warning: could not generate Field Comparison Report: {e}")
        return None


# ============================================================================
# PDF RENDERING HELPERS
# ============================================================================

def _is_table_separator(line):
    import re as _re
    stripped = line.strip().strip('|')
    if not stripped:
        return False
    cells = [c.strip() for c in stripped.split('|')]
    return all(_re.match(r'^[-: ]+$', c) for c in cells if c)


def _clean_inline(text):
    """Converts inline markdown to reportlab XML and strips unsafe characters."""
    import re as _re

    text = text.encode('ascii', 'ignore').decode('ascii')
    text = _re.sub(r'<br\s*/?>', ' | ', text, flags=_re.IGNORECASE)
    text = _re.sub(r'<[^>]+>', '', text)
    text = _re.sub(r'\*\*([^*]+)\*\*', r'<b>\1</b>', text)
    text = _re.sub(r'(?<!\*)\*([^*]+)\*(?!\*)', r'<i>\1</i>', text)
    text = _re.sub(r'&(?!amp;|lt;|gt;|quot;|apos;|#)', '&amp;', text)
    text = text.replace('–', '-').replace('—', '-')
    return text.strip()


def _markdown_to_reportlab(text):
    """Converts AI markdown output into a list of typed (kind, content) tuples
    that build_pdf_section() renders into reportlab flowables.

    Kinds: 'para', 'bullet', 'heading', 'rec_heading', 'table', 'spacer'
    """
    import re as _re

    text  = text.replace('\r\n', '\n').replace('\r', '\n')
    lines = text.split('\n')

    # Pass 1 — group consecutive table lines into table blocks
    raw_items = []
    i = 0
    while i < len(lines):
        line = lines[i].rstrip()
        if line.strip().startswith('|'):
            block = []
            while i < len(lines) and lines[i].rstrip().strip().startswith('|'):
                block.append(lines[i].rstrip())
                i += 1
            raw_items.append(('table_block', block))
        else:
            raw_items.append(('line', line))
            i += 1

    # Pass 2 — convert to typed element tuples
    elements = []

    for item_type, item_value in raw_items:

        if item_type == 'table_block':
            rows = []
            for tline in item_value:
                if _is_table_separator(tline):
                    continue
                cells = [_clean_inline(c.strip())
                         for c in tline.strip().strip('|').split('|')]
                if cells:
                    rows.append(cells)
            if rows:
                elements.append(('table', rows))
            continue

        line = item_value

        if not line.strip():
            if elements and elements[-1][0] != 'spacer':
                elements.append(('spacer',))
            continue

        rec_match = _re.match(
            r'^[^\w]*(?:Recommendation\s*#\d|Plan\s+[A-E]\s*[–-])', line.strip(),
            _re.IGNORECASE)
        if rec_match:
            elements.append(('rec_heading', _clean_inline(line.strip())))
            continue

        heading_match = _re.match(r'^#{2,4}\s+(.+)$', line)
        if heading_match:
            elements.append(('heading', _clean_inline(heading_match.group(1))))
            continue

        bold_heading = _re.match(r'^\*{2}([^*]+)\*{2}\s*$', line.strip())
        if bold_heading:
            elements.append(('heading', _clean_inline(bold_heading.group(1))))
            continue

        upper_heading = _re.match(
            r'^[A-Z][A-Z0-9 /&:()#\-]{8,}[A-Z0-9):]{0,2}\s*:?\s*$', line.strip())
        if upper_heading and len(line.strip()) < 100:
            elements.append(('heading', _clean_inline(line.strip())))
            continue

        star_heading = _re.match(r'^[★✦✪►▶→•]\s+(.+)$', line.strip())
        if star_heading:
            inner = star_heading.group(1)
            if len(inner) < 80 and not inner.rstrip().endswith('.'):
                elements.append(('heading', _clean_inline(inner)))
                continue

        bullet_match = _re.match(r'^[\s]*[-*•]\s+(.+)$', line)
        if bullet_match:
            elements.append(('bullet', _clean_inline(bullet_match.group(1))))
            continue

        numbered_match = _re.match(r'^[\s]*(\d+)[.)]\s+(.+)$', line)
        if numbered_match:
            num     = int(numbered_match.group(1))
            content = numbered_match.group(2)
            if num <= 5 and _re.search(
                    r'(Career|Mathematics|Communication|Affordable|Final|Advice)',
                    content, _re.IGNORECASE):
                elements.append(('heading', _clean_inline(content)))
            else:
                elements.append(('bullet', _clean_inline(content)))
            continue

        para_text = _clean_inline(line)
        if para_text.strip():
            elements.append(('para', para_text))

    return elements


def _safe_para(text, style):
    """Creates a Paragraph, falling back to ASCII-only on encoding errors."""
    try:
        return Paragraph(text, style)
    except Exception:
        return Paragraph(text.encode('ascii', 'ignore').decode('ascii'), style)


def _build_table_flowable(rows, page_width_pts):
    """Converts list-of-row-lists into a styled reportlab Table."""
    from reportlab.platypus import Paragraph as _Para
    from reportlab.lib.styles import getSampleStyleSheet as _gss

    _styles = _gss()
    header_style = ParagraphStyle(
        "TableHeader", parent=_styles["Normal"],
        fontSize=8, leading=10,
        textColor=colors.white, fontName="Helvetica-Bold")
    cell_style = ParagraphStyle(
        "TableCell", parent=_styles["Normal"],
        fontSize=8, leading=10)

    if not rows:
        return None
    num_cols   = max(len(r) for r in rows)
    table_data = []
    for row_idx, row in enumerate(rows):
        padded = row + [''] * (num_cols - len(row))
        style  = header_style if row_idx == 0 else cell_style
        table_data.append([_Para(cell, style) for cell in padded])

    col_width  = page_width_pts / max(num_cols, 1)
    col_widths = [col_width] * num_cols

    tbl = Table(table_data, colWidths=col_widths, repeatRows=1, hAlign='LEFT')
    tbl.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, 0),  colors.HexColor("#2C3E50")),
        ("TEXTCOLOR",     (0, 0), (-1, 0),  colors.white),
        ("FONTNAME",      (0, 0), (-1, 0),  "Helvetica-Bold"),
        ("ROWBACKGROUNDS",(0, 1), (-1, -1),
         [colors.HexColor("#F2F2F2"), colors.white]),
        ("GRID",          (0, 0), (-1, -1), 0.4, colors.HexColor("#AAAAAA")),
        ("FONTSIZE",      (0, 0), (-1, -1), 8),
        ("VALIGN",        (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING",    (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("LEFTPADDING",   (0, 0), (-1, -1), 4),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 4),
    ]))
    return tbl


def build_pdf_section(doc_elements, number, title, content, styles,
                      page_width_pts=None):
    """Adds one formatted section to the PDF — handles tables, headings, bullets, prose."""
    if page_width_pts is None:
        page_width_pts = A4[0] - 4 * cm

    doc_elements.append(Paragraph(f"{number}. {title}", styles["Heading2"]))
    doc_elements.append(Spacer(1, 0.3 * cm))

    if not content or not content.strip():
        doc_elements.append(Paragraph("Data not provided.", styles["Normal"]))
        doc_elements.append(Spacer(1, 0.5 * cm))
        return

    bullet_style = ParagraphStyle(
        "BulletItem", parent=styles["Normal"],
        leftIndent=18, bulletIndent=8, fontSize=9, leading=13)
    heading3_style = ParagraphStyle(
        "SubHeading", parent=styles["Normal"],
        fontSize=10, leading=14, fontName="Helvetica-Bold",
        spaceBefore=8, spaceAfter=4)
    rec_heading_style = ParagraphStyle(
        "RecHeading", parent=styles["Normal"],
        fontSize=12, leading=16, fontName="Helvetica-Bold",
        textColor=colors.HexColor("#1A5276"), spaceBefore=14, spaceAfter=6)
    normal_style = ParagraphStyle(
        "NormalSmall", parent=styles["Normal"],
        fontSize=9, leading=13)

    for item in _markdown_to_reportlab(content):
        kind = item[0]
        if kind == 'spacer':
            doc_elements.append(Spacer(1, 0.2 * cm))
        elif kind == 'table':
            tbl = _build_table_flowable(item[1], page_width_pts)
            if tbl:
                doc_elements.append(Spacer(1, 0.15 * cm))
                doc_elements.append(tbl)
                doc_elements.append(Spacer(1, 0.25 * cm))
        elif kind == 'rec_heading':
            doc_elements.append(_safe_para(item[1], rec_heading_style))
        elif kind == 'heading':
            doc_elements.append(_safe_para(item[1], heading3_style))
        elif kind == 'bullet':
            doc_elements.append(_safe_para(f"• {item[1]}", bullet_style))
        else:
            doc_elements.append(_safe_para(item[1], normal_style))

    doc_elements.append(Spacer(1, 0.5 * cm))


# ============================================================================
# PDF COVER PAGES
# ============================================================================

def _cover_page(doc_elements, title_line1, title_line2, meta_lines, styles):
    """Generic cover page builder."""
    title_style = ParagraphStyle(
        "CoverTitle", parent=styles["Title"], fontSize=22, spaceAfter=20)
    doc_elements.append(Spacer(1, 4 * cm))
    doc_elements.append(Paragraph(title_line1, title_style))
    doc_elements.append(Paragraph(title_line2, styles["Heading2"]))
    doc_elements.append(Spacer(1, 1 * cm))
    for line in meta_lines:
        doc_elements.append(Paragraph(line, styles["Normal"]))
    doc_elements.append(PageBreak())


def build_pdf_cover_page(doc_elements, profile, styles):
    _cover_page(
        doc_elements, "EduPath AI", "Career Counselling Report",
        [
            f"Student: {profile.get('name', 'N/A')}",
            f"Session ID: {profile.get('session_id', 'N/A')}",
            f"Date: {datetime.now().strftime('%Y-%m-%d')}",
        ],
        styles,
    )


def build_field_scope_pdf_cover_page(doc_elements, field_name, styles):
    _cover_page(
        doc_elements, "EduPath AI", "Field Scope Report",
        [
            f"Field: {field_name}",
            f"Date: {datetime.now().strftime('%Y-%m-%d')}",
        ],
        styles,
    )


def build_field_comparison_pdf_cover_page(doc_elements, field_names, styles):
    _cover_page(
        doc_elements, "EduPath AI", "Field Comparison Report",
        [
            f"Fields Compared: {' vs. '.join(field_names)}",
            f"Date: {datetime.now().strftime('%Y-%m-%d')}",
        ],
        styles,
    )


# ============================================================================
# PDF BUILDERS  (one per pipeline)
# ============================================================================

def _make_doc(path):
    """Creates a SimpleDocTemplate with standard margins."""
    left = right = 2 * cm
    return SimpleDocTemplate(
        path, pagesize=A4,
        leftMargin=left, rightMargin=right,
        topMargin=2 * cm, bottomMargin=2 * cm,
    ), A4[0] - left - right


def create_pdf_report(report_text, profile, path):
    """Builds and saves the personalised student PDF report."""
    ensure_reports_dir()
    styles = getSampleStyleSheet()
    doc, pw = _make_doc(path)
    elements = []

    build_pdf_cover_page(elements, profile, styles)

    sections      = parse_sections(report_text)
    math_strong   = bool(profile.get("math_is_favourite")) and bool(profile.get("math_career_ok"))
    comm_skills   = profile.get("communication_skills") or {}
    comm_high     = bool(comm_skills) and (sum(comm_skills.values()) / len(comm_skills)) >= 7
    financial_need = profile.get("financial_status") in ("Need Scholarship", "Tight Budget")
    show_flags    = {2: math_strong, 3: comm_high, 4: financial_need}

    for number in range(1, 6):
        if number in _CONDITIONAL_SECTIONS and not show_flags.get(number, False):
            continue
        build_pdf_section(
            elements, number, SECTION_TITLES[number],
            get_section_text(sections, number), styles, page_width_pts=pw)

    doc.build(elements)
    return path


def create_field_scope_pdf_report(report_text, field_name, path):
    """Builds and saves the Field Scope PDF report."""
    ensure_reports_dir()
    styles = getSampleStyleSheet()
    doc, pw = _make_doc(path)
    elements = []

    build_field_scope_pdf_cover_page(elements, field_name, styles)
    sections = parse_field_scope_sections(report_text)

    for number in range(1, 9):
        build_pdf_section(
            elements, number, FIELD_SCOPE_SECTION_TITLES[number],
            get_section_text(sections, number), styles, page_width_pts=pw)

    doc.build(elements)
    return path


def create_field_comparison_pdf_report(report_text, field_names, path):
    """Builds and saves the Field Comparison PDF report."""
    ensure_reports_dir()
    styles = getSampleStyleSheet()
    doc, pw = _make_doc(path)
    elements = []

    build_field_comparison_pdf_cover_page(elements, field_names, styles)
    sections = parse_field_comparison_sections(report_text)

    for number in range(1, 9):
        build_pdf_section(
            elements, number, FIELD_COMPARISON_SECTION_TITLES[number],
            get_section_text(sections, number), styles, page_width_pts=pw)

    doc.build(elements)
    return path


# ============================================================================
# FILENAME GENERATORS + SAVE WRAPPERS
# ============================================================================

def generate_report_filename(profile):
    name     = re.sub(r"[^A-Za-z0-9]", "", (profile.get("name") or "Student").replace(" ", ""))
    date_str = datetime.now().strftime("%Y%m%d")
    return f"Report_{name}_{date_str}.pdf"


def generate_field_scope_report_filename(field_name):
    name     = re.sub(r"[^A-Za-z0-9]", "", (field_name or "Field").strip().replace(" ", ""))
    date_str = datetime.now().strftime("%Y%m%d")
    return f"FieldScope_{name}_{date_str}.pdf"


def generate_field_comparison_report_filename(field_names):
    combined = "Vs".join(
        re.sub(r"[^A-Za-z0-9]", "", n.strip().replace(" ", ""))
        for n in field_names
    )[:60]
    date_str = datetime.now().strftime("%Y%m%d")
    return f"Compare_{combined}_{date_str}.pdf"


def save_report(report_text, profile):
    ensure_reports_dir()
    path = os.path.join(REPORT_DIR, generate_report_filename(profile))
    try:
        create_pdf_report(report_text, profile, path)
        return path
    except Exception as e:
        print(f"  >> Could not save PDF report: {e}")
        return None


def save_field_scope_report(report_text, field_name):
    ensure_reports_dir()
    path = os.path.join(REPORT_DIR, generate_field_scope_report_filename(field_name))
    try:
        create_field_scope_pdf_report(report_text, field_name, path)
        return path
    except Exception as e:
        print(f"  >> Could not save Field Scope PDF report: {e}")
        return None


def save_field_comparison_report(report_text, field_names):
    ensure_reports_dir()
    path = os.path.join(REPORT_DIR, generate_field_comparison_report_filename(field_names))
    try:
        create_field_comparison_pdf_report(report_text, field_names, path)
        return path
    except Exception as e:
        print(f"  >> Could not save Field Comparison PDF report: {e}")
        return None
