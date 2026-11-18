import html
import datetime
import streamlit as st
from fpdf import FPDF
from core import (
    PRIMARY_MODEL,
    BACKUP_MODEL,
    BENCHMARK_QUESTIONS,
    check_answer,
    answer_question,
    explain_failure,
    was_backup_used,
    read_document_text,
    extract_document_claims,
    verify_claim_item,
    generate_topic_brief,
    load_benchmark,
    evaluate_single_benchmark_question,
    save_benchmark,
)

st.set_page_config(
    page_title="Stale-answer detector",
    initial_sidebar_state="collapsed",
)

st.markdown(
    """
    <style>
    /* Deep dark canvas & completely hide sidebar */
    .stApp {
        background-color: #0B0F14 !important;
        color: #F8FAFC !important;
    }
    [data-testid="stSidebar"], [data-testid="collapsedControl"] {
        display: none !important;
    }
    [data-testid="stMainBlockContainer"] {
        max-width: 840px;
        padding-top: 2rem;
        padding-bottom: 3rem;
        margin: 0 auto;
    }
    [data-testid="stVerticalBlock"] { gap: 0.95rem; }
    [data-testid="stHorizontalBlock"] { gap: 0.85rem; }
    .stApp p, .stApp li, .stApp label { font-size: 14px; }

    /* Glowing teal buttons */
    .stButton button, .stDownloadButton button {
        width: 100%;
        font-size: 0.89rem;
        padding: 0.56rem 0.75rem;
        border-radius: 9px;
        border: 1px solid rgba(94, 234, 212, 0.45) !important;
        background-color: #111921 !important;
        color: #E2E8F0 !important;
        box-shadow: 0 0 8px rgba(20, 184, 166, 0.12);
        transition: all 0.2s ease;
    }
    .stButton button:hover, .stDownloadButton button:hover {
        border-color: #5EEAD4 !important;
        color: #FFFFFF !important;
        box-shadow: 0 0 12px rgba(94, 234, 212, 0.28);
    }
    .stButton button[kind="primary"] {
        background-color: #0D9488 !important;
        color: #FFFFFF !important;
        font-weight: 700 !important;
        border: 1px solid #5EEAD4 !important;
        box-shadow: 0 0 14px rgba(20, 184, 166, 0.35);
    }
    textarea, input {
        border-color: rgba(94, 234, 212, 0.35) !important;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

COLORS = {
    "Fresh": ("#14532D", "#86EFAC", "#22C55E"),
    "Unclear": ("#78350F", "#FDE68A", "#F59E0B"),
    "Outdated": ("#7F1D1D", "#FCA5A5", "#EF4444"),
}
CAUSES = {
    "unclear_question": "The question was unclear or missing details",
    "outdated_knowledge": "The AI used outdated knowledge",
    "ai_mistake": "The AI made a mistake or invented something",
    "answer_looks_fine": "The answer looks fine",
}
NOT_CONFIRMED = "Could not confirm the latest information. Check the source link."
SAMPLE = ("The CEO of Twitter is Parag Agrawal. "
          "Python 3.9 is the latest version of Python. "
          "ChatGPT Plus costs $20 per month.")


def md(text):
    return str(text).replace("$", "\\$")


def hx(text):
    return html.escape(str(text)).replace("$", "&#36;")


def heading(text, color="#5EEAD4"):
    st.markdown('<div style="font-size:18px;font-weight:700;color:' + color
                + ';margin-top:8px;">' + text + '</div>', unsafe_allow_html=True)


def to_score(value):
    try:
        return int(float(value))
    except Exception:
        return 50


def level(score):
    if score >= 70:
        return "Fresh"
    if score >= 40:
        return "Unclear"
    return "Outdated"


def badge(name):
    bg, fg, border = COLORS[name]
    return (f'<span style="background:{bg};color:{fg};border:1px solid {border};'
            f'padding:3px 10px;border-radius:12px;font-size:12px;font-weight:700;'
            f'white-space:nowrap;">{name}</span>')


def tile(label, value, color="#5EEAD4"):
    return ('<div style="border:1px solid rgba(94, 234, 212, 0.45);border-radius:10px;'
            'padding:12px 14px;background:rgba(20, 184, 166, 0.05);'
            'box-shadow:0 0 10px rgba(20, 184, 166, 0.10);">'
            '<div style="font-size:15px;font-weight:700;color:' + color + ';">' + label + '</div>'
            '<div style="font-size:15px;font-weight:600;margin-top:4px;color:#F8FAFC;">' + hx(value) + '</div></div>')


def clean_pdf_text(text):
    replacements = {
        "\u2014": "-", "\u2013": "-", "\u2018": "'", "\u2019": "'",
        "\u201c": '"', "\u201d": '"', "\u2022": "*", "\u20b9": "Rs. ",
        "\u20ac": "EUR ", "\u00a3": "GBP ", "\u2192": "->",
    }
    s = str(text or "")
    for k, v in replacements.items():
        s = s.replace(k, v)
    return s.encode("latin-1", "replace").decode("latin-1")


def write_pdf_block(pdf, text, line_h=6):
    pdf.set_x(pdf.l_margin)
    pdf.multi_cell(pdf.epw, line_h, clean_pdf_text(text), new_x="LMARGIN", new_y="NEXT")


def section_banner(pdf, title, rgb=(15, 118, 110)):
    pdf.ln(3)
    pdf.set_font("Helvetica", "B", 13)
    pdf.set_text_color(*rgb)
    write_pdf_block(pdf, title, line_h=7)
    y = pdf.get_y()
    pdf.set_draw_color(*rgb)
    pdf.set_line_width(0.4)
    pdf.line(pdf.l_margin, y, pdf.l_margin + pdf.epw, y)
    pdf.ln(3)


def build_pdf_report(source_text, results, levels, verdict, why, brief, section_title="2. Checked Content"):
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()

    pdf.set_fill_color(15, 118, 110)
    pdf.rect(pdf.l_margin, pdf.get_y(), pdf.epw, 18, style="F")
    pdf.set_xy(pdf.l_margin + 4, pdf.get_y() + 3)
    pdf.set_font("Helvetica", "B", 16)
    pdf.set_text_color(255, 255, 255)
    pdf.cell(0, 6, "Stale-Answer Detector | Fact & Freshness Audit", new_x="LMARGIN", new_y="NEXT")
    pdf.set_x(pdf.l_margin + 4)
    pdf.set_font("Helvetica", "", 9)
    pdf.set_text_color(204, 251, 241)
    topic_label = brief.get("topic_title") or "AI Answer Verification Report"
    pdf.cell(0, 5, clean_pdf_text(f"Subject: {topic_label}   |   Date: {datetime.date.today().isoformat()}"),
             new_x="LMARGIN", new_y="NEXT")
    pdf.ln(6)

    fresh_c = levels.count("Fresh")
    outdated_c = levels.count("Outdated")
    unclear_c = levels.count("Unclear")
    pdf.set_fill_color(240, 253, 250)
    pdf.set_draw_color(45, 212, 191)
    box_y = pdf.get_y()
    pdf.rect(pdf.l_margin, box_y, pdf.epw, 14, style="DF")
    pdf.set_xy(pdf.l_margin + 4, box_y + 4)
    pdf.set_font("Helvetica", "B", 10)
    pdf.set_text_color(15, 118, 110)
    summary_line = (
        f"OVERALL VERDICT: {verdict.upper()}    |    "
        f"Claims Checked: {len(results)}   (Fresh: {fresh_c}, Outdated: {outdated_c}, Unclear: {unclear_c})"
    )
    pdf.cell(0, 6, clean_pdf_text(summary_line), new_x="LMARGIN", new_y="NEXT")
    pdf.ln(5)

    if brief.get("topic_overview") or brief.get("key_insights"):
        section_banner(pdf, "1. Topic Overview & Context", rgb=(13, 148, 136))
        if brief.get("topic_overview"):
            pdf.set_font("Helvetica", "", 10)
            pdf.set_text_color(30, 41, 59)
            write_pdf_block(pdf, brief["topic_overview"], line_h=5.5)
            pdf.ln(2)
        if brief.get("key_insights"):
            pdf.set_font("Helvetica", "B", 10)
            pdf.set_text_color(15, 118, 110)
            write_pdf_block(pdf, "Key Takeaways:", line_h=5.5)
            pdf.set_font("Helvetica", "", 10)
            pdf.set_text_color(51, 65, 85)
            for item in brief["key_insights"]:
                write_pdf_block(pdf, f"  * {item}", line_h=5.5)

    section_banner(pdf, section_title, rgb=(30, 64, 175))
    pdf.set_font("Helvetica", "", 10)
    pdf.set_text_color(30, 41, 59)
    write_pdf_block(pdf, source_text[:1500], line_h=5.5)

    section_banner(pdf, "3. Claim-by-Claim Verification", rgb=(15, 118, 110))
    status_colors = {
        "Fresh": (22, 101, 52),
        "Outdated": (185, 28, 28),
        "Unclear": (180, 83, 9),
    }

    for idx, (r, lv) in enumerate(zip(results, levels), start=1):
        pdf.set_font("Helvetica", "B", 10.5)
        r_col = status_colors.get(lv, (30, 41, 59))
        pdf.set_text_color(*r_col)
        write_pdf_block(pdf, f"Claim {idx} [{lv.upper()}]: {r.get('claim', '')}", line_h=5.5)

        pdf.set_font("Helvetica", "", 9.5)
        pdf.set_text_color(51, 65, 85)
        write_pdf_block(pdf, f"Finding: {r.get('reason', '')}", line_h=5)
        if r.get("source_url"):
            pdf.set_text_color(2, 132, 199)
            write_pdf_block(pdf, f"Verified Source: {r.get('source_url', '')}", line_h=5)
        pdf.ln(2.5)

    to_fix = [(r, lv) for r, lv in zip(results, levels) if lv != "Fresh"]
    if to_fix:
        section_banner(pdf, "4. Updated & Corrected Information", rgb=(21, 128, 61))
        for r, lv in to_fix:
            fix = r.get("current_info") or NOT_CONFIRMED
            pdf.set_font("Helvetica", "B", 9.5)
            pdf.set_text_color(100, 116, 139)
            write_pdf_block(pdf, f"Outdated Statement: {r.get('claim', '')}", line_h=5)
            pdf.set_font("Helvetica", "B", 10)
            pdf.set_text_color(22, 101, 52)
            write_pdf_block(pdf, f"Current Fact: {fix}", line_h=5.5)
            pdf.ln(2)

    if why:
        section_banner(pdf, "5. Root Cause Analysis (Why Did the AI Go Wrong?)", rgb=(109, 40, 217))
        cause = CAUSES.get(why.get("cause"), "Not clear")
        pdf.set_font("Helvetica", "B", 10)
        pdf.set_text_color(30, 41, 59)
        write_pdf_block(pdf, f"Likely Reason: {cause}", line_h=5.5)
        pdf.set_font("Helvetica", "", 10)
        write_pdf_block(pdf, why.get("explanation", ""), line_h=5.5)
        if why.get("tip"):
            pdf.set_text_color(100, 116, 139)
            write_pdf_block(pdf, f"Prompt Tip: {why.get('tip', '')}", line_h=5)

    if brief.get("recommendations"):
        section_banner(pdf, "6. Recommendations & Next Steps", rgb=(15, 118, 110))
        pdf.set_font("Helvetica", "", 10)
        pdf.set_text_color(30, 41, 59)
        for rec in brief["recommendations"]:
            write_pdf_block(pdf, f"  * {rec}", line_h=5.5)

    pdf.ln(4)
    pdf.set_font("Helvetica", "I", 8.5)
    pdf.set_text_color(148, 163, 184)
    write_pdf_block(
        pdf,
        "Generated by Stale-Answer Detector (Powered by Tavily Live Search & Bifrost AI Gateway). "
        "Always verify critical decisions via the linked primary sources.",
        line_h=4.5,
    )

    return bytes(pdf.output())


def run_check(answer, key, backup_already_used=False):
    try:
        with st.spinner("Searching the live web and checking each claim..."):
            results = check_answer(answer)
    except Exception as ex:
        st.error("Something went wrong: " + str(ex) + " (Is Bifrost still running?)")
        return
    st.session_state[key] = {
        "answer": answer,
        "results": results,
        "why": None,
        "pdf_bytes": None,
        "backup": backup_already_used or was_backup_used(),
    }


def show(key, allow_why=True, pdf_section="2. Checked Content"):
    data = st.session_state.get(key)
    if not data:
        return
    results = data["results"]
    if not results:
        st.info("No time-sensitive claims found. General or timeless facts do not change over time, so no live web search was needed.")
        return

    levels = [level(to_score(r.get("score"))) for r in results]
    outdated = levels.count("Outdated")
    unclear = levels.count("Unclear")
    if outdated == 0 and unclear == 0:
        verdict = "Up to date"
    elif outdated == len(levels):
        verdict = "Outdated"
    else:
        verdict = "Mixed"

    c1, c2, c3 = st.columns(3)
    c1.markdown(tile("Claims checked", len(results), "#5EEAD4"), unsafe_allow_html=True)
    c2.markdown(tile("Possibly outdated", outdated + unclear, "#FDBA74"), unsafe_allow_html=True)
    c3.markdown(tile("Verdict", verdict, "#5EEAD4"), unsafe_allow_html=True)

    heading("Claim by claim", "#5EEAD4")
    for r, lv in zip(results, levels):
        src_html = ""
        if r.get("source_url"):
            src_html = f'<div style="margin-top:8px;"><a href="{hx(r["source_url"])}" target="_blank" style="color:#5EEAD4;font-size:13px;text-decoration:none;">Source link &rarr;</a></div>'
        st.markdown(
            f"""
            <div style="border:1px solid rgba(94, 234, 212, 0.45);border-radius:10px;
                        padding:14px 16px;margin-bottom:10px;background:rgba(20, 184, 166, 0.04);
                        box-shadow:0 0 8px rgba(20, 184, 166, 0.08);">
              <div style="display:flex;justify-content:space-between;align-items:flex-start;gap:10px;">
                <div style="font-size:15px;font-weight:700;color:#5EEAD4;">{hx(r.get("claim", ""))}</div>
                <div>{badge(lv)}</div>
              </div>
              <div style="font-size:14px;margin-top:6px;color:#E5E7EB;">{hx(r.get("reason", ""))}</div>
              {src_html}
            </div>
            """,
            unsafe_allow_html=True,
        )

    to_fix = [(r, lv) for r, lv in zip(results, levels) if lv != "Fresh"]
    if to_fix:
        heading("Correct answers", "#4ADE80")
        for r, lv in to_fix:
            fix = r.get("current_info") or NOT_CONFIRMED
            with st.container(border=True):
                st.markdown('<div style="font-size:13px;opacity:0.8;">Instead of: '
                            + hx(r.get("claim", "")) + '</div>', unsafe_allow_html=True)
                st.success(md(fix))
                if r.get("source_url"):
                    st.markdown("[Source](" + str(r["source_url"]) + ")")

    if allow_why:
        heading("Why did the AI go wrong?", "#93C5FD")
        asked = st.text_input("The question you asked the AI", key=key + "_q")
        expected = st.text_input("What you expected to see", key=key + "_e")
        if st.button("Find the likely reason", key=key + "_why_btn"):
            try:
                with st.spinner("Thinking..."):
                    data["why"] = explain_failure(asked, expected, data["answer"], results)
                    data["pdf_bytes"] = None
            except Exception as ex:
                st.error("Something went wrong: " + str(ex))
        why = data.get("why")
        if why:
            cause = CAUSES.get(why.get("cause"), "Not clear")
            st.markdown("**Likely reason:** " + cause)
            st.write(md(why.get("explanation", "")))
            if why.get("tip"):
                st.caption("Tip for next time: " + md(why["tip"]))
    else:
        why = None

    heading("Export Detailed Report", "#5EEAD4")
    b1, b2 = st.columns(2)
    if not data.get("pdf_bytes"):
        if b1.button("Generate Detailed PDF Report", key=key + "_gen_pdf"):
            with st.spinner("Adding topic background, key insights & formatting PDF..."):
                brief = generate_topic_brief(data["answer"], results)
                data["pdf_bytes"] = build_pdf_report(
                    data["answer"], results, levels, verdict, why, brief, section_title=pdf_section
                )
            st.rerun()
    else:
        b1.download_button(
            "Download Detailed PDF",
            data=data["pdf_bytes"],
            file_name="stale_detector_detailed_report.pdf",
            mime="application/pdf",
            key=key + "_dl",
        )

    if b2.button("Check another", key=key + "_reset"):
        st.session_state[key] = None
        if key == "audit":
            st.session_state["asked"] = None
            st.session_state["ask_backup"] = False
        st.rerun()
    st.caption("Searched via Tavily. Analyzed via Bifrost.")


# --- HEADER ---
if "mode" not in st.session_state:
    st.session_state["mode"] = "ask"
mode = st.session_state["mode"]

show_backup = False
if mode == "ask":
    show_backup = st.session_state.get("ask_backup", False) or (st.session_state.get("audit") or {}).get("backup", False)
elif mode == "check":
    show_backup = (st.session_state.get("paste") or {}).get("backup", False)
elif mode == "doc":
    show_backup = (st.session_state.get("doc") or {}).get("backup", False)

backup_pill = ""
if show_backup:
    backup_pill = (
        '<div style="background:rgba(20,184,166,0.16);color:#5EEAD4;padding:4px 12px;'
        'border:1px solid rgba(94,234,212,0.5);border-radius:20px;font-size:12px;font-weight:600;">'
        'Answered by backup model</div>'
    )

st.markdown(
    f"""
    <div style="display:flex;align-items:center;justify-content:space-between;gap:10px;">
      <div style="display:flex;align-items:center;gap:12px;">
        <div style="width:40px;height:40px;border-radius:10px;background:#0D9488;color:#FFFFFF;
                    border:1px solid #5EEAD4;
                    display:flex;align-items:center;justify-content:center;
                    font-size:21px;font-weight:800;">S</div>
        <span style="font-size:30px;font-weight:700;color:#5EEAD4;">Stale-answer detector</span>
      </div>
      {backup_pill}
    </div>
    """,
    unsafe_allow_html=True,
)
st.caption("Catch outdated facts in AI answers. We check each claim on the live web "
           "and show the correct information.")

m1, m2, m3, m4 = st.columns(4)
if m1.button("Ask a Question", key="mode_ask",
             type="primary" if mode == "ask" else "secondary"):
    st.session_state["mode"] = "ask"
    st.rerun()
if m2.button("Check an Answer", key="mode_check",
             type="primary" if mode == "check" else "secondary"):
    st.session_state["mode"] = "check"
    st.rerun()
if m3.button("Check a Document", key="mode_doc",
             type="primary" if mode == "doc" else "secondary"):
    st.session_state["mode"] = "doc"
    st.rerun()
if m4.button("Compare AI Models", key="mode_compare",
             type="primary" if mode == "compare" else "secondary"):
    st.session_state["mode"] = "compare"
    st.rerun()

if mode == "ask":
    st.caption("Ask any question. We get the AI's answer and check if its facts are still true today.")
    question = st.text_input(
        "Ask any question",
        value="How much does ChatGPT Plus cost and what is the latest Python version?")
    if st.button("Ask & Check Now", type="primary", key="btn2"):
        if question.strip():
            reply = None
            with st.spinner("Getting the AI's answer..."):
                try:
                    reply = answer_question(question)
                except Exception as ex:
                    st.error("Something went wrong: " + str(ex))
            if reply:
                b_used = was_backup_used()
                st.session_state["asked"] = reply
                st.session_state["ask_backup"] = b_used
                run_check(reply, "audit", backup_already_used=b_used)
        else:
            st.warning("Type a question first.")
    if st.session_state.get("asked"):
        st.markdown("**The AI's original answer**")
        st.write(md(st.session_state["asked"]))
    show("audit")

elif mode == "check":
    st.caption("Paste an AI-generated answer below, then click Check Now.")
    answer = st.text_area("AI-generated answer", value=SAMPLE, height=150,
                          label_visibility="collapsed")
    if st.button("Check Now", type="primary", key="btn1"):
        if answer.strip():
            run_check(answer, "paste")
        else:
            st.warning("Paste an answer first.")
    show("paste")

elif mode == "doc":
    st.caption("Upload a .pdf or .txt file (up to 12 time-sensitive claims checked per document).")
    uploaded = st.file_uploader("Upload a PDF or TXT file", type=["pdf", "txt"], label_visibility="collapsed")
    if uploaded is not None:
        if st.button("Check Document Now", type="primary", key="btn_doc"):
            try:
                with st.spinner("Reading document and finding time-sensitive claims..."):
                    doc_text = read_document_text(uploaded)
                    if not doc_text:
                        st.warning("Could not read any text from this file.")
                        claims = []
                    else:
                        claims = extract_document_claims(doc_text, max_total=12)
                if claims:
                    progress = st.progress(0, text=f"Checking claim 1 of {len(claims)}...")
                    doc_results = []
                    for i, c in enumerate(claims):
                        progress.progress((i) / len(claims), text=f"Checking claim {i + 1} of {len(claims)}...")
                        doc_results.append(verify_claim_item(c))
                    progress.progress(1.0, text="Done!")
                    progress.empty()
                    summary_text = f"Document: {uploaded.name}\n\n{doc_text[:1200]}"
                    st.session_state["doc"] = {
                        "answer": summary_text,
                        "results": doc_results,
                        "why": None,
                        "pdf_bytes": None,
                        "backup": was_backup_used(),
                    }
                elif doc_text:
                    st.session_state["doc"] = {
                        "answer": f"Document: {uploaded.name}",
                        "results": [],
                        "why": None,
                        "pdf_bytes": None,
                        "backup": was_backup_used(),
                    }
            except Exception as ex:
                st.error("Document check failed: " + str(ex))
    show("doc", allow_why=False, pdf_section="2. Checked Document Excerpt")

elif mode == "compare":
    st.caption(
        "Head-to-head freshness benchmark across 8 time-sensitive questions using Bifrost AI Gateway & Tavily."
    )
    saved = load_benchmark()
    btn_label = "Re-run Model Benchmark (8 Questions)" if saved else "Run Model Benchmark (8 Questions)"
    if st.button(btn_label, type="primary", key="btn_bench"):
        models = [PRIMARY_MODEL, BACKUP_MODEL]
        prog = st.progress(0, text="Starting benchmark...")
        rows = []
        for idx, q in enumerate(BENCHMARK_QUESTIONS):
            prog.progress(idx / len(BENCHMARK_QUESTIONS),
                          text=f"Testing question {idx + 1} of {len(BENCHMARK_QUESTIONS)}: {q[:45]}...")
            rows.append(evaluate_single_benchmark_question(q, models=models))
        prog.progress(1.0, text="Saving benchmark results...")
        saved = save_benchmark(rows, models=models)
        prog.empty()
        st.rerun()

    if not saved:
        st.info(
            "Click **Run Model Benchmark (8 Questions)** once to test "
            f"`{PRIMARY_MODEL}` vs `{BACKUP_MODEL}` against the live web. "
            "Results are saved locally so future visits load immediately."
        )
    else:
        st.caption(f"Last benchmark run: {saved.get('run_date', 'Today')}  |  Questions tested: {len(saved.get('rows', []))}")
        models = saved.get("models", [PRIMARY_MODEL, BACKUP_MODEL])
        summary = saved.get("summary", {})

        cols = st.columns(len(models))
        for col, m in zip(cols, models):
            s = summary.get(m, {})
            short_name = m.split("/")[-1]
            col.markdown(
                tile(
                    short_name,
                    f"{s.get('fresh_pct', 0)}% Fresh  |  {s.get('outdated_pct', 0)}% Outdated",
                    "#5EEAD4",
                ),
                unsafe_allow_html=True,
            )

        heading("Freshness Accuracy Comparison (%)", "#5EEAD4")
        chart_rows = []
        for m in models:
            s = summary.get(m, {})
            short_name = m.split("/")[-1]
            fresh_w = s.get("fresh_pct", 0)
            out_w = s.get("outdated_pct", 0)
            unc_w = max(0, 100 - fresh_w - out_w)
            chart_rows.append(
                f"""
                <div style="margin-bottom:12px;">
                  <div style="display:flex;justify-content:space-between;font-size:13px;margin-bottom:4px;">
                    <strong style="color:#F8FAFC;">{hx(short_name)}</strong>
                    <span style="color:#94A3B8;">Fresh: {fresh_w}% &bull; Outdated: {out_w}% &bull; Unclear: {unc_w}%</span>
                  </div>
                  <div style="width:100%;height:16px;border-radius:8px;overflow:hidden;display:flex;background:#1E293B;">
                    <div style="width:{fresh_w}%;background:#22C55E;" title="Fresh {fresh_w}%"></div>
                    <div style="width:{out_w}%;background:#EF4444;" title="Outdated {out_w}%"></div>
                    <div style="width:{unc_w}%;background:#F59E0B;" title="Unclear {unc_w}%"></div>
                  </div>
                </div>
                """
            )
        st.markdown(
            '<div style="border:1px solid rgba(94, 234, 212, 0.45);border-radius:10px;'
            'padding:14px 16px;background:rgba(20, 184, 166, 0.04);">'
            + "".join(chart_rows)
            + "</div>",
            unsafe_allow_html=True,
        )

        heading("Question-by-Question Results", "#5EEAD4")
        for idx, r in enumerate(saved.get("rows", []), start=1):
            with st.container(border=True):
                st.markdown(f"**Q{idx}: {hx(r.get('question', ''))}**")
                for m in models:
                    m_info = r.get("models", {}).get(m, {})
                    short_name = m.split("/")[-1]
                    st_name = m_info.get("status", "Unclear")
                    st.markdown(
                        f'<div style="display:flex;justify-content:space-between;align-items:center;margin-top:6px;">'
                        f'<span style="color:#5EEAD4;font-weight:600;">{hx(short_name)}</span>'
                        f'{badge(st_name)}</div>',
                        unsafe_allow_html=True,
                    )
                    st.caption(md(m_info.get("answer", "")))