import streamlit as st
import openai
from dotenv import load_dotenv
import os

# Load environment variables from .env file
load_dotenv()

# Access the API key securely
openai.api_key = os.getenv("OPENAI_API_KEY")

# Streamlit UI
st.title("🔬 AI Science Explainer")

topic = st.text_input("Enter a science topic:")
if st.button("Explain"):
    if not topic:
        st.warning("Please enter a topic before clicking Explain.")
    else:
        # Create a prompt for the OpenAI API
        prompt = f"Explain the science topic '{topic}' in simple terms."
        
        # Call OpenAI's ChatCompletion API
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}]
        )
        
        explanation = response["choices"][0]["message"]["content"]
        st.write(explanation)
