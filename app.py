import streamlit as st
import google.generativeai as genai
from dotenv import load_dotenv
import os
import re

# --- Setup ---
load_dotenv()
genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))
model = genai.GenerativeModel("gemini-2.0-flash")

st.set_page_config(page_title="AI Science Explainer", page_icon="🧠")
st.title("🧠 AI Science Explainer + Quiz (Gemini 2.0 Flash)")

# --- User Input ---
topic = st.text_input("🎓 Enter a science topic:", placeholder="e.g., Photosynthesis")
level = st.selectbox("📘 Select difficulty:", ["Beginner", "Intermediate", "Advanced"])

# --- Initialize session state ---
if "explanation" not in st.session_state:
    st.session_state.explanation = ""
if "quiz" not in st.session_state:
    st.session_state.quiz = {}
if "quiz_answer" not in st.session_state:
    st.session_state.quiz_answer = None
if "history" not in st.session_state:
    st.session_state.history = []  # 🧠 Keeps all generated responses

# --- Generate Explanation + Quiz ---
if st.button("✨ Generate Explanation and Quiz"):
    if topic:
        with st.spinner("🤖 Generating your explanation and quiz... please wait ⏳"):
            prompt = f"""
            You are a science teacher explaining the topic '{topic}' at a {level} level.

            Please provide:
            1. A clear explanation suitable for {level} level.
            2. One multiple-choice quiz question with four options labeled A), B), C), D).
            3. The correct answer in the format: Answer: (letter).

            Format your response exactly like this:

            EXPLANATION:
            [Your explanation here]

            QUESTION:
            [Your multiple-choice question here]

            OPTIONS:
            A) [Option A]
            B) [Option B]
            C) [Option C]
            D) [Option D]

            ANSWER:
            (Correct letter)
            """

            try:
                response = model.generate_content(prompt)

                # --- Safe Gemini 2.0 text extraction ---
                try:
                    if hasattr(response, "text") and response.text:
                        text = response.text
                    else:
                        text = response.candidates[0].content.parts[0].text
                except Exception:
                    text = ""

                if not text:
                    st.error("⚠️ No explanation returned by the model. Try again.")
                    st.stop()

                # --- Debug: Raw AI Output ---
                with st.expander("🔍 Raw AI Response (Debug View)"):
                    st.text_area("Raw Response", text, height=200)

                # --- Improved Parsing Logic ---
                explanation, question, options, answer = "", "", [], ""
                sections = text.split("\n\n")

                for section in sections:
                    lines = section.strip().split("\n")
                    if not lines:
                        continue

                    first_line = lines[0].lower()

                    if "explanation" in first_line:
                        explanation_lines = []
                        for line in lines[1:]:
                            if line.strip() and not any(
                                keyword in line.lower() for keyword in ["question", "options", "answer"]
                            ):
                                explanation_lines.append(line.strip())
                        explanation = " ".join(explanation_lines) if explanation_lines else " ".join(lines)

                    elif "question" in first_line:
                        question = (
                            " ".join(lines[1:]) if len(lines) > 1 else lines[0].split(":", 1)[-1].strip()
                        )

                    elif "options" in first_line or any(
                        line.strip().startswith(("A)", "B)", "C)", "D)")) for line in lines
                    ):
                        for line in lines:
                            line = line.strip()
                            if line.startswith(("A)", "B)", "C)", "D)")):
                                options.append(line)

                    elif "answer" in first_line:
                        for line in lines:
                            if "answer" in line.lower():
                                match = re.search(r"\(([A-D])\)", line.upper())
                                if match:
                                    answer = match.group(1)
                                else:
                                    match = re.search(r"[A-D]", line.upper())
                                    if match:
                                        answer = match.group(0)

                # --- Fallback Parsing ---
                if not explanation:
                    parts = text.split("QUESTION:")
                    if len(parts) > 1:
                        explanation = parts[0].replace("EXPLANATION:", "").strip()

                if not question:
                    question_match = re.search(
                        r"QUESTION:\s*(.*?)(?=OPTIONS:|ANSWER:|$)", text, re.IGNORECASE | re.DOTALL
                    )
                    if question_match:
                        question = question_match.group(1).strip()

                if not options:
                    options = re.findall(r"^[A-D]\)\s*.+$", text, re.MULTILINE)

                if not answer:
                    answer_match = re.search(r"ANSWER:\s*\(?([A-D])\)?", text, re.IGNORECASE)
                    if answer_match:
                        answer = answer_match.group(1)
                    else:
                        answer = "A"

                # --- Final Fallback Defaults ---
                if not explanation:
                    explanation = "No explanation generated. Please try again."
                if not question:
                    question = "Test your understanding:"
                if not options:
                    options = ["A) Option A", "B) Option B", "C) Option C", "D) Option D"]

                # --- Save to Session State ---
                st.session_state.explanation = explanation
                st.session_state.quiz = {"question": question, "options": options, "answer": answer}
                st.session_state.quiz_answer = None

                # --- Save to History ---
                if explanation and explanation != "No explanation generated. Please try again.":
                    st.session_state.history.append(
                        {"topic": topic, "level": level, "explanation": explanation}
                    )
                    st.toast(f"💾 Saved '{topic}' to your learning history!", icon="💡")

                st.success("✅ Explanation and quiz generated successfully!")

            except Exception as e:
                st.error(f"⚠️ API Error: {e}")
                st.error("Full error details:", str(e))
    else:
        st.warning("Please enter a topic first.")

st.divider()

# --- Display Explanation ---
if st.session_state.explanation:
    st.header(f"📖 {level} Explanation")
    st.write(st.session_state.explanation)

# --- Display Quiz ---
if st.session_state.quiz and st.session_state.quiz.get("options"):
    quiz = st.session_state.quiz
    st.subheader("🧩 Quick Quiz")
    st.write(f"**{quiz['question']}**")

    user_choice = st.radio("Choose your answer:", quiz["options"], key="quiz_choice")

    if st.button("Submit Answer"):
        st.session_state.quiz_answer = user_choice

    if st.session_state.quiz_answer:
        correct_letter = quiz.get("answer", "A").upper().strip()

        user_match = re.match(
            r"^([A-D])[\)\.\:]\s*", st.session_state.quiz_answer.strip().upper()
        )
        user_letter = user_match.group(1) if user_match else None

        if user_letter == correct_letter:
            st.success("✅ Correct! Well done!")
        else:
            st.error(f"❌ Not quite! The correct answer was: **{correct_letter})**")

st.divider()

# --- Display Learning History ---
st.header("🕒 Previous Explanations")

if st.session_state.history:
    st.write(f"📚 You have **{len(st.session_state.history)}** saved explanations this session.")
    for i, record in enumerate(reversed(st.session_state.history), start=1):
        with st.expander(f"{i}. {record['topic']} ({record['level']})"):
            st.write(record["explanation"])
else:
    st.info("No previous explanations yet. Generate one above to start your learning log! 📖")
