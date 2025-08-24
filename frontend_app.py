import os
import streamlit as st
import streamlit_authenticator as stauth
from streamlit_extras.mention import mention
import yaml
import time
from yaml.loader import SafeLoader
import requests
import json
from datetime import datetime
import pandas as pd
from dotenv import load_dotenv
load_dotenv()

st.set_page_config(page_title="Chatbot Landing Page", page_icon="🤖")

with open("./auth/config_multitenant.yaml") as file:
    config = yaml.load(file, Loader = SafeLoader)
    
authenticator = stauth.Authenticate(
    config['credentials'],
    config['cookie']['name'],
    config['cookie']['key'],
    config['cookie']['expiry_days'],
    config['pre-authorized']
)

# to map each document name to its respective link to access the document
s3_url_link = {"hep-b-healthcare.pdf": os.getenv("HEP_B_HEALTHCARE_PDF"),
               "IHP-Individual-Member-Handbook-Singapore.pdf": os.getenv("IHP_INDIVIDUAL_MEMBER_HANDBOOK_SINGAPORE_PDF"),
               "tb-healthcare.pdf": os.getenv("TB_HEALTHCARE_PDF"),
               "Congressional Record Volume 170.docx": os.getenv("CONGRESSIONAL_RECORD_VOLUME_170_DOCX"),
               "Digital Economy Partnership Agreement.pdf": os.getenv("DIGITAL_ECONOMY_PARTNERSHIP_AGREEMENT_PDF"),
               "free-trade-agreement.pdf": os.getenv("FREE_TRADE_AGREEMENT_PDF"),
               "state-of-union.pdf": os.getenv("STATE_OF_UNION_PDF"),
               "mcbook-user-guide.pdf": os.getenv("MCBOOK_USER_GUIDE_PDF"),
               "Office 365 Project Online.docx": os.getenv("OFFICE_365_PROJECT_ONLINE_DOCX")}

# define helper function for generating response
def response_generator(question, username, tenant, session_id, prompt_template):
    global retrieved_citation
    global document_retrieved_from
    global similarity_score
    global page_no
    url = os.getenv("INVOKE_RAG_ORCHESTRATOR_URL")
    headers = {
    "Content-Type": "application/json"
    }
    
    # fill in the payload with session variables
    payload = {"user_id": username,
               "tenant_id": tenant,
               "question": question,
               "session_id": session_id,
               "prompt_template": prompt_template}
    
    with st.spinner("Retrieving LLM output.."):
        response = requests.post(url, headers = headers, data = json.dumps(payload))
        llm_output = json.loads(response.content.decode("utf-8"))["llm_answer"]
        retrieved_citation = json.loads(response.content.decode("utf-8"))["citation"]
        document_retrieved_from = json.loads(response.content.decode("utf-8"))["document_retrieved_from"]
        similarity_score = json.loads(response.content.decode("utf-8"))["similarity_score"]
        page_no = json.loads(response.content.decode("utf-8"))["page_no"]
    
    for word in llm_output.split():
        yield word + " "
        time.sleep(0.05)

# define helper function to retrieve chat hist
def retrieve_chat_hist(username, tenant):
    url = os.getenv("RETRIEVE_CHAT_HIST_URL")
    headers = {
    "Content-Type": "application/json"
    }
    payload = {"user_id": username,
               "tenant_id": tenant}
    response = requests.post(url, headers = headers, data = json.dumps(payload))
    chat_hist_output = json.loads(response.content.decode("utf-8"))["dynamodb_res"]['Items']
    return chat_hist_output

# define helper function to retrieve ALL the sessions title
def retrieve_sess_title(username, tenant):
    url = os.getenv("RETRIEVE_SESS_TITLE_URL")
    headers = {
    "Content-Type": "application/json"
    }
    payload = {"user_id": username,
               "tenant_id": tenant}
    response = requests.post(url, headers = headers, data = json.dumps(payload))
    session_titles = json.loads(response.content.decode("utf-8"))["session_title_res"]["Items"]
    return session_titles

# define helper function to retrieve to retrieve the generated session ID and summarised session title (only applies for new chat/session)
def new_chat_sess_id_title(tenant_index, user_question, user_id):
    url = os.getenv("NEW_CHAT_SESS_ID_TITLE_URL")
    headers = {
    "Content-Type": "application/json"
    }
    tenant_index = tenant_index + "-index"
    timestamp = datetime.now().isoformat()
    payload = {"tenant_id": tenant_index,
               "question": user_question,
               "user_id": user_id,
               "timestamp": timestamp}
    response = requests.post(url, headers = headers, data = json.dumps(payload))
    session_id = json.loads(response.content.decode("utf-8"))["session_id"]
    session_title = json.loads(response.content.decode("utf-8"))["summarised_title"]
    return session_id, session_title

# define helper function to update session
def update_session(prompt, tenant_id, username):
    with st.spinner("Creating new session title.."):
        print(f"In this callback, my tenant is {tenant_id}, my prompt is {prompt} and username is {username}")
        current_session_id, current_session_title = new_chat_sess_id_title(tenant_id, prompt, username)            
        print(f"new session ID is {current_session_id} and new session title is {current_session_title}")
        # rename current "New Session" to the summarised title
        titles_to_display[0] = current_session_title
        # add it another "New Session"
        titles_to_display.insert(0, "New Session")
    return current_session_id, current_session_title

# function to change the selected option (can just click on the the 2nd session, and it will load in the New Session and summarised session title)
def change_selected_option(new_option):
    st.session_state.selected_option = new_option
    print(f"selected radio option changed to {new_option}")
    
# strealit authenticator module
name, authentication_status, username = authenticator.login("main", fields = {'Form name': 'Enter your credentials below to access AIDA :sunglasses:'})
print(name)
print(authentication_status)
print(username)

if authentication_status: # once authenticated, go in chatbot landing page
    print(f"Successfully logged in as {name}")
    st.title("Hello, I am a :rainbow[Chatbot].")
    st.subheader('Use me below :sunglasses:', divider='rainbow')
    tenant_id = config["credentials"]["usernames"][username]["tenant"]
    print(tenant_id)

    # create sidebar to let user choose model etc.
    with st.sidebar:
        # select prompt template to use
        prompt_template = st.selectbox("Prompt Template", ("Generative AI", "Direct Lifting")) # indicating index = None means that the select box will be initialised w/o any selections
        
        # print("========")
        chat_hist = retrieve_chat_hist(username, tenant_id)

        # retrieve all unique sessions 
        df_chat_hist = pd.DataFrame(chat_hist)
        df_chat_hist = df_chat_hist.sort_values(["timestamp"], ascending = False) # so when i retrieve the session id, it will be displayed from most recent to earliest
        print(df_chat_hist.shape)
        session_ids = df_chat_hist["session_id"].unique().tolist()
        df_chat_hist = df_chat_hist.sort_values(["timestamp"], ascending = True) # so when i display the chat hist for each session, will start from latest to most recent
        chat_hist = df_chat_hist.to_dict(orient = "records") # convert back to dictionary

        session_titles = retrieve_sess_title(username, tenant_id)
        df_session_titles = pd.DataFrame(session_titles)
        # map the session_ids to their respective session titles (need another API gateway? abit weird..)
        df_session_id_title = pd.merge(df_chat_hist[["session_id", "timestamp"]], df_session_titles[["session_id", "session_title"]], on = "session_id", how = "inner")
        df_session_id_title = df_session_id_title.sort_values(["timestamp"], ascending = False)
        titles_to_display = df_session_id_title["session_title"].unique().tolist()
        titles_to_display.insert(0, "New Session")
        
        # on first login, initialise selected session as New Session
        if "selected_option" not in st.session_state:
            st.session_state.selected_option = "New Session"
        # check if it is a scenario where someone logout and login to another account. if yes, initialise as new session
        # if i don't do this, will have error when we create the radio button below
        if st.session_state.selected_option not in titles_to_display:
            st.session_state.selected_option = "New Session"
                    
        print(st.session_state.selected_option)
        
        # create radio button to display all the different sessions
        sessions = st.radio("Previous Sessions", titles_to_display, index = titles_to_display.index(st.session_state.selected_option))        
        authenticator.logout("Logout", "main") # display logout button at sidebar
        
    # initialise session_state messages as chat_hist
    st.session_state.messages = chat_hist 

    # display chat messages from history on app rerun
    # use a for loop to iterate through chat history and display each message in the chat container
    print(sessions)
    if sessions != "New Session":
        # print("Reloading session chat hist. maybe this will work!")
        # retrieve all the chat that are from that particular session ID
        current_session_id = df_session_id_title.loc[df_session_id_title["session_title"] == sessions, "session_id"].iloc[0]
        print(current_session_id)
        # if it is not a new session, to list down all the chat history stuff
        for message in st.session_state.messages:
            if current_session_id != message["session_id"]:
                continue
            else:
                # print("i am here.")
                # with st.chat_message(message["role"]):
                # add in user query
                with st.chat_message("user"):
                    st.markdown(message["user_question"])
                    
                # add in LLM response
                with st.chat_message("assistant"):
                    st.markdown(message["generated_answer"])

    # use st.chat_input to provide a widget for users to type in the message
    prompt = st.chat_input(placeholder = f"Hello {name} 👋, how can I help you today?")

    if prompt: # when user typed in prompt (doesnt matter new session or not)
        # display user qns in chat container
        with st.chat_message("user"):
            st.markdown(prompt)
        if sessions == "New Session":
            # if it is new session, neaed to generate session ID and create session title for display in streamlit
            current_session_id, current_session_title = update_session(prompt, tenant_id, username)
        with st.chat_message("assistant"): # display assistant response in chat message container
            response = st.write_stream(response_generator(prompt, username, tenant_id, current_session_id, prompt_template))
            
            # only return the citation if score >= 0.55
            if similarity_score >= 0.55:
                s3_source_url = s3_url_link[document_retrieved_from]
                # add in page number behind
                s3_source_url = s3_source_url + "#page=" + str(page_no)
                mention(label = f"Source: {retrieved_citation}", url = s3_source_url) 
            
        # if new session, rerun everything, to change the current session title + create new "New Session"
        if sessions == "New Session": 
            change_selected_option(current_session_title)
            # st.rerun()
            
# incorrect username/password
elif st.session_state["authentication_status"] is False:
    st.error("Username/password is incorrect.")
