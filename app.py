import streamlit as st
import google.generativeai as genai
from dotenv import load_dotenv
import os

# Load environment variables
load_dotenv()
genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))

# Initialize model
model = genai.GenerativeModel("gemini-2.0-flash")

# App Title
st.title("🧠 AI Science Explainer")

# Intro section
st.markdown("""
Welcome to the **AI Science Explainer**!  
Type any science topic below and select your preferred difficulty level to get a clear, tailored explanation.  
""")

st.divider()

# --- 🧩 INPUT SECTION ---
st.header("🎓 Choose Your Topic")
topic = st.text_input("🔍 Enter a science topic:", placeholder="e.g., Photosynthesis")

level = st.selectbox(
    "📘 Select difficulty level:",
    ["Beginner", "Intermediate", "Advanced"]
)

st.divider()

# --- ⚙️ ACTION SECTION ---
if "explanation" not in st.session_state:
    st.session_state.explanation = ""

st.markdown("### 🚀 Generate Explanation")
if st.button("✨ Explain Topic"):
    if topic:
        prompt = f"""
        You are a science teacher explaining '{topic}' at a {level} level.

        - If Beginner: Use simple terms and analogies.
        - If Intermediate: Add moderate details and a real-world example.
        - If Advanced: Dive into the underlying scientific theory and terminology.

        Return a clear, engaging explanation suitable for the chosen level.
        """
        try:
            response = model.generate_content(prompt)
            st.session_state.explanation = response.text
        except Exception as e:
            st.error(f"⚠️ API Error: {e}")
    else:
        st.warning("Please enter a topic before clicking Explain.")

st.divider()

# --- 📖 OUTPUT SECTION ---
if st.session_state.explanation:
    st.header(f"🧩 {level} Explanation")
    st.write(st.session_state.explanation)
    st.markdown("---")
    st.success("💡 Tip: Try switching levels to compare how the explanation changes!")
