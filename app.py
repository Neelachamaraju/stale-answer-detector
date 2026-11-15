import html
import streamlit as st
from core import check_answer, answer_question, explain_failure

st.set_page_config(page_title="Stale-answer detector")

st.markdown(
    """
    <style>
    .block-container { max-width: 760px; padding-top: 2rem; padding-bottom: 3rem; }
    [data-testid="stVerticalBlock"] { gap: 1rem; }
    [data-testid="stHorizontalBlock"] { gap: 1rem; }
    .stApp p, .stApp li, .stApp label { font-size: 14px; }
    .stButton button, .stDownloadButton button { font-size: 0.95rem; padding: 0.5rem 1.2rem; border-radius: 8px; }
    textarea { font-size: 0.95rem !important; }
    </style>
    """,
    unsafe_allow_html=True,
)

st.markdown(
    """
    <div style="display:flex;align-items:center;gap:10px;">
      <div style="width:38px;height:38px;border-radius:9px;background:#534AB7;color:#ffffff;
                  display:flex;align-items:center;justify-content:center;
                  font-size:20px;font-weight:700;">S</div>
      <span style="font-size:30px;font-weight:700;color:#A78BFA;">Stale-answer detector</span>
    </div>
    """,
    unsafe_allow_html=True,
)
st.caption("Catch outdated facts in AI answers. We check each claim on the live web "
           "and show the correct information.")

SAMPLE = ("The CEO of Twitter is Parag Agrawal. "
          "Python 3.9 is the latest version of Python. "
          "ChatGPT Plus costs $20 per month.")

COLORS = {
    "Fresh": ("#EAF3DE", "#27500A"),
    "Unclear": ("#FAEEDA", "#633806"),
    "Outdated": ("#FCEBEB", "#791F1F"),
}
CAUSES = {
    "unclear_question": "The question was unclear or missing details",
    "outdated_knowledge": "The AI used outdated knowledge",
    "ai_mistake": "The AI made a mistake or invented something",
    "answer_looks_fine": "The answer looks fine",
}
NOT_CONFIRMED = "Could not confirm the latest information. Check the source link."


def md(text):
    """Safe text for st.write / st.success (stops $ from turning into maths)."""
    return str(text).replace("$", "\\$")


def hx(text):
    """Safe text inside our own HTML."""
    return html.escape(str(text)).replace("$", "&#36;")


def heading(text, color):
    st.markdown('<div style="font-size:17px;font-weight:700;color:' + color
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
    bg, fg = COLORS[name]
    return ('<span style="background:' + bg + ';color:' + fg + ';padding:2px 8px;'
            'border-radius:6px;font-size:12px;font-weight:600;">' + name + '</span>')


def tile(label, value, color):
    return ('<div style="border:1px solid rgba(128,128,128,0.35);border-radius:10px;'
            'padding:10px 12px;">'
            '<div style="font-size:15px;font-weight:700;color:' + color + ';">' + label + '</div>'
            '<div style="font-size:12px;margin-top:4px;">' + hx(value) + '</div></div>')


def run_check(answer, key):
    try:
        with st.spinner("Searching the live web and checking each claim..."):
            results = check_answer(answer)
    except Exception as ex:
        st.error("Something went wrong: " + str(ex) + " (Is Bifrost still running?)")
        return
    st.session_state[key] = {"answer": answer, "results": results, "why": None}


def show(key):
    data = st.session_state.get(key)
    if not data:
        return
    results = data["results"]
    if not results:
        st.success("No time-sensitive claims found in this answer.")
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
    c1.markdown(tile("Claims checked", len(results), "#A78BFA"), unsafe_allow_html=True)
    c2.markdown(tile("Possibly outdated", outdated + unclear, "#FDBA74"), unsafe_allow_html=True)
    c3.markdown(tile("Verdict", verdict, "#2DD4BF"), unsafe_allow_html=True)

    report = ["STALE-ANSWER DETECTOR REPORT", "", "Original answer:", data["answer"], ""]

    heading("Claim by claim", "#C4B5FD")
    for r, lv in zip(results, levels):
        with st.container(border=True):
            st.markdown('<div style="font-size:15px;font-weight:700;color:#C4B5FD;">'
                        + hx(r.get("claim", "")) + '</div>', unsafe_allow_html=True)
            st.markdown(badge(lv), unsafe_allow_html=True)
            st.markdown('<div style="font-size:13px;">' + hx(r.get("reason", "")) + '</div>',
                        unsafe_allow_html=True)
            if r.get("source_url"):
                st.markdown("[Source](" + str(r["source_url"]) + ")")
        report += ["[" + lv + "] " + str(r.get("claim", "")),
                   "  Reason: " + str(r.get("reason", "")),
                   "  Source: " + str(r.get("source_url", "")), ""]

    to_fix = [(r, lv) for r, lv in zip(results, levels) if lv != "Fresh"]
    if to_fix:
        heading("Correct answers", "#4ADE80")
        report += ["CORRECT ANSWERS", ""]
        for r, lv in to_fix:
            fix = r.get("current_info") or NOT_CONFIRMED
            with st.container(border=True):
                st.markdown('<div style="font-size:13px;opacity:0.8;">Instead of: '
                            + hx(r.get("claim", "")) + '</div>', unsafe_allow_html=True)
                st.success(md(fix))
                if r.get("source_url"):
                    st.markdown("[Source](" + str(r["source_url"]) + ")")
            report += ["Instead of: " + str(r.get("claim", "")),
                       "  Correct answer: " + str(fix),
                       "  Source: " + str(r.get("source_url", "")), ""]

    heading("Why did the AI go wrong?", "#93C5FD")
    asked = st.text_input("The question you asked the AI", key=key + "_q")
    expected = st.text_input("What you expected to see", key=key + "_e")
    if st.button("Find the likely reason", key=key + "_why_btn"):
        try:
            with st.spinner("Thinking..."):
                data["why"] = explain_failure(asked, expected, data["answer"], results)
        except Exception as ex:
            st.error("Something went wrong: " + str(ex))
    why = data.get("why")
    if why:
        cause = CAUSES.get(why.get("cause"), "Not clear")
        st.markdown("**Likely reason:** " + cause)
        st.write(md(why.get("explanation", "")))
        if why.get("tip"):
            st.caption("Tip for next time: " + md(why["tip"]))
        report += ["Likely reason: " + cause, str(why.get("explanation", "")), ""]

    b1, b2 = st.columns(2)
    b1.download_button("Download my report", "\n".join(report),
                       file_name="freshness_report.txt", key=key + "_dl")
    if b2.button("Check another", key=key + "_reset"):
        st.session_state[key] = None
        if key == "audit":
            st.session_state["asked"] = None
        st.rerun()
    st.caption("Searched via Tavily. Analyzed via Bifrost.")


if "mode" not in st.session_state:
    st.session_state["mode"] = "check"
mode = st.session_state["mode"]

m1, m2 = st.columns(2)
if m1.button("Check freshness", key="mode_check",
             type="primary" if mode == "check" else "secondary"):
    st.session_state["mode"] = "check"
    st.rerun()
if m2.button("Ask and audit", key="mode_ask",
             type="primary" if mode == "ask" else "secondary"):
    st.session_state["mode"] = "ask"
    st.rerun()

if mode == "check":
    st.caption("Paste an AI-generated answer below, then tap Check now.")
    answer = st.text_area("AI-generated answer", value=SAMPLE, height=150,
                          label_visibility="collapsed")
    if st.button("Check now", type="primary", key="btn1"):
        if answer.strip():
            run_check(answer, "paste")
        else:
            st.warning("Paste an answer first.")
    show("paste")
else:
    st.caption("Ask any question. We get the AI's answer and audit it for outdated facts.")
    question = st.text_input(
        "Ask any question",
        value="How much does ChatGPT Plus cost and what is the latest Python version?")
    if st.button("Ask AI and audit its answer", type="primary", key="btn2"):
        if question.strip():
            reply = None
            with st.spinner("Getting the AI's answer..."):
                try:
                    reply = answer_question(question)
                except Exception as ex:
                    st.error("Something went wrong: " + str(ex))
            if reply:
                st.session_state["asked"] = reply
                run_check(reply, "audit")
        else:
            st.warning("Type a question first.")
    if st.session_state.get("asked"):
        st.markdown("**The AI's original answer**")
        st.write(md(st.session_state["asked"]))
    show("audit")