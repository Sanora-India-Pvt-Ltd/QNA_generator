import streamlit as st
import json
import logging

# -----------------------------
# SILENCE WEBSOCKET NOISE
# -----------------------------
logging.getLogger("tornado").setLevel(logging.ERROR)

# -----------------------------
# PAGE CONFIG
# -----------------------------
st.set_page_config(
    page_title="Ulearn And Earn MCQ Quiz",
    page_icon="🧠",
    layout="centered"
)

st.title("🧠 Ulearn And Earn MCQ Quiz")
st.caption("Generated automatically from YouTube content")

# -----------------------------
# LOAD JSON
# -----------------------------
@st.cache_data
def load_questions():
    with open("quiz_results.json", "r", encoding="utf-8") as f:
        data = json.load(f)
    return data["questions"]

questions = load_questions()
total_questions = len(questions)

# -----------------------------
# SESSION STATE INIT
# -----------------------------
if "index" not in st.session_state:
    st.session_state.index = 0
    st.session_state.score = 0
    st.session_state.show_result = False
    st.session_state.selected = None
    st.session_state.answered = False  # ✅ NEW

# =============================
# QUIZ LOGIC
# =============================
if st.session_state.index < total_questions:
    q = questions[st.session_state.index]

    st.subheader(f"Question {st.session_state.index + 1} of {total_questions}")
    st.write(q["question"])

    options = q["options"]

    st.session_state.selected = st.radio(
        "Choose your answer:",
        options=list(options.keys()),
        format_func=lambda x: f"{x}. {options[x]}",
        key=f"radio_{st.session_state.index}",
        disabled=st.session_state.answered  # ✅ disable after submit
    )

    # -----------------------------
    # SUBMIT BUTTON
    # -----------------------------
    if st.button("Submit Answer", disabled=st.session_state.answered):
        st.session_state.show_result = True
        st.session_state.answered = True

        if st.session_state.selected == q["correct_answer"]:
            st.session_state.score += 1

    # -----------------------------
    # RESULT FEEDBACK
    # -----------------------------
    if st.session_state.show_result:
        correct = q["correct_answer"]

        if st.session_state.selected == correct:
            st.success("✅ Correct Answer!")
        else:
            st.error(f"❌ Wrong Answer. Correct is **{correct}**")

        if q.get("explanation"):
            st.info(f"ℹ {q['explanation']}")

        if st.button("Next Question"):
            st.session_state.index += 1
            st.session_state.show_result = False
            st.session_state.selected = None
            st.session_state.answered = False
            try:
                st.rerun()
            except Exception:
                pass

# =============================
# FINAL RESULT (TOTAL SCORE)
# =============================
else:
    correct = st.session_state.score
    wrong = total_questions - correct
    percentage = (correct / total_questions) * 100 if total_questions else 0

    st.balloons()
    st.success("🎉 Quiz Completed!")

    st.markdown("### 📊 Final Result Summary")
    st.write(f"**Total Questions:** {total_questions}")
    st.write(f"**Correct Answers:** {correct}")
    st.write(f"**Wrong Answers:** {wrong}")
    st.write(f"**Score:** {correct} / {total_questions}")
    st.write(f"**Percentage:** {percentage:.2f}%")

    if st.button("Restart Quiz"):
        st.session_state.clear()   # ✅ SAFE RESET
        try:
            st.rerun()
        except Exception:
            pass
