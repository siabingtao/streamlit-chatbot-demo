# Streamlit Chatbot Frontend POC
This app provides a ChatGPT like frontend UI using Streamlit. You will need to provide your own working APIs for
1. Invoking a chatbot
2. Retrieving session titles
3. Retrieving chat history per session

## Status:
Backend APIs (previously hosted on AWS API Gateway) have been decomissioned. As a result, the demo currently is not integrated to a live backend.

## Planned updates:
- Do a FastAPI mock backend to show the working frontend

## Quick Start:
Create environment
```
pip install -r requirements.txt
```
Run the streamlit app
```
streamlit run frontend_app.py
```