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
        prompt = f"""
You are a friendly and knowledgeable science teacher.
Explain the science topic: "{topic}" at three levels of understanding.

1. Beginner Level: Use simple language, short sentences, and a relatable analogy.
2. Intermediate Level: Provide more scientific detail, use basic technical terms, and include a real-world example.
3. Advanced Level: Dive deep into principles, equations, or advanced concepts suitable for a university student.

End with one curiosity-driven question to encourage further exploration.
"""


        try:
            response = model.generate_content(prompt)
            st.write(response.text)
        except Exception as e:
            st.error(f"⚠️ API Error: {e}")
