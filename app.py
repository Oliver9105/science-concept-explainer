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

# --- Session State ---
if "explanation" not in st.session_state:
    st.session_state.explanation = ""
if "quiz" not in st.session_state:
    st.session_state.quiz = {}
if "quiz_answer" not in st.session_state:
    st.session_state.quiz_answer = None

# --- Generate Explanation + Quiz ---
if st.button("✨ Generate Explanation and Quiz"):
    if topic:
        prompt = f"""
        You are a science teacher explaining the topic '{topic}' at a {level} level.
        1️⃣ Write a clear explanation suitable for that level.
        2️⃣ Then create one multiple-choice quiz question with four options labeled A), B), C), D).
        3️⃣ Clearly mark the correct answer at the end in the exact format:
            Answer: (A/B/C/D)
        Example output:

        Explanation: <text>
        Question: <text>
        Options:
        A) ...
        B) ...
        C) ...
        D) ...
        Answer: (A)
        """

        try:
            response = model.generate_content(prompt)
            text = response.text

            # --- Robust Parsing ---
            explanation, question, options, answer = "", "", [], ""
            lines = [l.strip() for l in text.splitlines() if l.strip()]

            for line in lines:
                l = line.lower()
                if l.startswith("explanation:"):
                    explanation = line.split(":", 1)[1].strip()
                elif l.startswith("question:"):
                    question = line.split(":", 1)[1].strip()
                elif any(line.startswith(prefix) for prefix in ["A)", "B)", "C)", "D)"]):
                    options.append(line.strip())
                elif l.startswith("answer:"):
                    answer = line.split(":", 1)[1].strip().upper()

            # Fallbacks
            if not question and options:
                question = "Here’s a quick quiz based on the topic above!"
            if not answer:
                answer = "(A)"

            st.session_state.explanation = explanation
            st.session_state.quiz = {"question": question, "options": options, "answer": answer}
            st.session_state.quiz_answer = None
            st.success("✅ Explanation and quiz generated successfully!")

        except Exception as e:
            st.error(f"⚠️ API Error: {e}")
    else:
        st.warning("Please enter a topic first.")

st.divider()

# --- Display Explanation ---
if st.session_state.explanation:
    st.header(f"📖 {level} Explanation")
    st.write(st.session_state.explanation)

# --- Display Quiz ---
if st.session_state.quiz:
    quiz = st.session_state.quiz
    st.subheader("🧩 Quick Quiz")
    st.write(f"**{quiz['question']}**")

    if quiz["options"]:
        user_choice = st.radio("Choose your answer:", quiz["options"])
        if st.button("Submit Answer"):
            st.session_state.quiz_answer = user_choice

        # --- Robust Answer Evaluation ---
        if st.session_state.quiz_answer:
            raw_answer = quiz.get("answer", "").strip()
            # Extract the correct letter safely
            match = re.search(r"[A-D]", raw_answer.upper())
            correct_letter = match.group(0) if match else "A"

            # Extract first letter of user choice
            user_letter_match = re.match(r"([A-D])[\)\.\:]*", user_choice.strip().upper())
            user_letter = user_letter_match.group(1) if user_letter_match else None

            if user_letter == correct_letter:
                st.success("✅ Correct! Well done!")
            else:
                st.error(f"❌ Not quite! The correct answer was: **{raw_answer}**")

    else:
        st.warning("⚠️ No quiz options were generated. Try again.")
