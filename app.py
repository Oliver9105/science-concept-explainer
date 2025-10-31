import os, re, io, tempfile, json, time
import streamlit as st
from dotenv import load_dotenv
import google.generativeai as genai
from gtts import gTTS
from datetime import datetime

# ---------- Setup ----------
load_dotenv()
GENAI_API_KEY = os.getenv("GOOGLE_API_KEY")
HISTORY_FILE = "lessons.json"

st.set_page_config(
    page_title="AI Science Explainer",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded"
)
st.title("🧠 AI Science Explainer — Robust Learning Edition")

# ---------- Persistence Utilities ----------
def save_history_to_file(history):
    """Save user lesson history to local JSON file."""
    try:
        with open(HISTORY_FILE, "w", encoding="utf-8") as f:
            json.dump(history, f, indent=2)
        return True
    except Exception as e:
        st.error(f"Failed to save history: {e}")
        return False

def load_history_from_file():
    """Load user lesson history if it exists."""
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            st.error(f"Failed to load history: {e}")
            return []
    return []

# ---------- Quiz Generator ----------
def generate_topic_specific_quiz(topic, level, explanation_text=""):
    """Generate quiz questions dynamically based on topic and level."""
    
    # Dynamic question templates based on level
    level_templates = {
        "Beginner": [
            {
                "question": f"What is the main concept of {topic}?",
                "options": [
                    f"A) A basic process in {topic}", 
                    f"B) A complex theory about {topic}", 
                    f"C) A simple fact about {topic}", 
                    f"D) A measurement of {topic}"
                ],
                "answer": "A"
            },
            {
                "question": f"How is {topic} important in everyday life?",
                "options": [
                    f"A) It affects daily activities", 
                    f"B) It has no practical use", 
                    f"C) It's only theoretical", 
                    f"D) It's too complex for daily use"
                ],
                "answer": "A"
            },
            {
                "question": f"What would happen if {topic} didn't exist?",
                "options": [
                    f"A) Nothing significant", 
                    f"B) Major changes in our world", 
                    f"C) Only minor effects", 
                    f"D) Unknown consequences"
                ],
                "answer": "B"
            }
        ],
        "Intermediate": [
            {
                "question": f"What is the underlying mechanism of {topic}?",
                "options": [
                    f"A) Simple cause and effect", 
                    f"B) Complex interactions between components", 
                    f"C) Random processes", 
                    f"D) Pure speculation"
                ],
                "answer": "B"
            },
            {
                "question": f"Which scientific field best describes {topic}?",
                "options": [
                    "A) Physics", 
                    "B) Chemistry", 
                    "C) Biology", 
                    "D) It spans multiple fields"
                ],
                "answer": "D"
            },
            {
                "question": f"What evidence supports our understanding of {topic}?",
                "options": [
                    "A) Theoretical models", 
                    "B) Experimental data", 
                    "C) Mathematical proof", 
                    "D) All of the above"
                ],
                "answer": "D"
            }
        ],
        "Advanced": [
            {
                "question": f"What are the mathematical models used to describe {topic}?",
                "options": [
                    "A) Linear equations", 
                    "B) Differential equations", 
                    "C) Statistical models", 
                    "D) Complex computational models"
                ],
                "answer": "D"
            },
            {
                "question": f"How does {topic} relate to fundamental physics principles?",
                "options": [
                    "A) It's unrelated", 
                    "B) It follows standard physical laws", 
                    "C) It challenges current understanding", 
                    "D) It's purely philosophical"
                ],
                "answer": "B"
            },
            {
                "question": f"What are the current research frontiers in {topic}?",
                "options": [
                    "A) Established knowledge", 
                    "B) Active investigation", 
                    "C) Speculative theories", 
                    "D) Unknown territory"
                ],
                "answer": "B"
            }
        ]
    }
    
    return level_templates.get(level, level_templates["Beginner"])

# ---------- API Configuration ----------
@st.cache_resource(show_spinner="🔧 Initializing AI services...")
def init_gemini():
    if not GENAI_API_KEY:
        return None, "❌ Missing GOOGLE_API_KEY in .env"
    try:
        genai.configure(api_key=GENAI_API_KEY)
        model = genai.GenerativeModel("gemini-2.0-flash")
        return model, "✅ AI Ready"
    except Exception as e:
        return None, f"❌ Failed to initialize: {str(e)}"

# ---------- Core Functions ----------
@st.cache_data(show_spinner="🤖 Generating explanation...")
def generate_explanation(topic, level):
    """Generate comprehensive science explanation with guaranteed quiz."""
    level_contexts = {
        "Beginner": "simple language, basic concepts, everyday examples",
        "Intermediate": "moderate complexity, scientific terminology, practical applications",
        "Advanced": "detailed explanations, complex concepts, technical precision"
    }
    context = level_contexts.get(level, level_contexts["Beginner"])
    
    prompt = f"""
You are a patient, engaging science teacher explaining the topic '{topic}' for a {level} learner.

Please provide:
1. CLEAR EXPLANATION (200-300 words): use {context}, give one real-world example.
2. ENGAGING FUN FACTS (exactly 2)
3. INTERACTIVE QUIZ (exactly 3 questions): multiple choice A-D, with answer letters.

Format with clear headers: EXPLANATION, FUN FACTS, QUIZ QUESTIONS.
"""
    try:
        response = MODEL.generate_content(prompt)
        text = getattr(response, "text", "") or response.candidates[0].content.parts[0].text
        return process_ai_response(text, topic, level)
    except Exception as e:
        # Fallback response when AI fails
        explanation = f"{topic} is an important scientific concept. It involves various processes and mechanisms that are fundamental to understanding our world. The applications of {topic} are found throughout nature and technology, making it essential for scientific literacy."
        
        return {
            "explanation": explanation,
            "fun_facts": [
                f"Many scientists study {topic} extensively.", 
                f"{topic} has practical applications in daily life."
            ],
            "quizzes": generate_topic_specific_quiz(topic, level),
            "topic": topic,
            "level": level,
            "timestamp": datetime.now().isoformat(),
            "word_count": len(explanation.split()),
            "ai_generated": False
        }

def process_ai_response(text, topic, level):
    """Parse Gemini output into structured data with guaranteed quiz."""
    
    # Extract explanation
    exp_patterns = [
        r"EXPLANATION:?\s*(.*?)(?=FUN FACTS:|QUIZ|$)",
        r"1\.?\s*CLEAR EXPLANATION.*?(?=2\.|$)",
        r"EXPLANATION\s*(.*?)(?=\n\n|$)"
    ]
    
    explanation = ""
    for pattern in exp_patterns:
        exp_match = re.search(pattern, text, re.S | re.I)
        if exp_match:
            explanation = exp_match.group(1).strip()
            break
    
    if not explanation:
        # Fallback explanation
        explanation = f"{topic} is a fundamental scientific concept that involves important processes and principles. Understanding {topic} helps us better comprehend how the world works and has numerous practical applications in everyday life."
    
    # Extract fun facts
    facts_patterns = [
        r"FUN FACTS?:?\s*(.*?)(?=QUIZ|$)",
        r"2\.?\s*ENGAGING FUN FACTS.*?(?=3\.|$)"
    ]
    
    facts = []
    for pattern in facts_patterns:
        facts_match = re.search(pattern, text, re.S | re.I)
        if facts_match:
            facts_text = facts_match.group(1).strip()
            extracted_facts = re.findall(r"[-•]\s*(.+)", facts_text)
            facts.extend(extracted_facts)
            break
    
    if not facts:
        facts = [
            f"Research on {topic} continues to reveal new insights.", 
            f"{topic} plays a crucial role in scientific understanding."
        ]
    
    facts = facts[:2] if len(facts) >= 2 else facts + [f"Interesting fact about {topic}."] * (2 - len(facts))
    
    # Extract quiz with multiple robust patterns
    quiz_questions = extract_robust_quiz(text, topic, level)
    
    return {
        "explanation": explanation,
        "fun_facts": facts,
        "quizzes": quiz_questions,
        "topic": topic,
        "level": level,
        "timestamp": datetime.now().isoformat(),
        "word_count": len(explanation.split()),
        "ai_generated": True
    }

def extract_robust_quiz(text, topic, level):
    """Extract quiz with multiple fallback strategies."""
    
    # Strategy 1: Look for numbered questions
    quiz_patterns = [
        r"(?:Question\s*\d*:|Q\d*\.)\s*([^?]*\?)[\s\S]*?(?:A\)|Option\s*A)[\s\S]*?(?:B\)|Option\s*B)[\s\S]*?(?:C\)|Option\s*C)[\s\S]*?(?:D\)|Option\s*D)[\s\S]*?(?:Answer:\s*([A-D]))",
        r"(\d+\.\s*[^?]*\?)[\s\S]*?A\)\s*([^\n]+)[\s\S]*?B\)\s*([^\n]+)[\s\S]*?C\)\s*([^\n]+)[\s\S]*?D\)\s*([^\n]+)[\s\S]*?(?:Answer:\s*([A-D]))?",
        r"(?:QUESTION\s*\d*:)\s*([^?]*\?)[\s\S]*?(?:OPTIONS?|CHOICES?)[\s\S]*?(?:A\)[\s\S]*?B\)[\s\S]*?C\)[\s\S]*?D\))"
    ]
    
    extracted_quizzes = []
    
    for pattern in quiz_patterns:
        matches = re.findall(pattern, text, re.MULTILINE | re.DOTALL)
        for match in matches:
            if len(match) >= 5:  # Need question + 4 options minimum
                question = match[0].strip() if match[0] else f"Question about {topic}"
                
                # Extract options (flexible)
                full_match = match[0] if isinstance(match[0], str) else " ".join(str(m) for m in match[:4])
                options = re.findall(r"[A-D]\)\s*([^\n]+)", full_match)
                
                if len(options) >= 3:  # Need at least 3 options
                    # Pad to 4 options
                    while len(options) < 4:
                        options.append(f"Option {len(options)+1}")
                    
                    # Extract answer
                    answer = "A"
                    if len(match) > len(options):
                        answer_match = match[-1]
                        if answer_match and answer_match.upper() in "ABCD":
                            answer = answer_match.upper()
                    
                    extracted_quizzes.append({
                        "question": question,
                        "options": [f"{chr(65+i)}) {opt.strip()}" for i, opt in enumerate(options[:4])],
                        "answer": answer
                    })
    
    if len(extracted_quizzes) >= 3:
        return extracted_quizzes[:3]
    
    # Strategy 2: Use AI response but ensure we have 3 questions
    if len(extracted_quizzes) > 0:
        # If we have some questions, complete with topic-specific ones
        while len(extracted_quizzes) < 3:
            fallback_quiz = generate_topic_specific_quiz(topic, level)
            for quiz in fallback_quiz:
                if quiz not in extracted_quizzes and len(extracted_quizzes) < 3:
                    extracted_quizzes.append(quiz)
                    break
    
    # Strategy 3: Complete fallback - generate all questions
    if len(extracted_quizzes) < 3:
        fallback_quizzes = generate_topic_specific_quiz(topic, level)
        return fallback_quizzes
    
    return extracted_quizzes

def extract_key_points(explanation):
    """Extract 3-4 concise takeaways."""
    sentences = explanation.split('.')
    points = [s.strip() for s in sentences if len(s.strip()) > 20][:4]
    return points or ["Main ideas extracted from explanation."]

@st.cache_data(show_spinner="🔊 Generating audio...")
def generate_audio(text, language='en'):
    """Convert text to speech with gTTS."""
    try:
        tts = gTTS(text=text, lang=language)
        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as tmp:
            tts.save(tmp.name)
            return tmp.name, None
    except Exception as e:
        return None, str(e)

# ---------- Session State ----------
if "history" not in st.session_state:
    st.session_state.history = load_history_from_file()
if "current_lesson" not in st.session_state:
    st.session_state.current_lesson = None
if "quiz_answers" not in st.session_state:
    st.session_state.quiz_answers = {}
if "audio_file" not in st.session_state:
    st.session_state.audio_file = None
if "quiz_results" not in st.session_state:
    st.session_state.quiz_results = {}
if "current_quiz_score" not in st.session_state:
    st.session_state.current_quiz_score = {"correct": 0, "total": 0, "answers": {}}

# ---------- Initialize AI ----------
MODEL, status = init_gemini()

# ---------- Sidebar ----------
with st.sidebar:
    st.header("🎯 Learning Control Panel")
    st.markdown(f"**AI Engine:** {status}")
    st.metric("Lessons Stored", len(st.session_state.history))

    audio_language = st.selectbox("🎧 Audio Language", ["en", "es", "fr", "de"], index=0)

    st.markdown("---")
    if st.button("💾 Save Progress Now"):
        if save_history_to_file(st.session_state.history):
            st.success("✅ History saved successfully!")
    if st.button("📤 Export Lessons"):
        try:
            with open(HISTORY_FILE, "rb") as f:
                st.download_button("⬇️ Download JSON", data=f, file_name="my_lessons.json")
        except Exception as e:
            st.error(f"Export failed: {e}")
    if st.button("🧹 Clear All History"):
        st.session_state.history = []
        st.session_state.current_quiz_score = {"correct": 0, "total": 0, "answers": {}}
        save_history_to_file([])
        st.success("Session cleared.")
        st.rerun()

# ---------- Main Interface ----------
st.divider()
topic = st.text_input("🎓 Enter a science topic", placeholder="e.g., Photosynthesis")
level = st.selectbox("📘 Select Level", ["Beginner", "Intermediate", "Advanced"])
if st.button("✨ Generate Lesson"):
    if not MODEL:
        st.error("❌ AI not ready. Check API key.")
    elif topic:
        with st.spinner(f"Generating lesson on {topic}..."):
            data = generate_explanation(topic, level)
            if "error" in data:
                st.error(data["error"])
            else:
                st.session_state.current_lesson = data
                st.session_state.history.append(data)
                st.session_state.current_quiz_score = {"correct": 0, "total": 0, "answers": {}}
                save_history_to_file(st.session_state.history)
                st.success(f"✅ Lesson on {topic} ready! (Quiz guaranteed)")
                st.balloons()
    else:
        st.warning("Enter a topic first!")

# ---------- Display Lesson ----------
if st.session_state.current_lesson:
    lesson = st.session_state.current_lesson
    
    # Lesson header with generation status
    col1, col2 = st.columns([3, 1])
    with col1:
        st.subheader(f"📘 {lesson['topic']} ({lesson['level']})")
        if lesson.get('ai_generated', True):
            st.caption("🤖 AI Generated Content")
        else:
            st.caption("⚠️ Fallback Mode - Quiz Generated Locally")
    with col2:
        if st.button("🔄 Regenerate"):
            with st.spinner("Creating new lesson..."):
                new_lesson = generate_explanation(lesson['topic'], lesson['level'])
                st.session_state.current_lesson = new_lesson
                st.session_state.history[-1] = new_lesson
                st.session_state.current_quiz_score = {"correct": 0, "total": 0, "answers": {}}
                st.rerun()

    tab1, tab2, tab3, tab4 = st.tabs(["📘 Explanation", "🎉 Fun Facts", "🧩 Interactive Quiz", "🔊 Audio"])

    # Explanation Tab
    with tab1:
        st.markdown(lesson["explanation"])
        st.caption(f"📊 {lesson['word_count']} words • Generated {datetime.fromisoformat(lesson['timestamp']).strftime('%H:%M %p')}")
        
        st.markdown("### 💡 Key Takeaways")
        for pt in extract_key_points(lesson["explanation"]):
            st.markdown(f"- {pt}")

    # Fun Facts Tab
    with tab2:
        st.markdown("### 🎉 Fascinating Discoveries")
        for i, fact in enumerate(lesson["fun_facts"], 1):
            with st.container():
                st.markdown(f"**🧠 Fun Fact {i}:** {fact}")
                if i < len(lesson["fun_facts"]):
                    st.divider()

    # Quiz Tab - Enhanced with real-time scoring
    with tab3:
        st.markdown("### 🧩 Test Your Knowledge")
        st.markdown(f"Answer these questions about **{lesson['topic']}**:")
        
        # Initialize quiz session for this lesson if not exists
        lesson_key = f"{lesson['topic']}_{lesson['timestamp']}"
        if lesson_key not in st.session_state.quiz_results:
            st.session_state.quiz_results[lesson_key] = {
                "answers": {},
                "submitted": False
            }
        
        quiz_data = st.session_state.quiz_results[lesson_key]
        
        # Display current score progress
        if quiz_data["answers"]:
            correct_answers = sum(1 for answer in quiz_data["answers"].values() if answer["is_correct"])
            total_answered = len(quiz_data["answers"])
            
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Current Score", f"{correct_answers}/{total_answered}")
            with col2:
                if total_answered > 0:
                    percentage = (correct_answers / total_answered) * 100
                    st.metric("Percentage", f"{percentage:.0f}%")
                else:
                    st.metric("Percentage", "0%")
            with col3:
                st.metric("Questions Left", f"{len(lesson['quizzes']) - total_answered}")
        
        # Display each question
        for i, q in enumerate(lesson["quizzes"], 1):
            st.markdown(f"**Question {i}:** {q['question']}")
            
            # Check if this question has been answered
            question_key = f"q_{i}"
            is_answered = question_key in quiz_data["answers"]
            
            # Create radio button for answer selection
            selected_answer = st.radio(
                "Select your answer:",
                q["options"],
                key=f"quiz_{lesson_key}_{i}",
                index=None if not is_answered else next((idx for idx, opt in enumerate(q["options"]) if opt.startswith(quiz_data["answers"][question_key]["selected"])), None),
                disabled=is_answered,
                label_visibility="hidden"
            )
            
            # Answer submission
            col1, col2 = st.columns([1, 4])
            with col1:
                if not is_answered and selected_answer:
                    if st.button(f"✅ Submit Answer {i}", key=f"submit_{i}"):
                        # Check if answer is correct
                        is_correct = selected_answer.startswith(q["answer"])
                        
                        # Store the answer
                        quiz_data["answers"][question_key] = {
                            "selected": selected_answer[0],  # Store just the letter (A, B, C, D)
                            "is_correct": is_correct,
                            "correct_answer": q["answer"]
                        }
                        
                        # Update current quiz score
                        st.session_state.current_quiz_score["total"] += 1
                        if is_correct:
                            st.session_state.current_quiz_score["correct"] += 1
                        
                        st.success("✅ Answer submitted!")
                        st.rerun()
            
            with col2:
                if is_answered:
                    answer_data = quiz_data["answers"][question_key]
                    if answer_data["is_correct"]:
                        st.success("🎉 **Correct!** Well done!")
                    else:
                        st.error(f"❌ **Not quite right.** The correct answer is: **{q['answer']}**")
                    st.info(f"💡 **Explanation:** This question tests your understanding of key concepts in {lesson['topic']}.")
            
            st.divider()
        
        # Final quiz summary
        if quiz_data["answers"] and len(quiz_data["answers"]) == len(lesson["quizzes"]):
            correct_answers = sum(1 for answer in quiz_data["answers"].values() if answer["is_correct"])
            total_questions = len(lesson["quizzes"])
            percentage = (correct_answers / total_questions) * 100
            
            st.markdown("### 🏆 Quiz Complete!")
            
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Final Score", f"{correct_answers}/{total_questions}")
            with col2:
                st.metric("Final Percentage", f"{percentage:.0f}%")
            with col3:
                if percentage >= 80:
                    st.success("🏆 Excellent!")
                elif percentage >= 60:
                    st.info("👍 Good work!")
                else:
                    st.warning("📚 Keep learning!")
            
            # Detailed breakdown
            st.markdown("#### 📊 Answer Breakdown:")
            for i, q in enumerate(lesson["quizzes"], 1):
                question_key = f"q_{i}"
                answer_data = quiz_data["answers"][question_key]
                status = "✅" if answer_data["is_correct"] else "❌"
                st.write(f"{status} **Question {i}:** Your answer: {answer_data['selected']} | Correct answer: {q['answer']}")
            
            # Reset quiz button
            if st.button("🔄 Retake Quiz"):
                del st.session_state.quiz_results[lesson_key]
                st.session_state.current_quiz_score = {"correct": 0, "total": 0, "answers": {}}
                st.rerun()

    # Audio Tab
    with tab4:
        st.markdown("### 🔊 Listen to Your Lesson")
        
        if st.session_state.audio_file:
            st.success("✅ Audio ready!")
            st.audio(st.session_state.audio_file)
            
            col1, col2 = st.columns(2)
            with col1:
                if st.button("🔄 New Audio"):
                    with st.spinner("Generating new audio..."):
                        audio, err = generate_audio(f"{lesson['topic']} lesson. {lesson['explanation']}", language=audio_language)
                        if err:
                            st.error(err)
                        else:
                            st.session_state.audio_file = audio
                            st.success("Audio updated!")
                            st.rerun()
            with col2:
                if st.button("💾 Download"):
                    try:
                        with open(st.session_state.audio_file, 'rb') as f:
                            audio_bytes = f.read()
                            st.download_button(
                                "📱 Save Audio",
                                data=audio_bytes,
                                file_name=f"{lesson['topic']}_lesson.mp3",
                                mime="audio/mpeg"
                            )
                    except Exception as e:
                        st.error(f"Download failed: {e}")
        else:
            if st.button("🔊 Generate Audio"):
                with st.spinner("Creating audio narration..."):
                    audio, err = generate_audio(f"{lesson['topic']} lesson. {lesson['explanation']}", language=audio_language)
                    if err:
                        st.error(err)
                    else:
                        st.session_state.audio_file = audio
                        st.success("Audio ready!")
                        st.rerun()

# ---------- Enhanced History Section ----------
with st.expander("📚 Complete Lesson History", expanded=False):
    if st.session_state.history:
        # History statistics
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Total Lessons", len(st.session_state.history))
        with col2:
            topics = [h['topic'] for h in st.session_state.history]
            unique_topics = len(set(topics))
            st.metric("Unique Topics", unique_topics)
        with col3:
            ai_generated = sum(1 for h in st.session_state.history if h.get('ai_generated', True))
            st.metric("AI Generated", f"{ai_generated}/{len(st.session_state.history)}")
        
        st.markdown("---")
        
        # Display lessons
        for i, lesson in enumerate(reversed(st.session_state.history), 1):
            with st.container():
                col1, col2, col3, col4 = st.columns([3, 1, 1, 1])
                
                with col1:
                    st.markdown(f"**{i}. {lesson['topic']}** ({lesson['level']})")
                    
                    # Show quiz quality indicator
                    if len(lesson.get('quizzes', [])) >= 3:
                        st.success("✅ Complete quiz")
                    else:
                        st.warning("⚠️ Quiz may be incomplete")
                    
                    # Timestamp
                    timestamp = datetime.fromisoformat(lesson['timestamp'])
                    st.caption(f"📅 {timestamp.strftime('%b %d, %Y at %I:%M %p')}")
                
                with col2:
                    if st.button("👁️ View", key=f"view_{i}"):
                        st.session_state.current_lesson = lesson
                        st.rerun()
                
                with col3:
                    if st.button("🗑️ Delete", key=f"delete_{i}"):
                        st.session_state.history.remove(lesson)
                        save_history_to_file(st.session_state.history)
                        st.success("Lesson deleted")
                        st.rerun()
                
                with col4:
                    word_count = lesson.get('word_count', 0)
                    st.caption(f"📝 {word_count} words")
                
                st.divider()
    else:
        st.info("📚 No lessons saved yet. Generate your first lesson to get started!")

# ---------- Footer ----------
st.markdown("---")
col1, col2, col3 = st.columns(3)

with col1:
    st.caption("🎯 **Guaranteed Quiz Generation**")
    st.caption("Every lesson includes 3 interactive questions")

with col2:
    st.caption("🤖 **AI-Powered Content**")  
    st.caption("Powered by Google Gemini with fallback support")

with col3:
    st.caption("💾 **Persistent Storage**")
    st.caption("Your lessons are saved locally and persistently")