import streamlit as st
#import streamlit_authenticator as stauth
#from pymongo import MongoClient
#import certifi
import yaml
from yaml.loader import SafeLoader
import streamlit_authenticator as stauth

# MongoDB connection setup
#uri = st.secrets.mongo.uri
#client = MongoClient(uri, tlsCAFile=certifi.where())
#db = client["HallFarming"]
#users_collection = db["Users"]

def load_content():
    st.title("Welcome to Hall Farming")

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