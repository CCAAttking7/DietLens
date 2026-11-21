from pathlib import Path

from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_CONNECTOR, MSO_SHAPE
from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
from pptx.util import Inches, Pt


ROOT = Path(__file__).resolve().parents[1]
OUT = Path(__file__).resolve().parent
SCREENSHOT = ROOT / "artifacts/dietlens-round-3/after/dietlens-home-1440.png"

W, H = 13.333, 7.5
NAVY = RGBColor(15, 23, 42)
NAVY_2 = RGBColor(24, 35, 58)
INK = RGBColor(36, 35, 31)
CREAM = RGBColor(247, 246, 242)
MUTED = RGBColor(164, 174, 191)
LINE = RGBColor(61, 75, 99)
BRAND = RGBColor(178, 78, 50)
BRAND_LIGHT = RGBColor(246, 210, 193)
SAGE = RGBColor(126, 177, 145)
TEAL = RGBColor(121, 190, 184)
AMBER = RGBColor(224, 175, 86)
WHITE = RGBColor(255, 255, 255)


def rgb_hex(c):
    return "#%02x%02x%02x" % (c[0], c[1], c[2])


def box(slide, x, y, w, h, fill=None, line=None, radius=False, transparency=0):
    shape = slide.shapes.add_shape(
        MSO_SHAPE.ROUNDED_RECTANGLE if radius else MSO_SHAPE.RECTANGLE,
        Inches(x), Inches(y), Inches(w), Inches(h),
    )
    shape.fill.solid()
    shape.fill.fore_color.rgb = fill or NAVY
    shape.fill.transparency = transparency
    shape.line.color.rgb = line or fill or NAVY
    shape.line.transparency = 0 if line else 100
    if radius:
        shape.adjustments[0] = 0.12
    return shape


def text(slide, value, x, y, w, h, size=18, color=CREAM, bold=False,
         font="Inter", align=PP_ALIGN.LEFT, valign=MSO_ANCHOR.TOP,
         margin=0, italic=False, tracking=None):
    tb = slide.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    tf = tb.text_frame
    tf.clear()
    tf.word_wrap = True
    tf.margin_left = Inches(margin)
    tf.margin_right = Inches(margin)
    tf.margin_top = Inches(margin)
    tf.margin_bottom = Inches(margin)
    tf.vertical_anchor = valign
    p = tf.paragraphs[0]
    p.alignment = align
    p.space_after = Pt(0)
    run = p.add_run()
    run.text = value
    run.font.name = font
    run.font.size = Pt(size)
    run.font.bold = bold
    run.font.italic = italic
    run.font.color.rgb = color
    if tracking is not None:
        run.font._element.set("spc", str(tracking))
    return tb


def rich_lines(slide, lines, x, y, w, h, size=14, color=CREAM, leading=1.15,
               bullet=False, gap=7, font="Inter"):
    tb = slide.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    tf = tb.text_frame
    tf.clear()
    tf.word_wrap = True
    tf.margin_left = Inches(0.02)
    tf.margin_right = Inches(0.02)
    tf.margin_top = Inches(0.02)
    tf.margin_bottom = Inches(0.02)
    for i, item in enumerate(lines):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.space_after = Pt(gap)
        p.line_spacing = leading
        p.level = 0
        if bullet:
            p.text = "• " + item
        else:
            p.text = item
        p.font.name = font
        p.font.size = Pt(size)
        p.font.color.rgb = color
    return tb


def line(slide, x1, y1, x2, y2, color=LINE, width=1.2, arrow=False, dash=None):
    shape = slide.shapes.add_connector(MSO_CONNECTOR.STRAIGHT, Inches(x1), Inches(y1), Inches(x2), Inches(y2))
    shape.line.color.rgb = color
    shape.line.width = Pt(width)
    if dash:
        shape.line.dash_style = dash
    if arrow:
        shape.line.end_arrowhead = True
    return shape


def pill(slide, value, x, y, w, fill=NAVY_2, color=BRAND_LIGHT, border=None, size=10):
    box(slide, x, y, w, 0.30, fill=fill, line=border or fill, radius=True)
    text(slide, value.upper(), x, y + 0.01, w, 0.26, size=size, color=color, bold=True,
         align=PP_ALIGN.CENTER, valign=MSO_ANCHOR.MIDDLE, tracking=5)


def title_block(slide, eyebrow, title_value, subtitle=None, num=None):
    text(slide, eyebrow.upper(), 0.60, 0.40, 7.8, 0.25, size=10, color=BRAND_LIGHT,
         bold=True, tracking=8)
    text(slide, title_value, 0.60, 0.78, 11.9, 0.62, size=27, color=CREAM, bold=True,
         font="Inter Display")
    if subtitle:
        text(slide, subtitle, 0.62, 1.49, 11.4, 0.38, size=12, color=MUTED)
    if num:
        text(slide, num, 12.05, 0.45, 0.70, 0.22, size=10, color=MUTED, align=PP_ALIGN.RIGHT,
             bold=True, tracking=3)


def footer(slide, source=None):
    line(slide, 0.60, 7.08, 12.73, 7.08, color=LINE, width=0.65)
    text(slide, "DIETLENS  ·  SYSTEM DESIGN PROGRESS  ·  2026", 0.60, 7.17, 6.2, 0.16,
         size=8, color=MUTED, bold=True, tracking=2)
    if source:
        text(slide, source, 6.45, 7.17, 6.28, 0.16, size=7.5, color=MUTED, align=PP_ALIGN.RIGHT)


def add_slide(prs, bg=NAVY):
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    slide.background.fill.solid()
    slide.background.fill.fore_color.rgb = bg
    return slide


def card(slide, x, y, w, h, heading, body, accent=BRAND, body_size=11.5, icon=None):
    box(slide, x, y, w, h, fill=NAVY_2, line=LINE, radius=True)
    box(slide, x, y, 0.06, h, fill=accent, line=accent, radius=True)
    if icon:
        box(slide, x + 0.25, y + 0.24, 0.34, 0.34, fill=accent, line=accent, radius=True)
        text(slide, icon, x + 0.25, y + 0.255, 0.34, 0.30, size=11, color=NAVY,
             bold=True, align=PP_ALIGN.CENTER, valign=MSO_ANCHOR.MIDDLE)
        hx = x + 0.75
    else:
        hx = x + 0.28
    text(slide, heading, hx, y + 0.22, w - (hx - x) - 0.18, 0.28, size=13, color=CREAM, bold=True)
    rich_lines(slide, body if isinstance(body, list) else [body], x + 0.28, y + 0.67, w - 0.52,
               h - 0.86, size=body_size, color=MUTED, gap=6)


def node(slide, x, y, w, h, heading, detail, fill=NAVY_2, accent=BRAND, detail_color=MUTED):
    box(slide, x, y, w, h, fill=fill, line=LINE, radius=True)
    box(slide, x, y, w, 0.07, fill=accent, line=accent, radius=True)
    text(slide, heading, x + 0.16, y + 0.18, w - 0.32, 0.26, size=11.5, color=CREAM, bold=True,
         align=PP_ALIGN.CENTER)
    text(slide, detail, x + 0.16, y + 0.50, w - 0.32, h - 0.62, size=8.5, color=detail_color,
         align=PP_ALIGN.CENTER, valign=MSO_ANCHOR.MIDDLE)


def build_deck():
    prs = Presentation()
    prs.slide_width = Inches(W)
    prs.slide_height = Inches(H)
    prs.core_properties.title = "DietLens — System Design Progress"
    prs.core_properties.subject = "Assignment 2 · Logical, deployment and technology architecture"
    prs.core_properties.author = "DietLens team"
    prs.core_properties.keywords = "DietLens, system design, architecture, agentic workflow"

    # 1 — cover
    s = add_slide(prs)
    box(s, 0, 0, W, H, fill=NAVY, line=NAVY)
    box(s, 0, 0, 0.12, H, fill=BRAND, line=BRAND)
    pill(s, "SYSTEM DESIGN PROGRESS", 0.72, 0.62, 2.30)
    text(s, "DietLens", 0.70, 1.40, 5.8, 0.68, size=42, color=CREAM, bold=True, font="Inter Display")
    text(s, "From meal choice\nto trusted reflection", 0.72, 2.15, 5.7, 1.15, size=27, color=CREAM,
         bold=True, font="Inter Display")
    text(s, "A lightweight, user-controlled personal meal decision\nand reflection companion.", 0.75, 3.55, 5.2, 0.65,
         size=14, color=MUTED)
    pill(s, "AGENTIC WORKFLOW", 0.74, 4.65, 1.58, fill=BRAND, color=WHITE)
    pill(s, "HUMAN CONFIRMATION", 2.43, 4.65, 1.92, fill=NAVY_2, color=BRAND_LIGHT)
    pill(s, "EVIDENCE-FIRST DATA", 4.45, 4.65, 1.78, fill=NAVY_2, color=BRAND_LIGHT)
    text(s, "Assignment 2  ·  Design presentation  ·  2026–2027", 0.75, 6.35, 5.8, 0.25,
         size=10, color=MUTED, bold=True, tracking=1)
    # actual product evidence
    box(s, 7.12, 0.72, 5.54, 5.85, fill=RGBColor(28, 39, 61), line=LINE, radius=True)
    if SCREENSHOT.exists():
        s.shapes.add_picture(str(SCREENSHOT), Inches(7.33), Inches(1.02), width=Inches(5.12), height=Inches(4.80))
    box(s, 7.33, 5.97, 5.12, 0.36, fill=NAVY_2, line=NAVY_2, radius=True)
    text(s, "Product evidence · current meal composer", 7.55, 6.02, 4.7, 0.19, size=9, color=MUTED,
         align=PP_ALIGN.CENTER)
    footer(s, "Evidence: artifacts/dietlens-round-3/after/dietlens-home-1440.png")

    # 2 — thesis / progress
    s = add_slide(prs)
    title_block(s, "01 · Design thesis", "Make every meal decision traceable", "Progress since Part I: the product is now designed around a trustworthy loop, not a generic chatbot.", "02 / 07")
    # left statement
    box(s, 0.62, 2.12, 4.10, 3.92, fill=BRAND, line=BRAND, radius=True)
    text(s, "THE PRODUCT PROMISE", 0.94, 2.45, 3.2, 0.25, size=10, color=BRAND_LIGHT, bold=True, tracking=6)
    text(s, "Context →\nDecision →\nActual meal →\nReflection", 0.94, 2.92, 3.25, 2.05, size=28, color=WHITE, bold=True, font="Inter Display")
    text(s, "The same confirmed context should remain understandable\nwhen the user looks back later.", 0.96, 5.27, 3.10, 0.51, size=11.5, color=BRAND_LIGHT)
    # right progression
    text(s, "What changed in the design", 5.25, 2.12, 5.8, 0.28, size=14, color=CREAM, bold=True)
    rows = [
        ("Generic assistant", "Bounded decision companion", "state + confirmation"),
        ("Missing values hidden", "Unknown is explicit", "truthful data"),
        ("Plan and intake conflated", "Plan / actual / feedback separated", "clean semantics"),
        ("Model as authority", "Model interprets; rules decide", "safe boundaries"),
    ]
    yy = 2.62
    for old, new, tag in rows:
        box(s, 5.25, yy, 2.13, 0.70, fill=NAVY_2, line=LINE, radius=True)
        text(s, old, 5.43, yy + 0.14, 1.78, 0.34, size=10, color=MUTED, bold=True)
        text(s, "→", 7.53, yy + 0.16, 0.36, 0.28, size=17, color=BRAND_LIGHT, bold=True, align=PP_ALIGN.CENTER)
        box(s, 7.98, yy, 3.03, 0.70, fill=RGBColor(34, 55, 66), line=RGBColor(74, 117, 122), radius=True)
        text(s, new, 8.17, yy + 0.14, 2.65, 0.34, size=10, color=CREAM, bold=True)
        pill(s, tag, 11.25, yy + 0.18, 1.18, fill=NAVY_2, color=TEAL, border=LINE, size=8)
        yy += 0.83
    footer(s, "Sources: docs/product-logic.md · docs/DietLens-Round-4.1-Data-Truth-and-Experience-Closure.md")

    # 3 — decisions
    s = add_slide(prs)
    title_block(s, "02 · Key decisions", "The architecture makes trust a system property", "Each decision removes a specific failure mode identified in the requirements and product audit.", "03 / 07")
    card(s, 0.62, 2.14, 2.88, 2.05, "One control plane", ["Harness owns state transitions, consent and writes.", "UI stays thin and recoverable."], BRAND, icon="1")
    card(s, 3.67, 2.14, 2.88, 2.05, "Rules decide safety", ["The model may extract intent.", "Deterministic rules decide blocked / needs confirmation / safe."], SAGE, icon="2")
    card(s, 6.72, 2.14, 2.88, 2.05, "Facts stay separate", ["Plan servings, ingredient quantity and actual intake are different fields.", "No silent copying."], TEAL, icon="3")
    card(s, 9.77, 2.14, 2.88, 2.05, "Unknown is real", ["Missing allergy or source data remains unknown.", "No invented zeros or certainty."], AMBER, icon="4")
    # bottom decision strip
    box(s, 0.62, 4.60, 12.03, 1.42, fill=NAVY_2, line=LINE, radius=True)
    text(s, "DESIGN CONSEQUENCE", 0.92, 4.91, 1.75, 0.22, size=9, color=BRAND_LIGHT, bold=True, tracking=5)
    text(s, "A recommendation is not a write.  A source field is not proof.  A plan is not an actual meal.",
         0.92, 5.27, 10.9, 0.32, size=17, color=CREAM, bold=True, font="Inter Display")
    text(s, "The system keeps each transition explicit so users can understand, confirm and revise it.",
         0.94, 5.70, 10.6, 0.22, size=10.5, color=MUTED)
    footer(s, "Decision log: docs/product-logic.md · docs/model-routing.md · docs/profile-workflow.md")

    # 4 — logical architecture
    s = add_slide(prs)
    title_block(s, "03 · Logical architecture", "One control plane, bounded intelligence", "The Harness coordinates the workflow; domain services keep safety and persistence deterministic.", "04 / 07")
    # nodes
    node(s, 0.72, 3.04, 1.45, 1.00, "USER", "meal · profile · feedback", fill=BRAND, accent=BRAND, detail_color=BRAND_LIGHT)
    node(s, 2.65, 2.80, 1.72, 1.50, "WEB APP", "React / Vite\nroute + focus + draft", fill=NAVY_2, accent=TEAL)
    node(s, 4.91, 2.80, 1.88, 1.50, "API BOUNDARY", "FastAPI\nvalidation + auth", fill=NAVY_2, accent=TEAL)
    node(s, 7.37, 2.46, 2.08, 2.18, "HARNESS", "state machine\nconsent gate\noperation key\nrecovery", fill=RGBColor(46, 55, 70), accent=BRAND)
    node(s, 10.04, 2.05, 2.20, 0.92, "DOMAIN RULES", "food safety · profile", fill=NAVY_2, accent=SAGE)
    node(s, 10.04, 3.16, 2.20, 0.92, "DOMAIN SERVICES", "planning · meals · review", fill=NAVY_2, accent=TEAL)
    node(s, 10.04, 4.27, 2.20, 0.92, "REPOSITORY / STORE", "SQLite or Supabase", fill=NAVY_2, accent=AMBER)
    # connectors
    line(s, 2.17, 3.54, 2.65, 3.54, color=BRAND_LIGHT, arrow=True)
    line(s, 4.37, 3.54, 4.91, 3.54, color=BRAND_LIGHT, arrow=True)
    line(s, 6.79, 3.54, 7.37, 3.54, color=BRAND_LIGHT, arrow=True)
    line(s, 9.45, 2.98, 10.04, 2.49, color=SAGE, arrow=True)
    line(s, 9.45, 3.54, 10.04, 3.62, color=TEAL, arrow=True)
    line(s, 9.45, 4.16, 10.04, 4.72, color=AMBER, arrow=True)
    # side model boundary
    box(s, 7.25, 5.12, 5.01, 0.78, fill=NAVY, line=BRAND, radius=True)
    text(s, "OPTIONAL MODEL PROVIDER", 7.48, 5.29, 1.95, 0.20, size=9, color=BRAND_LIGHT, bold=True, tracking=3)
    text(s, "structured intent only · never writes · never declares safety", 9.44, 5.27, 2.54, 0.28, size=9, color=MUTED, align=PP_ALIGN.RIGHT)
    line(s, 8.40, 5.12, 8.40, 4.64, color=BRAND_LIGHT, width=1, dash=1)
    footer(s, "Evidence: api_server.py · dietlens_mvp/harness.py · dietlens_mvp/tools.py · models.py")

    # 5 — deployment + technology
    s = add_slide(prs)
    title_block(s, "04 · Deployment + technology", "Small runtime footprint, clear seams", "The prototype can run locally with SQLite while keeping an explicit path to hosted auth, storage and source adapters.", "05 / 07")
    # deployment top
    text(s, "DEPLOYMENT VIEW", 0.66, 2.08, 2.0, 0.22, size=9, color=BRAND_LIGHT, bold=True, tracking=5)
    node(s, 0.70, 2.50, 2.15, 1.18, "CLIENT DEVICE", "Browser\nReact static assets", fill=NAVY_2, accent=TEAL)
    node(s, 3.60, 2.50, 2.15, 1.18, "APP RUNTIME", "FastAPI\nHarness + domain services", fill=NAVY_2, accent=BRAND)
    node(s, 6.50, 2.50, 2.15, 1.18, "DATA NODE", "SQLite / WAL\nor Supabase Postgres", fill=NAVY_2, accent=AMBER)
    node(s, 9.40, 2.50, 2.15, 1.18, "EXTERNAL SOURCES", "Food data adapters\noptional model API", fill=NAVY_2, accent=SAGE)
    line(s, 2.85, 3.09, 3.60, 3.09, color=BRAND_LIGHT, arrow=True)
    line(s, 5.75, 3.09, 6.50, 3.09, color=BRAND_LIGHT, arrow=True)
    line(s, 8.65, 3.09, 9.40, 3.09, color=BRAND_LIGHT, arrow=True)
    # technology bottom
    text(s, "TECHNOLOGY CHOICES", 0.66, 4.27, 2.6, 0.22, size=9, color=BRAND_LIGHT, bold=True, tracking=5)
    techs = [
        ("Frontend", "React + TypeScript\nVite", TEAL),
        ("Backend", "FastAPI + Pydantic\nPython services", BRAND),
        ("Persistence", "SQLite prototype\nSupabase path", AMBER),
        ("Verification", "pytest · Playwright\ncontrast + syntax", SAGE),
    ]
    xx = 0.70
    for heading, body, accent in techs:
        box(s, xx, 4.68, 2.70, 1.36, fill=NAVY_2, line=LINE, radius=True)
        text(s, heading, xx + 0.19, 4.91, 2.28, 0.24, size=11.5, color=CREAM, bold=True)
        text(s, body, xx + 0.19, 5.29, 2.28, 0.48, size=10, color=MUTED)
        box(s, xx + 0.19, 5.92, 0.62, 0.06, fill=accent, line=accent, radius=True)
        xx += 3.00
    footer(s, "Rationale: low operational friction now; explicit seams for deployment and testability later.")

    # 6 — interaction / guardrails
    s = add_slide(prs)
    title_block(s, "05 · Interaction design", "From user input to a confirmed fact", "The agentic part is intentionally narrow: interpret the request, then hand control back to rules and the user.", "06 / 07")
    steps = [
        ("01", "Describe", "meal + options", BRAND),
        ("02", "Interpret", "structured intent", TEAL),
        ("03", "Check", "profile + source", SAGE),
        ("04", "Offer", "bounded actions", AMBER),
        ("05", "Confirm", "explicit write", BRAND),
        ("06", "Reflect", "feedback + review", TEAL),
    ]
    xx = 0.70
    for i, (n, heading, detail, accent) in enumerate(steps):
        box(s, xx, 2.62, 1.70, 1.18, fill=NAVY_2, line=LINE, radius=True)
        text(s, n, xx + 0.15, 2.80, 0.45, 0.25, size=10, color=accent, bold=True, tracking=2)
        text(s, heading, xx + 0.15, 3.13, 1.38, 0.25, size=13, color=CREAM, bold=True)
        text(s, detail, xx + 0.15, 3.48, 1.38, 0.20, size=9, color=MUTED)
        if i < len(steps) - 1:
            line(s, xx + 1.70, 3.21, xx + 2.04, 3.21, color=BRAND_LIGHT, arrow=True)
        xx += 2.06
    # state strip
    box(s, 0.70, 4.45, 7.98, 1.22, fill=RGBColor(34, 55, 66), line=RGBColor(74, 117, 122), radius=True)
    text(s, "PERSISTED STATE", 0.98, 4.73, 1.48, 0.20, size=9, color=TEAL, bold=True, tracking=4)
    text(s, "Draft → interpreted → needs confirmation → confirmed → feedback", 0.98, 5.08, 7.22, 0.28, size=16, color=CREAM, bold=True, font="Inter Display")
    # guardrail panel
    box(s, 9.10, 4.45, 3.55, 1.22, fill=RGBColor(67, 47, 44), line=BRAND, radius=True)
    text(s, "MODEL BOUNDARY", 9.36, 4.73, 1.65, 0.20, size=9, color=BRAND_LIGHT, bold=True, tracking=4)
    text(s, "Cannot write,\nbypass consent or declare safety.", 9.36, 5.05, 2.86, 0.43, size=11, color=WHITE, bold=True)
    footer(s, "Interaction evidence: docs/product-logic.md · docs/model-routing.md")

    # 7 — refinements and open issues
    s = add_slide(prs)
    title_block(s, "06 · Refinement + next validation", "Design decisions are explicit—and testable", "Requirements were refined where implementation exposed a safety or semantic gap. Part III validates the remaining risks.", "07 / 07")
    # left
    box(s, 0.62, 2.13, 5.90, 4.25, fill=NAVY_2, line=LINE, radius=True)
    text(s, "REQUIREMENT REFINEMENTS", 0.94, 2.44, 3.1, 0.23, size=9, color=BRAND_LIGHT, bold=True, tracking=5)
    refinements = [
        ("01", "Allergy state is tri-state", "unknown / none / specified"),
        ("02", "Planning is single-day in UI", "7-day backend remains future work"),
        ("03", "Quantities are separate", "servings ≠ ingredient ≠ actual intake"),
        ("04", "Nutrition is bounded", "no inference from meal names"),
        ("05", "Shopping is explicit", "main ingredients only; no auto conversion"),
    ]
    yy = 2.92
    for n, head, detail in refinements:
        text(s, n, 0.98, yy, 0.35, 0.21, size=9, color=BRAND, bold=True, tracking=2)
        text(s, head, 1.44, yy - 0.02, 2.90, 0.23, size=11, color=CREAM, bold=True)
        text(s, detail, 1.44, yy + 0.25, 4.40, 0.18, size=9.2, color=MUTED)
        yy += 0.64
    # right
    box(s, 6.82, 2.13, 5.83, 4.25, fill=RGBColor(28, 39, 61), line=LINE, radius=True)
    text(s, "OPEN ISSUES FOR PART III", 7.14, 2.44, 3.0, 0.23, size=9, color=BRAND_LIGHT, bold=True, tracking=5)
    issues = [
        "Secure authenticated browser fixture",
        "Ingredient-level restaurant allergen verification",
        "A truthful 7-day planning editor",
        "Portion-aware nutrition coverage",
        "Feedback-driven preference signals",
    ]
    rich_lines(s, issues, 7.16, 2.92, 4.86, 2.25, size=12, color=CREAM, bullet=True, gap=13)
    box(s, 7.14, 5.48, 5.10, 0.50, fill=BRAND, line=BRAND, radius=True)
    text(s, "Prototype the risky assumptions before scaling the claims.", 7.34, 5.61, 4.70, 0.21, size=10.5, color=WHITE, bold=True, align=PP_ALIGN.CENTER)
    footer(s, "Next: prototype, measure, then promote only verified capabilities.")

    OUT.mkdir(parents=True, exist_ok=True)
    out_path = OUT / "DietLens-Assignment-2-System-Design.pptx"
    prs.save(out_path)
    return out_path


if __name__ == "__main__":
    print(build_deck())
