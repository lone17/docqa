import requests
import streamlit as st

st.title("Document QA")

chat_endpoint = "http://127.0.0.1:8000/chat"

# Initialize chat history
if "messages" not in st.session_state:
    st.session_state.messages = []

# Display chat messages from history on app rerun
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])


def generate_chat_response(placeholder, content):
    full_response = ""
    for chunk in content:
        full_response += chunk or ""
        placeholder.markdown(full_response + "▌")

    placeholder.markdown(full_response)

    return full_response


# Accept user input
if prompt := st.chat_input("What do you you want to know about Generative Agents?"):
    # Add user message to chat history
    st.session_state.messages.append({"role": "user", "content": prompt})

    # Display user message in chat message container
    with st.chat_message("user"):
        st.markdown(prompt)

    # Display assistant response in chat message container
    with st.chat_message("assistant"):
        message_placeholder = st.empty()

        response = requests.post(chat_endpoint, json={"message": prompt}).json()

        answer = response["answer"]
        references = response["references"]

        full_response = generate_chat_response(message_placeholder, answer)

    st.session_state.messages.append({"role": "assistant", "content": full_response})
