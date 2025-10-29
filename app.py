import streamlit as st
import google.generativeai as genai
from dotenv import load_dotenv
import os

# Load API key
load_dotenv()
api_key = os.getenv("GOOGLE_API_KEY")
genai.configure(api_key=api_key)

# Set up the model
model = genai.GenerativeModel("gemini-2.0-flash")

# Streamlit UI
st.title("🔬 AI Science Explainer (Gemini)")

topic = st.text_input("Enter a science topic:")

if st.button("Explain"):
    if not topic:
        st.warning("Please enter a topic before clicking Explain.")
    else:
        prompt = f"Explain the science topic '{topic}' in simple terms."

        try:
            response = model.generate_content(prompt)
            st.write(response.text)
        except Exception as e:
            st.error(f"⚠️ API Error: {e}")
