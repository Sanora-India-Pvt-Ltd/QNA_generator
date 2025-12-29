import streamlit as st
import json
import logging
import os

# -----------------------------
# SILENCE WEBSOCKET NOISE
# -----------------------------
logging.getLogger("tornado").setLevel(logging.ERROR)
logging.getLogger("streamlit").setLevel(logging.ERROR)

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
    """Load questions from quiz_results.json with error handling"""
    json_path = "quiz_results.json"
    
    if not os.path.exists(json_path):
        st.error(f"❌ File not found: {json_path}")
        st.info("💡 Please run the quiz generator first to create quiz_results.json")
        return []
    
    try:
        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        questions = data.get("questions", [])
        
        # Validate questions structure
        valid_questions = []
        for i, q in enumerate(questions):
            if not isinstance(q, dict):
                continue
            if "question" not in q or "options" not in q or "correct_answer" not in q:
                st.warning(f"⚠ Question {i+1} is missing required fields, skipping...")
                continue
            
            # Ensure options is a dict
            if not isinstance(q.get("options"), dict):
                continue
            
            # Ensure correct_answer is valid
            if q.get("correct_answer") not in q.get("options", {}):
                st.warning(f"⚠ Question {i+1} has invalid correct_answer, skipping...")
                continue
            
            valid_questions.append(q)
        
        return valid_questions
    
    except json.JSONDecodeError as e:
        st.error(f"❌ Invalid JSON in {json_path}: {e}")
        return []
    except Exception as e:
        st.error(f"❌ Error loading questions: {e}")
        return []

questions = load_questions()
total_questions = len(questions)

# -----------------------------
# CHECK IF QUESTIONS LOADED
# -----------------------------
if total_questions == 0:
    st.stop()

# -----------------------------
# SESSION STATE INIT
# -----------------------------
if "index" not in st.session_state:
    st.session_state.index = 0
    st.session_state.score = 0
    st.session_state.show_result = False
    st.session_state.selected = None
    st.session_state.answered = False

# =============================
# QUIZ LOGIC
# =============================
if st.session_state.index < total_questions:
    q = questions[st.session_state.index]

    st.subheader(f"Question {st.session_state.index + 1} of {total_questions}")
    st.write(f"**{q['question']}**")

    options = q["options"]
    
    # Ensure options are in order (A, B, C, D)
    option_keys = sorted(options.keys())

    st.session_state.selected = st.radio(
        "Choose your answer:",
        options=option_keys,
        format_func=lambda x: f"{x}. {options[x]}",
        key=f"radio_{st.session_state.index}",
        disabled=st.session_state.answered
    )

    # -----------------------------
    # SUBMIT BUTTON
    # -----------------------------
    col1, col2 = st.columns([1, 4])
    
    with col1:
        if st.button("Submit Answer", disabled=st.session_state.answered, use_container_width=True):
            st.session_state.show_result = True
            st.session_state.answered = True

            if st.session_state.selected == q["correct_answer"]:
                st.session_state.score += 1

    # -----------------------------
    # RESULT FEEDBACK
    # -----------------------------
    if st.session_state.show_result:
        correct = q["correct_answer"]
        selected = st.session_state.selected

        st.divider()
        
        if selected == correct:
            st.success(f"✅ **Correct Answer!** ({correct})")
        else:
            st.error(f"❌ **Wrong Answer.** Correct answer is **{correct}**")
            if selected:
                st.info(f"Your answer: **{selected}**")

        if q.get("explanation"):
            st.info(f"💡 **Explanation:** {q['explanation']}")

        st.divider()
        
        # Next Question Button
        if st.button("Next Question ➡️", use_container_width=True):
            st.session_state.index += 1
            st.session_state.show_result = False
            st.session_state.selected = None
            st.session_state.answered = False
            st.rerun()

# =============================
# FINAL RESULT (TOTAL SCORE)
# =============================
else:
    correct = st.session_state.score
    wrong = total_questions - correct
    percentage = (correct / total_questions) * 100 if total_questions else 0

    st.balloons()
    st.success("🎉 **Quiz Completed!**")

    st.markdown("### 📊 Final Result Summary")
    
    # Create columns for better layout
    col1, col2 = st.columns(2)
    
    with col1:
        st.metric("Total Questions", total_questions)
        st.metric("Correct Answers", correct, delta=f"{percentage:.1f}%")
    
    with col2:
        st.metric("Wrong Answers", wrong)
        st.metric("Score", f"{correct}/{total_questions}")
    
    # Progress bar
    st.progress(percentage / 100)
    st.caption(f"**Percentage:** {percentage:.2f}%")
    
    # Performance message
    if percentage >= 90:
        st.success("🌟 **Excellent!** Outstanding performance!")
    elif percentage >= 70:
        st.info("👍 **Good job!** Well done!")
    elif percentage >= 50:
        st.warning("📚 **Keep practicing!** You're getting there!")
    else:
        st.error("💪 **Don't give up!** Review the material and try again!")

    st.divider()
    
    if st.button("🔄 Restart Quiz", use_container_width=True):
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.rerun()

