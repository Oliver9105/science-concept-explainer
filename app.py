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
st.title("🧠 AI Science Explainer + Cached Tutor (Gemini 2.0 Flash)")

# --- Cache Function ---
@st.cache_data(show_spinner="📦 Retrieving or generating AI explanation...")
def generate_lesson(topic: str, level: str):
    """Generate explanation, fun facts, and quizzes for a topic."""
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

    response = model.generate_content(prompt)
    text = response.text if hasattr(response, "text") else response.candidates[0].content.parts[0].text

    # --- Parse Explanation + Fun Facts ---
    explanation_match = re.search(r"EXPLANATION:\s*(.*?)(?=FUN FACTS:|QUIZZES:|$)", text, re.DOTALL)
    fun_facts_match = re.search(r"FUN FACTS:\s*(.*?)(?=QUIZZES:|QUESTION 1:|$)", text, re.DOTALL)
    explanation = explanation_match.group(1).strip() if explanation_match else "No explanation generated."
    fun_facts = [f.strip("-• ").strip() for f in fun_facts_match.group(1).split("\n") if f.strip()] if fun_facts_match else []

    # --- Parse Quizzes ---
    quiz_blocks = re.findall(r"(QUESTION\s*\d+:[\s\S]*?(?=(?:QUESTION\s*\d+:|$)))", text, re.IGNORECASE)
    quizzes = []
    for block in quiz_blocks:
        q_match = re.search(r"QUESTION\s*\d*:\s*(.*?)(?=OPTIONS:|ANSWER:|$)", block, re.DOTALL | re.IGNORECASE)
        opts = re.findall(r"^[A-D]\)\s*.*", block, re.MULTILINE)
        ans_match = re.search(r"ANSWER:\s*\(?([A-D])\)?", block, re.IGNORECASE)
        question = q_match.group(1).strip() if q_match else "Question unavailable."
        answer = ans_match.group(1).upper() if ans_match else "A"
        quizzes.append({"question": question, "options": opts, "answer": answer})

    return {
        "explanation": explanation,
        "fun_facts": fun_facts,
        "quizzes": quizzes
    }

# --- UI Inputs ---
topic = st.text_input("🎓 Enter a science topic:", placeholder="e.g., Photosynthesis")
level = st.selectbox("📘 Select difficulty:", ["Beginner", "Intermediate", "Advanced"])

# --- Session Init ---
if "history" not in st.session_state:
    st.session_state.history = []

# --- Generate / Retrieve from Cache ---
if st.button("✨ Generate or Load from Cache"):
    if topic:
        with st.spinner("🤖 Thinking..."):
            lesson = generate_lesson(topic, level)
            st.session_state.current = lesson
            st.session_state.history.append({
                "topic": topic,
                "level": level,
                "explanation": lesson["explanation"],
                "fun_facts": lesson["fun_facts"],
                "quizzes": lesson["quizzes"]
            })
        st.success("✅ Loaded successfully (from cache if previously generated).")
    else:
        st.warning("Please enter a topic first.")

st.divider()

# --- Display Explanation + TTS ---
if "current" in st.session_state:
    lesson = st.session_state.current
    st.header(f"📖 {level} Explanation")
    st.write(lesson["explanation"])

    if st.button("🔊 Read Aloud"):
        try:
            tts = gTTS(lesson["explanation"])
            with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as tmp:
                tts.save(tmp.name)
                st.audio(tmp.name)
        except Exception as e:
            st.error(f"🎤 TTS Error: {e}")

    # --- Fun Facts ---
    if lesson["fun_facts"]:
        st.subheader("🎉 Fun Facts")
        for fact in lesson["fun_facts"]:
            st.markdown(f"- {fact}")

    # --- Quizzes ---
    if lesson["quizzes"]:
        st.subheader("🧩 Quick Quiz (3 Questions)")
        for i, quiz in enumerate(lesson["quizzes"], start=1):
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

# --- History Section ---
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
    st.info("No lessons yet. Generate one above to start learning.")
