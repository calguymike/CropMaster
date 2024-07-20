import streamlit as st
import yaml
from yaml.loader import SafeLoader
import streamlit_authenticator as stauth

def load_content():
    # Set tabs at top of page
    tab1, tab2 = st.tabs(["Log Spreading", "Settings"])

    with tab1:
        st.title("Log Spreading")

    with tab2:
        st.title("Settings")

def authenticate_user():
    with open('.streamlit/config.yaml') as file:
        config = yaml.load(file, Loader=SafeLoader)

    authenticator = stauth.Authenticate(
        config['credentials'],
        config['cookie']['name'],
        config['cookie']['key'],
        config['cookie']['expiry_days'],
        config['pre-authorized']
    )
    authenticator.login()

    if st.session_state["authentication_status"]:
        authenticator.logout()
        st.write(f'Welcome *{st.session_state["name"]}*')
        load_content()
    elif st.session_state["authentication_status"] is False:
        st.error('Username/password is incorrect')
    elif st.session_state["authentication_status"] is None:
        st.warning('Please enter your username and password')

authenticate_user()
