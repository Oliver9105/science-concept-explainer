# app.py — Full Day 5 stable build (merged features)
import streamlit as st
import google.generativeai as genai
from dotenv import load_dotenv
from gtts import gTTS
import os
import re
import tempfile
import time

# --- Setup ---
load_dotenv()
genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))
model = genai.GenerativeModel("gemini-2.0-flash")

st.set_page_config(page_title="AI Science Explainer", page_icon="🧠")
st.title("🧠 AI Science Explainer — Patient Teacher (Stable Build)")

# --- Cached generator (unique key: topic + level) ---
@st.cache_data(show_spinner="📦 Retrieving or generating AI explanation...")
def generate_lesson(topic: str, level: str):
    """
    Returns: dict with keys: explanation (str), fun_facts (list[str]), quizzes (list[dict])
    Each quiz dict: {"question": str, "options": [str,...], "answer": "A"/"B"/"C"/"D"}
    """
    # Teacher-tone + uniqueness instructions
    prompt = f"""
You are a calm and patient science teacher who explains complex ideas step-by-step
in a friendly tone. Use simple analogies, short real-world examples, and a warm, encouraging voice.

The topic is '{topic}' at a {level} level.

Please respond in this exact structure and be explicit: create THREE UNIQUE questions that test DIFFERENT sub-concepts. Avoid repeating concepts or phrasing.

EXPLANATION:
[Your explanation here. Be conversational and include at least one relatable example.]

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
        start_time = time.time()
        response = model.generate_content(prompt)

        # Timeout guard (defensive)
        if time.time() - start_time > 30:
            raise TimeoutError("API request took too long.")

        # --- Safe extraction of text (supports structured legacy and candidates)
        text = ""
        try:
            if hasattr(response, "text") and response.text:
                text = response.text
            elif hasattr(response, "candidates") and response.candidates:
                # typical Gemini structured path
                text = response.candidates[0].content.parts[0].text
            else:
                # fallback to string repr
                text = str(response)
        except Exception:
            text = str(response)

        if not text or len(text.strip()) == 0:
            raise ValueError("Empty API response")

        # --- Parse Explanation ---
        explanation_match = re.search(r"EXPLANATION:\s*(.*?)(?=FUN FACTS:|QUIZZES:|QUESTION 1:|$)", text, re.DOTALL | re.IGNORECASE)
        explanation = explanation_match.group(1).strip() if explanation_match else ""

        # --- Parse Fun Facts ---
        fun_facts_match = re.search(r"FUN FACTS:\s*(.*?)(?=QUIZZES:|QUESTION 1:|$)", text, re.DOTALL | re.IGNORECASE)
        fun_facts = []
        if fun_facts_match:
            for line in fun_facts_match.group(1).splitlines():
                line = line.strip()
                if not line:
                    continue
                # remove leading bullet chars
                fact = re.sub(r'^[\-\•\*\s]+', '', line)
                if fact:
                    fun_facts.append(fact.strip())

        # --- Parse quiz blocks (QUESTION 1/2/3) ---
        quiz_blocks = re.findall(r"(QUESTION\s*\d+:[\s\S]*?)(?=(QUESTION\s*\d+:|$))", text, re.IGNORECASE)
        quizzes = []
        # quiz_blocks is list of tuples due to group; extract first element each
        for tup in quiz_blocks:
            block = tup[0]
            q_match = re.search(r"QUESTION\s*\d*:\s*(.*?)(?=OPTIONS:|ANSWER:|$)", block, re.DOTALL | re.IGNORECASE)
            opts = re.findall(r"^[A-D]\)\s*.*", block, re.MULTILINE)
            # normalize options (strip)
            opts = [o.strip() for o in opts]
            ans_match = re.search(r"ANSWER:\s*\(?([A-D])\)?", block, re.IGNORECASE)
            q_text = q_match.group(1).strip() if q_match else ""
            answer = ans_match.group(1).upper() if ans_match else None
            if q_text and opts:
                # if answer missing, attempt to infer by scanning trailing lines
                if not answer:
                    # look for a line like "Correct: B" or "Correct answer: B" else default A
                    alt = re.search(r"(Correct(?: answer)?:|Correct:)\s*\(?([A-D])\)?", block, re.IGNORECASE)
                    answer = alt.group(2).upper() if alt else "A"
                quizzes.append({"question": q_text, "options": opts, "answer": answer})

        # Fallback parsing if the strict blocks weren't found (robustness)
        if not explanation:
            # everything before first "QUESTION" or "FUN FACTS" as explanation
            fallback = re.split(r"QUESTION\s*1:|QUIZZES:|FUN FACTS:", text, flags=re.IGNORECASE)
            if fallback and len(fallback) > 0:
                explanation = fallback[0].replace("EXPLANATION:", "").strip()

        # If fun_facts empty, try quick regex for lines starting with - after FUN FACTS
        if not fun_facts:
            ff = re.findall(r"FUN FACTS:\s*((?:[\-\•\*].*(?:\n|$))+)", text, re.IGNORECASE)
            if ff:
                for line in ff[0].splitlines():
                    line = re.sub(r'^[\-\•\*\s]+', '', line).strip()
                    if line:
                        fun_facts.append(line)

        # If no quizzes parsed, try to find A/B/C/D options across whole text and chunk
        if not quizzes:
            # find all occurrences of A) ... B) ... C) ... D) ... groups
            blocks = re.findall(r"((?:^[A-D]\)\s*.*\n?){4})", text, re.MULTILINE)
            for b in blocks:
                opts = re.findall(r"^[A-D]\)\s*.*", b, re.MULTILINE)
                if opts:
                    # try to match nearest preceding question line
                    q_near = re.findall(r"([^\n]{10,200}?)\n(?:A\))", text, re.DOTALL)
                    q_text = q_near[0].strip() if q_near else "Question"
                    quizzes.append({"question": q_text, "options": [o.strip() for o in opts], "answer": "A"})

        # --- Deduplicate similar questions (normalize and compare) ---
        unique_quizzes = []
        seen = set()
        for q in quizzes:
            norm = re.sub(r'\s+', ' ', q["question"].strip().lower())
            if norm not in seen:
                unique_quizzes.append(q)
                seen.add(norm)
        # ensure we have at most 3; if less, it's okay
        unique_quizzes = unique_quizzes[:3]

        # Final sensible defaults
        if not explanation:
            explanation = "No clear explanation was returned. Please try again."
        if not fun_facts:
            fun_facts = ["No fun facts were returned."]
        if not unique_quizzes:
            # build placeholder quizzes
            unique_quizzes = [
                {"question": "Placeholder question: What is this topic about?", "options": ["A) Option A","B) Option B","C) Option C","D) Option D"], "answer": "A"}
            ]

        return {
            "explanation": explanation,
            "fun_facts": fun_facts,
            "quizzes": unique_quizzes
        }

    except TimeoutError as te:
        # Bubble up a friendly error payload
        return {"explanation": "The AI timed out. Please try again.", "fun_facts": [], "quizzes": []}
    except Exception as e:
        return {"explanation": f"Error generating content: {e}", "fun_facts": [], "quizzes": []}


# --- UI inputs & session init ---
topic = st.text_input("🎓 Enter a science topic:", placeholder="e.g., Photosynthesis")
level = st.selectbox("📘 Select difficulty:", ["Beginner", "Intermediate", "Advanced"])

if "history" not in st.session_state:
    st.session_state.history = []  # saved lessons
if "current" not in st.session_state:
    st.session_state.current = None
# per-question answered flags
# we'll use keys like answered_1, answered_2, answered_3 in session_state when user submits

# --- Generate / Load (from cache) ---
if st.button("✨ Generate Lesson"):
    if not topic:
        st.warning("Please enter a topic first.")
    else:
        with st.spinner("🤖 Generating lesson (cached by topic+level)..."):
            lesson = generate_lesson(topic.strip(), level)
            st.session_state.current = lesson
            # Save to history (store topic, level, lesson snapshot)
            st.session_state.history.append({
                "topic": topic.strip(),
                "level": level,
                "explanation": lesson.get("explanation", ""),
                "fun_facts": lesson.get("fun_facts", []),
                "quizzes": lesson.get("quizzes", [])
            })
        st.success("✅ Lesson ready!")

st.divider()

# --- Display current lesson ---
if st.session_state.current:
    lesson = st.session_state.current
    st.header(f"📖 {level} Explanation")
    st.write(lesson["explanation"])

    # TTS read aloud button
    tts_col1, tts_col2 = st.columns([1,5])
    with tts_col1:
        if st.button("🔊 Read Aloud"):
            try:
                tts = gTTS(lesson["explanation"])
                with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as tmp:
                    tts.save(tmp.name)
                    st.audio(tmp.name)
            except Exception as e:
                st.error(f"TTS error: {e}")

    # Fun facts
    if lesson.get("fun_facts"):
        st.subheader("🎉 Fun Facts")
        for fact in lesson["fun_facts"]:
            st.markdown(f"- {fact}")

    # Quizzes: display each with a radio and submit button; results persist via session_state
    if lesson.get("quizzes"):
        st.subheader("🧩 Quiz (3 Questions)")

        for idx, quiz in enumerate(lesson["quizzes"], start=1):
            q_key = f"quiz_choice_{idx}"
            submit_key = f"quiz_submit_{idx}"
            answered_key = f"quiz_answered_{idx}"
            result_key = f"quiz_result_{idx}"

            st.markdown(f"**Q{idx}. {quiz['question']}**")
            # Show options; each option is full string like "A) text"
            # If options are raw like "A) ..." keep them; otherwise format them
            options = quiz.get("options", [])
            if not options:
                # fallback options
                options = ["A) Option A", "B) Option B", "C) Option C", "D) Option D"]

            # default selection: if previously selected, use it
            default_index = 0
            prev_choice = st.session_state.get(q_key, None)
            if prev_choice and prev_choice in options:
                # set default index to that option
                try:
                    default_index = options.index(prev_choice)
                except Exception:
                    default_index = 0

            user_choice = st.radio("Choose an answer:", options, index=default_index, key=q_key)

            # Submit button for this question
            if st.button(f"Submit Q{idx}", key=submit_key):
                st.session_state[q_key] = user_choice  # persist chosen option
                # extract letter from chosen option
                m = re.match(r"^\s*([A-D])", user_choice.strip().upper())
                user_letter = m.group(1) if m else None
                correct_letter = quiz.get("answer", "A").upper().strip()
                is_correct = (user_letter == correct_letter)
                st.session_state[answered_key] = True
                st.session_state[result_key] = is_correct

            # If already answered, show persistent feedback
            if st.session_state.get(answered_key, False):
                if st.session_state.get(result_key, False):
                    st.success("✅ Correct!")
                else:
                    corr = quiz.get("answer", "A")
                    st.error(f"❌ Not quite — the correct answer was **{corr}**)")

            st.markdown("---")

st.divider()

# --- History (expanders) ---
st.header("🕒 Previous Lessons")
if st.session_state.history:
    st.write(f"📚 You have **{len(st.session_state.history)}** saved lessons in this session.")
    for i, record in enumerate(reversed(st.session_state.history), start=1):
        with st.expander(f"{i}. {record['topic']} ({record['level']})"):
            st.write(record["explanation"])
            if record.get("fun_facts"):
                st.markdown("**🎉 Fun Facts:**")
                for fact in record["fun_facts"]:
                    st.markdown(f"- {fact}")
            if record.get("quizzes"):
                st.markdown("**🧩 Quizzes (summary):**")
                for qi, q in enumerate(record["quizzes"], start=1):
                    st.markdown(f"- Q{qi}. {q['question']}")
else:
    st.info("No saved lessons yet. Generate one above to start your learning log.")
