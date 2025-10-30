import streamlit as st
import google.generativeai as genai
from dotenv import load_dotenv
from gtts import gTTS
import os, re, tempfile, time

# --- Setup ---
load_dotenv()
genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))
model = genai.GenerativeModel("gemini-2.0-flash")

st.set_page_config(page_title="AI Science Explainer", page_icon="🧠")
st.title("🧠 AI Science Explainer — Organized Learning Layout")

# --- Cached AI Generator ---
@st.cache_data(show_spinner="📦 Fetching or generating lesson...")
def generate_lesson(topic, level):
    prompt = f"""
You are a calm and patient science teacher. Explain '{topic}' at a {level} level using
friendly tone, analogies, and short examples. Then give 2 fun facts and 3 unique multiple-choice
quiz questions on different aspects of the topic.

EXPLANATION:
[Explanation text]

FUN FACTS:
- [Fact 1]
- [Fact 2]

QUIZZES:
QUESTION 1:
...
"""
    response = model.generate_content(prompt)
    text = response.text if hasattr(response, "text") else str(response)

    explanation_match = re.search(r"EXPLANATION:\s*(.*?)(?=FUN FACTS:|QUIZZES:|$)", text, re.DOTALL)
    fun_facts_match = re.search(r"FUN FACTS:\s*(.*?)(?=QUIZZES:|$)", text, re.DOTALL)
    explanation = explanation_match.group(1).strip() if explanation_match else "No explanation."
    fun_facts = [f.strip("-• ").strip() for f in fun_facts_match.group(1).split("\n") if f.strip()] if fun_facts_match else []
    quiz_blocks = re.findall(r"(QUESTION\s*\d+:[\s\S]*?)(?=(QUESTION\s*\d+:|$))", text, re.IGNORECASE)

    quizzes, seen = [], set()
    for tup in quiz_blocks:
        block = tup[0]
        q_match = re.search(r"QUESTION\s*\d*:\s*(.*?)(?=OPTIONS:|ANSWER:|$)", block, re.DOTALL | re.IGNORECASE)
        opts = re.findall(r"^[A-D]\)\s*.*", block, re.MULTILINE)
        ans_match = re.search(r"ANSWER:\s*\(?([A-D])\)?", block, re.IGNORECASE)
        q_text = q_match.group(1).strip() if q_match else ""
        if q_text.lower() not in seen and q_text:
            seen.add(q_text.lower())
            quizzes.append({
                "question": q_text,
                "options": opts,
                "answer": ans_match.group(1).upper() if ans_match else "A"
            })
    return {"explanation": explanation, "fun_facts": fun_facts, "quizzes": quizzes[:3]}

# --- UI ---
topic = st.text_input("🎓 Enter a science topic:")
level = st.selectbox("📘 Choose level:", ["Beginner", "Intermediate", "Advanced"])

if "history" not in st.session_state:
    st.session_state.history = []
if "lesson" not in st.session_state:
    st.session_state.lesson = None

if st.button("✨ Generate Lesson"):
    if topic:
        with st.spinner("🤖 Teaching assistant is preparing your lesson..."):
            lesson = generate_lesson(topic, level)
            st.session_state.lesson = lesson
            st.session_state.history.append({"topic": topic, "level": level, **lesson})
        st.success("✅ Lesson ready!")
    else:
        st.warning("Please enter a topic.")

# --- Layout with Tabs ---
if st.session_state.lesson:
    lesson = st.session_state.lesson
    st.divider()
    st.subheader(f"📚 Learning Dashboard: {topic.title()} ({level})")

    tab1, tab2, tab3, tab4 = st.tabs(["📘 Explanation", "🎉 Fun Facts", "🧩 Quizzes", "🔊 Listen"])

    with tab1:
        st.write(lesson["explanation"])

    with tab2:
        for fact in lesson["fun_facts"]:
            st.markdown(f"- {fact}")

    with tab3:
        for i, q in enumerate(lesson["quizzes"], start=1):
            st.markdown(f"**Q{i}. {q['question']}**")
            choice = st.radio("Choose an answer:", q["options"], key=f"q{i}")
            if st.button(f"Submit Q{i}", key=f"s{i}"):
                if choice.startswith(q["answer"]):
                    st.success("✅ Correct!")
                else:
                    st.error(f"❌ The correct answer was {q['answer']})")
            st.markdown("---")

    with tab4:
        if st.button("▶️ Read Explanation"):
            try:
                tts = gTTS(lesson["explanation"])
                with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as tmp:
                    tts.save(tmp.name)
                    st.audio(tmp.name)
            except Exception as e:
                st.error(f"TTS error: {e}")

# --- Expander for History ---
st.divider()
with st.expander("🕒 View Previous Lessons"):
    if st.session_state.history:
        for i, record in enumerate(reversed(st.session_state.history), start=1):
            st.markdown(f"**{i}. {record['topic']} ({record['level']})**")
            st.caption(record["explanation"])
    else:
        st.info("No previous lessons yet.")
