import streamlit as st

# Title of the app
st.title("Science Topic Explorer 🔬")

# Text input field where user can type a topic
topic = st.text_input("Enter a science topic:")

# Button that triggers the description
if st.button("Describe"):
    # When clicked, this code block runs
    st.write(f"{topic} is an interesting area of science!")
