import streamlit as st
import google.generativeai as genai
from dotenv import load_dotenv
import os

# Load API key
load_dotenv()
genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))

# Initialize model
model = genai.GenerativeModel("gemini-2.0-flash")

# Streamlit UI
st.title("🔬 AI Science Explainer with Levels")

# User inputs
topic = st.text_input("Enter a science topic:")
level = st.selectbox(
    "Choose difficulty level:",
    ["Beginner", "Intermediate", "Advanced"]
)

# Initialize session state
if "explanation" not in st.session_state:
    st.session_state.explanation = ""

# Handle button click
if st.button("Explain"):
    if topic:
        # Dynamically adjust prompt based on difficulty level
        prompt = f"""
        You are a science teacher explaining the topic '{topic}' at a {level} level.

        - If Beginner: Use simple terms, short sentences, and analogies.
        - If Intermediate: Include moderate detail and one real-world example.
        - If Advanced: Explain deeply using technical terms, equations, and theory.

        Write a clear explanation suitable for the chosen level.
        """

        try:
            response = model.generate_content(prompt)
            st.session_state.explanation = response.text
        except Exception as e:
            st.error(f"⚠️ API Error: {e}")
    else:
        st.warning("Please enter a topic first.")

# Display explanation
if st.session_state.explanation:
    st.markdown(f"### {level} Explanation:")
    st.write(st.session_state.explanation)
