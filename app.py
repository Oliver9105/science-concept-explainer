import streamlit as st
import google.generativeai as genai
from dotenv import load_dotenv
from gtts import gTTS
import os
import re
import tempfile

# --- Setup ---
load_dotenv()
genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))
model = genai.GenerativeModel("gemini-2.0-flash")

st.set_page_config(page_title="AI Science Explainer", page_icon="🧠")
st.title("🧠 AI Science Explainer + Audio Tutor (Gemini 2.0 Flash)")

# --- User Inputs ---
topic = st.text_input("🎓 Enter a science topic:", placeholder="e.g., Gravity")
level = st.selectbox("📘 Select difficulty:", ["Beginner", "Intermediate", "Advanced"])

# --- Initialize session state ---
if "explanation" not in st.session_state:
    st.session_state.explanation = ""
if "fun_facts" not in st.session_state:
    st.session_state.fun_facts = []
if "quizzes" not in st.session_state:
    st.session_state.quizzes = []
if "history" not in st.session_state:
    st.session_state.history = []

# --- Generate AI Content ---
if st.button("✨ Generate Lesson"):
    if topic:
        with st.spinner("🤖 Generating explanation, fun facts, and quiz..."):
            prompt = f"""
            You are a science teacher explaining the topic '{topic}' at a {level} level.

            Please respond in this exact structure:

            EXPLANATION:
            [Brief, clear explanation suitable for {level} learners]

            FUN FACTS:
            - [Fun fact #1]
            - [Fun fact #2]

            QUIZZES:
            QUESTION 1:
            [Question text]
            OPTIONS:
            A) ...
            B) ...
            C) ...
            D) ...
            ANSWER: (letter)

            QUESTION 2:
            [Question text]
            OPTIONS:
            A) ...
            B) ...
            C) ...
            D) ...
            ANSWER: (letter)

            QUESTION 3:
            [Question text]
            OPTIONS:
            A) ...
            B) ...
            C) ...
            D) ...
            ANSWER: (letter)
            """

            try:
                response = model.generate_content(prompt)
                try:
                    text = response.text if hasattr(response, "text") else response.candidates[0].content.parts[0].text
                except Exception:
                    text = ""

                if not text:
                    st.error("⚠️ No content generated. Try again.")
                    st.stop()

                # --- Parse Explanation + Fun Facts ---
                explanation_match = re.search(r"EXPLANATION:\s*(.*?)(?=FUN FACTS:|QUIZZES:|$)", text, re.DOTALL)
                fun_facts_match = re.search(r"FUN FACTS:\s*(.*?)(?=QUIZZES:|QUESTION 1:|$)", text, re.DOTALL)
                explanation = explanation_match.group(1).strip() if explanation_match else "No explanation generated."
                fun_facts = [f.strip("-• ").strip() for f in fun_facts_match.group(1).split("\n") if f.strip()] if fun_facts_match else []

                # --- Parse 3 Questions ---
                quiz_blocks = re.findall(r"(QUESTION\s*\d+:[\s\S]*?(?=(?:QUESTION\s*\d+:|$)))", text, re.IGNORECASE)
                quizzes = []

                for block in quiz_blocks:
                    q_match = re.search(r"QUESTION\s*\d*:\s*(.*?)(?=OPTIONS:|ANSWER:|$)", block, re.DOTALL | re.IGNORECASE)
                    opts = re.findall(r"^[A-D]\)\s*.*", block, re.MULTILINE)
                    ans_match = re.search(r"ANSWER:\s*\(?([A-D])\)?", block, re.IGNORECASE)
                    question = q_match.group(1).strip() if q_match else "Question unavailable."
                    answer = ans_match.group(1).upper() if ans_match else "A"
                    quizzes.append({"question": question, "options": opts, "answer": answer})

                # --- Save to session ---
                st.session_state.explanation = explanation
                st.session_state.fun_facts = fun_facts
                st.session_state.quizzes = quizzes

                # --- Save to history ---
                st.session_state.history.append({
                    "topic": topic,
                    "level": level,
                    "explanation": explanation,
                    "fun_facts": fun_facts,
                    "quizzes": quizzes
                })

                st.success("✅ Lesson generated successfully!")

            except Exception as e:
                st.error(f"API Error: {e}")
    else:
        st.warning("Please enter a topic first.")

st.divider()

# --- Display Explanation ---
if st.session_state.explanation:
    st.header(f"📖 {level} Explanation")
    st.write(st.session_state.explanation)

    # --- Text-to-Speech ---
    if st.button("🔊 Read Aloud"):
        try:
            tts = gTTS(st.session_state.explanation)
            with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as tmp:
                tts.save(tmp.name)
                st.audio(tmp.name)
        except Exception as e:
            st.error(f"🎤 TTS Error: {e}")

# --- Display Fun Facts ---
if st.session_state.fun_facts:
    st.subheader("🎉 Fun Facts")
    for fact in st.session_state.fun_facts:
        st.markdown(f"- {fact}")

# --- Display Quizzes ---
if st.session_state.quizzes:
    st.subheader("🧩 Quick Quiz (3 Questions)")
    for i, quiz in enumerate(st.session_state.quizzes, start=1):
        st.markdown(f"**Q{i}. {quiz['question']}**")
        user_choice = st.radio("Choose your answer:", quiz["options"], key=f"quiz_{i}")
        if st.button(f"Submit Q{i}"):
            match = re.match(r"^([A-D])", user_choice.strip().upper())
            user_letter = match.group(1) if match else None
            if user_letter == quiz["answer"]:
                st.success("✅ Correct!")
            else:
                st.error(f"❌ The correct answer was {quiz['answer']})")
        st.markdown("---")

# --- History ---
st.header("🕒 Previous Lessons")
if st.session_state.history:
    for i, record in enumerate(reversed(st.session_state.history), start=1):
        with st.expander(f"{i}. {record['topic']} ({record['level']})"):
            st.write(record["explanation"])
            if record["fun_facts"]:
                st.markdown("**🎉 Fun Facts:**")
                for fact in record["fun_facts"]:
                    st.markdown(f"- {fact}")
else:
    st.info("No saved lessons yet. Generate one above to start learning! 📚")
