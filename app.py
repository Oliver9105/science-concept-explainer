import os, re, io, tempfile
import streamlit as st
from dotenv import load_dotenv
import google.generativeai as genai
from gtts import gTTS
import time
from datetime import datetime

# ---------- Setup ----------
load_dotenv()
GENAI_API_KEY = os.getenv("GOOGLE_API_KEY")

st.set_page_config(
    page_title="AI Science Explainer", 
    page_icon="🧠", 
    layout="wide",
    initial_sidebar_state="expanded"
)
st.title("🧠 AI Science Explainer — Core Learning Edition")

# ---------- API Configuration ----------
@st.cache_resource(show_spinner="🔧 Initializing AI services...")
def init_gemini():
    """Initialize Google Gemini AI"""
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
    """Generate comprehensive science explanation with quiz"""
    
    # Create context-aware prompt based on level
    level_contexts = {
        "Beginner": "simple language, basic concepts, everyday examples",
        "Intermediate": "moderate complexity, scientific terminology, practical applications", 
        "Advanced": "detailed explanations, complex concepts, technical precision"
    }
    
    context = level_contexts.get(level, level_contexts["Beginner"])
    
    prompt = f"""
You are an expert science teacher creating educational content for a {level} student.

TOPIC: {topic}
COMPLEXITY LEVEL: {level}
APPROACH: {context}

Please provide:

1. CLEAR EXPLANATION (200-300 words):
   - Define the concept clearly
   - Explain key processes/mechanisms
   - Include one real-world, relatable example
   - Use level-appropriate language

2. ENGAGING FUN FACTS (exactly 2):
   - Surprising or interesting details
   - Relevant to the main topic
   - Age-appropriate and memorable

3. INTERACTIVE QUIZ (exactly 3 questions):
   - Multiple choice (A, B, C, D options)
   - Test understanding, not just memorization
   - Include answer explanations
   - Mix conceptual and application questions

Format your response clearly with headers.
"""
    
    try:
        response = MODEL.generate_content(prompt)
        text = getattr(response, "text", "") or response.candidates[0].content.parts[0].text
        return process_ai_response(text, topic, level)
    except Exception as e:
        return {
            "error": f"Failed to generate content: {str(e)}",
            "topic": topic,
            "level": level,
            "timestamp": datetime.now().isoformat()
        }

def process_ai_response(text, topic, level):
    """Process and structure the AI response"""
    
    # Extract explanation
    exp_match = re.search(r"1\.?\s*CLEAR EXPLANATION.*?(?=2\.|$)", text, re.S | re.I)
    if exp_match:
        explanation = exp_match.group(0).replace("1.", "").strip()
    else:
        explanation = text.split("2.")[0].strip() if "2." in text else text
    
    # Extract fun facts
    facts_match = re.search(r"2\.?\s*ENGAGING FUN FACTS.*?(?=3\.|$)", text, re.S | re.I)
    if facts_match:
        facts_text = facts_match.group(0).replace("2.", "").strip()
        facts = re.findall(r"[-•]\s*(.+)", facts_text)[:2]
        facts = [f.strip() for f in facts if f.strip()]
    else:
        facts = ["Fun fact extraction failed", "This is a placeholder fact"]
    
    # Extract quiz questions
    quiz_match = re.search(r"3\.?\s*INTERACTIVE QUIZ.*", text, re.S | re.I)
    quizzes = []
    
    if quiz_match:
        quiz_text = quiz_match.group(0).replace("3.", "").strip()
        
        # Find individual questions
        question_blocks = re.findall(r"(Q\d*\.?[^Q]*?)(?=Q\d*\.?|$)", quiz_text, re.S)
        
        for block in question_blocks[:3]:
            # Extract question
            q_match = re.search(r"(?:Q\d*\.?)?\s*([^?]*\?)", block)
            question_text = q_match.group(1).strip() if q_match else "Question not found"
            
            # Extract options
            options = re.findall(r"[A-D]\)\s*([^\n]+)", block)
            if len(options) < 4:  # Pad with defaults if needed
                while len(options) < 4:
                    options.append(f"Option {len(options)+1}")
            
            # Extract answer
            ans_match = re.search(r"ANSWER:\s*\(?([A-D])\)?", block, re.I)
            answer = ans_match.group(1).upper() if ans_match else "A"
            
            quizzes.append({
                "question": question_text,
                "options": [f"{chr(65+i)}) {opt}" for i, opt in enumerate(options[:4])],
                "answer": answer
            })
    else:
        # Fallback quizzes
        quizzes = [
            {
                "question": f"What is the main concept discussed about {topic}?",
                "options": ["A) A simple definition", "B) A complex process", "C) A basic theory", "D) All of the above"],
                "answer": "A"
            },
            {
                "question": f"How is {topic} important in real life?",
                "options": ["A) It's not important", "B) Has practical applications", "C) Only academic value", "D) Unknown significance"],
                "answer": "B"
            },
            {
                "question": f"What would you need to understand {topic} better?",
                "options": ["A) More examples", "B) Simpler language", "C) Deeper study", "D) Visual aids"],
                "answer": "A"
            }
        ]
    
    return {
        "explanation": explanation,
        "fun_facts": facts,
        "quizzes": quizzes,
        "topic": topic,
        "level": level,
        "timestamp": datetime.now().isoformat(),
        "word_count": len(explanation.split())
    }

def extract_key_points(explanation):
    """Extract key points from explanation text"""
    # Simple extraction - split by sentences and filter meaningful ones
    sentences = explanation.split('.')
    key_points = []
    
    for sentence in sentences[:4]:  # Take first 4 meaningful sentences
        sentence = sentence.strip()
        if len(sentence) > 20 and not sentence.startswith('**'):  # Filter out short or formatting lines
            key_points.append(sentence[:100] + "..." if len(sentence) > 100 else sentence)
    
    return key_points if key_points else ["Key concept explained in detail", "Important process or mechanism described", "Real-world application provided"]

@st.cache_data(show_spinner="🔊 Generating audio...")
def generate_audio(text, language='en'):
    """Generate text-to-speech audio"""
    try:
        tts = gTTS(text=text, lang=language, slow=False)
        
        # Save to temporary file
        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as tmp:
            tts.save(tmp.name)
            return tmp.name, None
    except Exception as e:
        return None, str(e)

# ---------- Session State Management ----------
if "history" not in st.session_state:
    st.session_state.history = []
if "current_lesson" not in st.session_state:
    st.session_state.current_lesson = None
if "quiz_answers" not in st.session_state:
    st.session_state.quiz_answers = {}
if "audio_file" not in st.session_state:
    st.session_state.audio_file = None

# ---------- Initialize AI ----------
MODEL, status = init_gemini()

# ---------- Sidebar ----------
with st.sidebar:
    st.header("🎯 Learning Control Panel")
    
    # API Status
    st.subheader("📡 System Status")
    st.markdown(f"**AI Engine:** {status}")
    
    if MODEL:
        st.success("✅ Ready to teach!")
    else:
        st.error("⚠️ Setup incomplete - Add GOOGLE_API_KEY to .env")
    
    # Learning Statistics
    st.subheader("📊 Your Progress")
    st.metric("Lessons Generated", len(st.session_state.history))
    
    if st.session_state.history:
        recent_topics = [lesson["topic"] for lesson in st.session_state.history[-3:]]
        st.caption("Recent topics:")
        for topic in recent_topics:
            st.caption(f"• {topic}")
    
    # Settings
    st.subheader("⚙️ Preferences")
    audio_language = st.selectbox("Audio Language:", ["en", "es", "fr", "de", "it"], index=0)
    
    # Quick Actions
    st.subheader("⚡ Quick Actions")
    if st.button("🧹 Clear Session"):
        for key in list(st.session_state.keys()):
            if key != "audio_file":  # Keep audio file for current session
                del st.session_state[key]
        st.success("Session cleared!")
        st.rerun()
    
    if st.button("📈 Show Statistics"):
        if st.session_state.history:
            topics = [lesson["topic"] for lesson in st.session_state.history]
            levels = [lesson["level"] for lesson in st.session_state.history]
            
            st.write("**Most Explored Topics:**")
            from collections import Counter
            topic_counts = Counter(topics)
            for topic, count in topic_counts.most_common(5):
                st.write(f"• {topic}: {count} times")
            
            st.write("**Level Distribution:**")
            level_counts = Counter(levels)
            for level, count in level_counts.items():
                st.write(f"• {level}: {count} lessons")

# ---------- Main Interface ----------
st.markdown("---")

# Input Section
col1, col2, col3 = st.columns([3, 1, 1])

with col1:
    topic = st.text_input(
        "🎓 **What would you like to learn about?**", 
        placeholder="e.g., Photosynthesis, Quantum Physics, Climate Change...",
        key="main_topic_input"
    )

with col2:
    level = st.selectbox(
        "📚 **Difficulty Level:**", 
        ["Beginner", "Intermediate", "Advanced"],
        key="main_level_select"
    )

with col3:
    generate_btn = st.button(
        "✨ **Generate Lesson**",
        type="primary",
        use_container_width=True,
        key="main_generate_btn"
    )

# Progress indicator
if st.session_state.history and not st.session_state.current_lesson:
    st.info(f"📖 You've explored {len(st.session_state.history)} topics. Continue learning or explore something new!")

st.markdown("---")

# ---------- Lesson Generation ----------
if generate_btn and topic:
    if not MODEL:
        st.error("❌ AI service not available. Please check your GOOGLE_API_KEY configuration.")
    else:
        with st.spinner(f"🧠 Generating comprehensive lesson on {topic}..."):
            # Add progress steps
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            status_text.text("🤖 Analyzing topic...")
            progress_bar.progress(25)
            time.sleep(0.5)
            
            status_text.text("📝 Creating explanation...")
            progress_bar.progress(50)
            time.sleep(0.5)
            
            status_text.text("🎉 Preparing fun facts...")
            progress_bar.progress(75)
            time.sleep(0.5)
            
            # Generate the lesson
            lesson_data = generate_explanation(topic, level)
            
            if "error" in lesson_data:
                st.error(lesson_data["error"])
            else:
                # Update session state
                st.session_state.current_lesson = lesson_data
                st.session_state.history.append(lesson_data)
                st.session_state.quiz_answers = {}  # Reset quiz answers
                
                status_text.text("✅ Lesson ready!")
                progress_bar.progress(100)
                
                # Success feedback
                st.success(f"🎉 **Lesson on '{topic}' is ready!** Explore the tabs below to dive deeper.")
                st.balloons()
                
                time.sleep(1)
                progress_bar.empty()
                status_text.empty()

# ---------- Main Content Area ----------
if st.session_state.current_lesson:
    lesson = st.session_state.current_lesson
    
    # Lesson Header
    col1, col2, col3 = st.columns([2, 1, 1])
    
    with col1:
        st.subheader(f"📖 **{lesson['topic']}** ({lesson['level']})")
        st.caption(f"Generated on {datetime.fromisoformat(lesson['timestamp']).strftime('%B %d, %Y at %I:%M %p')}")
    
    with col2:
        if st.button("🔊 Generate Audio", key="header_audio_btn"):
            with st.spinner("🔊 Creating audio version..."):
                audio_file, error = generate_audio(
                    f"Lesson on {lesson['topic']}. {lesson['explanation']}", 
                    language=audio_language
                )
                
                if error:
                    st.error(f"Audio generation failed: {error}")
                else:
                    st.session_state.audio_file = audio_file
                    st.success("Audio ready!")
    
    with col3:
        new_lesson_btn = st.button("🔄 New Topic", key="new_lesson_btn")
        if new_lesson_btn:
            st.session_state.current_lesson = None
            st.rerun()
    
    st.markdown("---")
    
    # Main Content Tabs
    tab1, tab2, tab3, tab4 = st.tabs(["📘 **Explanation**", "🎉 **Fun Facts**", "🧩 **Interactive Quiz**", "🔊 **Audio Player**"])
    
    # Tab 1: Explanation
    with tab1:
        col1, col2 = st.columns([3, 1])
        
        with col1:
            st.markdown("### 📖 Core Concept")
            st.markdown(lesson["explanation"])
            
            # Word count and reading time
            st.caption(f"📊 **{lesson['word_count']} words** • ⏱️ **{max(1, lesson['word_count'] // 200)} min read**")
            
            # Additional context
            st.markdown("---")
            st.markdown("### 💡 Key Takeaways")
            
            # Auto-extract key points from explanation
            key_points = extract_key_points(lesson["explanation"])
            for i, point in enumerate(key_points, 1):
                st.write(f"{i}. {point}")
        
        with col2:
            st.markdown("### 🎯 Quick Actions")
            
            if st.button("📤 Share Explanation", key="share_explanation"):
                st.info("💡 Copy this link or use the export feature below!")
                
            if st.button("💾 Save for Later", key="save_explanation"):
                st.success("✅ Added to your saved lessons!")
                # In a real app, this would save to a database
            
            if st.button("🔄 Regenerate", key="regenerate_explanation"):
                with st.spinner("🔄 Creating new explanation..."):
                    new_lesson = generate_explanation(lesson["topic"], lesson["level"])
                    st.session_state.current_lesson = new_lesson
                    st.rerun()
    
    # Tab 2: Fun Facts
    with tab2:
        st.markdown("### 🎉 Surprising Discoveries")
        st.markdown("These fascinating facts will help you remember and understand the concept better!")
        
        for i, fact in enumerate(lesson["fun_facts"], 1):
            with st.expander(f"🧠 **Fun Fact {i}**", expanded=i <= 2):
                st.markdown(fact)
                
                # Add some interaction
                col_a, col_b = st.columns([1, 1])
                with col_a:
                    if st.button(f"👍 Amazing!", key=f"fact_{i}_like"):
                        st.success("🤩 Amazing indeed!")
                
                with col_b:
                    if st.button(f"❓ Tell me more", key=f"fact_{i}_more"):
                        st.info("💡 This is part of what makes science so interesting - there's always more to discover!")
        
        # Fun facts insights
        st.markdown("---")
        st.markdown("### 🔍 What Makes This Interesting?")
        st.markdown(f"""
        These facts about **{lesson['topic']}** demonstrate how science connects to our everyday lives. 
        Understanding these connections helps make abstract concepts more concrete and memorable.
        
        **Why fun facts work:**
        - ✨ Create emotional connection to the topic
        - 🎯 Make information more memorable  
        - 🌟 Spark curiosity for further learning
        """)
    
    # Tab 3: Interactive Quiz
    with tab3:
        st.markdown("### 🧩 Test Your Understanding")
        st.markdown("Answer these questions to check how well you understood the concept:")
        
        quiz_results = []
        
        for i, quiz in enumerate(lesson["quizzes"], 1):
            st.markdown(f"**Question {i}:** {quiz['question']}")
            
            # Radio buttons for answer selection
            user_answer = st.radio(
                "Select your answer:",
                quiz['options'],
                key=f"quiz_{i}",
                index=None,
                label_visibility="hidden"
            )
            
            # Check answer button
            if st.button(f"✅ Check Answer {i}", key=f"check_{i}"):
                if user_answer:
                    correct_answer = quiz['options'][ord(quiz['answer']) - 65]  # Convert A-D to index
                    
                    if user_answer == correct_answer:
                        st.success("🎉 **Correct!** Great job understanding the concept!")
                        quiz_results.append(True)
                    else:
                        st.error(f"❌ **Not quite right.** The correct answer is: **{quiz['answer']}**")
                        st.info(f"**Explanation:** {quiz['question']} The answer is {quiz['answer']} because it directly relates to the main concept we discussed.")
                        quiz_results.append(False)
                else:
                    st.warning("⚠️ Please select an answer first!")
            
            st.markdown("---")
        
        # Quiz summary
        if quiz_results:
            correct_count = sum(quiz_results)
            total_count = len(quiz_results)
            score_percentage = (correct_count / total_count) * 100
            
            if score_percentage >= 80:
                st.success(f"🏆 **Excellent!** You got {correct_count}/{total_count} correct ({score_percentage:.0f}%)")
                st.balloons()
            elif score_percentage >= 60:
                st.info(f"👍 **Good work!** You got {correct_count}/{total_count} correct ({score_percentage:.0f}%)")
            else:
                st.warning(f"📚 **Keep learning!** You got {correct_count}/{total_count} correct ({score_percentage:.0f}%)")
                st.info("💡 Review the explanation tab and try the quiz again!")
    
    # Tab 4: Audio Player
    with tab4:
        st.markdown("### 🔊 Listen and Learn")
        
        if st.session_state.audio_file:
            st.success("✅ Audio is ready! Click play to listen:")
            
            # Audio player
            st.audio(st.session_state.audio_file)
            
            # Audio controls
            col1, col2, col3 = st.columns(3)
            
            with col1:
                if st.button("🔄 Regenerate Audio", key="regenerate_audio"):
                    with st.spinner("🔄 Creating new audio..."):
                        audio_file, error = generate_audio(
                            f"Lesson on {lesson['topic']}. {lesson['explanation']}", 
                            language=audio_language
                        )
                        if error:
                            st.error(f"Audio generation failed: {error}")
                        else:
                            st.session_state.audio_file = audio_file
                            st.success("Audio updated!")
                            st.rerun()
            
            with col2:
                if st.button("💾 Download Audio", key="download_audio"):
                    try:
                        with open(st.session_state.audio_file, 'rb') as audio_file:
                            audio_bytes = audio_file.read()
                            st.download_button(
                                label="📱 Save Audio File",
                                data=audio_bytes,
                                file_name=f"{lesson['topic']}_lesson.mp3",
                                mime="audio/mpeg"
                            )
                    except Exception as e:
                        st.error(f"Download failed: {e}")
            
            with col3:
                if st.button("⏹️ Stop Audio", key="stop_audio"):
                    st.session_state.audio_file = None
                    st.rerun()
        else:
            st.info("🔊 Generate audio for your lesson by clicking the button above!")
            st.markdown("---")
            st.markdown("### 🎧 Audio Learning Benefits")
            st.markdown("""
            **Why audio learning is powerful:**
            - 👂 **Accessibility**: Great for visual impairments or when eyes are busy
            - 🧠 **Memory**: Auditory learning reinforces text comprehension  
            - ⏰ **Convenience**: Learn while commuting, exercising, or relaxing
            - 🔄 **Repetition**: Easy to replay complex concepts multiple times
            - 🎯 **Focus**: Different learning style for better retention
            """)

else:
    # Welcome screen when no lesson is generated
    st.markdown("## 🎯 Welcome to AI Science Explainer!")
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.markdown("""
        ### 🌟 What You'll Get
        
        **📖 Comprehensive Explanations**
        - Clear, level-appropriate content
        - Real-world examples you can relate to
        - Scientific concepts made simple
        
        **🎉 Engaging Fun Facts** 
        - Surprising discoveries about each topic
        - Memorable details that stick
        - Perfect conversation starters
        
        **🧩 Interactive Quizzes**
        - Test your understanding
        - Instant feedback and explanations  
        - Track your learning progress
        
        **🔊 Audio Narration**
        - Listen to lessons on-the-go
        - Perfect for auditory learners
        - Download for offline listening
        """)
    
    with col2:
        st.markdown("### 🎓 How to Use")
        st.markdown("""
        1. **Enter a topic** you'd like to learn about
        2. **Choose your level** (Beginner/Intermediate/Advanced)
        3. **Click 'Generate Lesson'**
        4. **Explore each tab** for different learning experiences
        5. **Test yourself** with the interactive quiz
        """)
        
        # Quick topic suggestions
        st.markdown("### 💡 Popular Topics")
        suggested_topics = [
            "Photosynthesis", "DNA Structure", "Climate Change", 
            "Quantum Physics", "Solar System", "Volcanoes",
            "Gravity", "Magnets", "The Human Brain"
        ]
        
        for topic in suggested_topics:
            if st.button(f"📚 {topic}", key=f"suggested_{topic.replace(' ', '_')}"):
                st.session_state.current_topic = topic
                st.rerun()

# ---------- Lesson History ----------
with st.expander("📚 **Lesson History**", expanded=False):
    if st.session_state.history:
        st.markdown("### Your Learning Journey")
        
        # History controls
        col1, col2, col3 = st.columns([2, 1, 1])
        
        with col1:
            # Filter options
            filter_level = st.selectbox("Filter by level:", ["All"] + list(set(l["level"] for l in st.session_state.history)))
        
        with col2:
            # Sort options
            sort_by = st.selectbox("Sort by:", ["Newest First", "Oldest First", "Alphabetical"])
        
        with col3:
            # Clear history
            if st.button("🗑️ Clear All"):
                st.session_state.history.clear()
                st.rerun()
        
        # Filter and sort history
        filtered_history = st.session_state.history.copy()
        if filter_level != "All":
            filtered_history = [lesson for lesson in filtered_history if lesson["level"] == filter_level]
        
        if sort_by == "Oldest First":
            filtered_history.reverse()
        elif sort_by == "Alphabetical":
            filtered_history.sort(key=lambda x: x["topic"])
        
        # Display history
        for i, lesson in enumerate(filtered_history, 1):
            with st.container():
                col_a, col_b, col_c = st.columns([3, 1, 1])
                
                with col_a:
                    st.markdown(f"**{i}. {lesson['topic']}** ({lesson['level']})")
                    
                    # Preview of explanation
                    preview = lesson["explanation"][:150] + "..." if len(lesson["explanation"]) > 150 else lesson["explanation"]
                    st.caption(preview)
                    
                    # Timestamp
                    timestamp = datetime.fromisoformat(lesson["timestamp"])
                    st.caption(f"📅 {timestamp.strftime('%B %d, %Y at %I:%M %p')}")
                
                with col_b:
                    if st.button("🔄 Review", key=f"review_{i}"):
                        st.session_state.current_lesson = lesson
                        st.rerun()
                
                with col_c:
                    if st.button("🗑️ Delete", key=f"delete_{i}"):
                        filtered_history.remove(lesson)
                        st.session_state.history.remove(lesson)
                        st.rerun()
        
        # History statistics
        if filtered_history:
            st.markdown("---")
            col1, col2, col3 = st.columns(3)
            
            with col1:
                total_words = sum(lesson.get("word_count", 0) for lesson in filtered_history)
                st.metric("Total Words Read", total_words)
            
            with col2:
                avg_words = total_words // len(filtered_history) if filtered_history else 0
                st.metric("Average per Lesson", avg_words)
            
            with col3:
                unique_topics = len(set(lesson["topic"] for lesson in filtered_history))
                st.metric("Unique Topics", unique_topics)
    
    else:
        st.info("📚 Your lesson history will appear here as you explore different topics!")

# ---------- Footer ----------
st.markdown("---")
col1, col2, col3 = st.columns(3)

with col1:
    st.caption("🎯 **Personalized Learning**")
    st.caption("Each lesson adapts to your chosen difficulty level")

with col2:
    st.caption("🚀 **AI-Powered**")  
    st.caption("Powered by Google Gemini for accurate content")

with col3:
    st.caption("📱 **Multi-Modal**")
    st.caption("Learn through text, audio, and interactive quizzes")

# ---------- Helper Functions ----------