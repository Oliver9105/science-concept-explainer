import streamlit as st
import google.generativeai as genai
from dotenv import load_dotenv
import os

load_dotenv()
genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))

model = genai.GenerativeModel("gemini-2.0-flash")
st.title("🔬 Persistent AI Science Explainer")

# Remember user input
topic = st.text_input("Enter a science topic:")

# Initialize session state keys
if "explanation" not in st.session_state:
    st.session_state.explanation = ""

if st.button("Explain"):
    if topic:
        prompt = f"Explain the science topic '{topic}' in simple terms."
        response = model.generate_content(prompt)
        st.session_state.explanation = response.text
    else:
        st.warning("Please enter a topic.")

# Display stored explanation (persists after reruns)
if st.session_state.explanation:
    st.markdown("### Explanation")
    st.write(st.session_state.explanation)
