import streamlit as st
import streamlit_authenticator as stauth
from pymongo import MongoClient
import certifi
import streamlit_authenticator as stauth
from streamlit_authenticator.utilities.hasher import Hasher

#Connect to database and initialise collections
uri = st.secrets.mongo.uri
client = MongoClient(uri, tlsCAFile=certifi.where())

# Set databases as variables
db = client.HallFarming
fields_collection = db.Land
crops_collection = db.Crops
user_db = client.Users
users_collection = user_db.Credentials

def load_content():
    tab1, tab2 = st.tabs(["Home", "User Settings"])
    with tab1:
        st.title("Welcome to Hall Farming")
        st.write(f'Welcome *{st.session_state["name"]}*')

    with tab2:
        try:
            with st.form("Set New Password"):
                new_password = st.text_input("New Password", type="password")
                confirm_password = st.text_input("Confirm New Password", type="password")
                submit_button = st.form_submit_button("Submit")

                if submit_button:
                    username = st.session_state["username"]
                    if new_password != confirm_password:
                        st.error("Passwords do not match")
                    elif new_password and confirm_password:
                        hashed_password = Hasher([new_password]).generate()[0]
                        filter = {f'usernames.{username}': {'$exists': True}}
                        update = {'$set': {f'usernames.{username}.password': hashed_password}}
                        update_result = users_collection.update_one(filter, update)
                    else:
                        st.warning("Please enter a new password")
                    if update_result.modified_count > 0:
                        st.success("Password modified successfully")
                    else:
                        st.error("Failed to update the password")
                else:
                    st.warning("Please enter a new password")
        except Exception as e:
            st.error(f"An error occurred: {e}")

def authenticate_user():
    credentials = users_collection.find_one({}, {"_id": 0, "usernames": 1})
    cookie_name = users_collection.find_one({}, {"cookie.name": 1, "_id": 0})['cookie']['name']
    cookie_key = users_collection.find_one({}, {"cookie.key": 1, "_id": 0})['cookie']['key']
    cookie_expiry = users_collection.find_one({}, {"cookie.expiry_days": 1, "_id": 0})['cookie']['expiry_days']
    pre_auth = users_collection.find_one({}, {"pre-authorized.emails": 1, "_id": 0}).get('pre-authorized', {}).get('emails', [])

    authenticator = stauth.Authenticate(
        credentials,
        cookie_name,
        cookie_key,
        cookie_expiry,
        pre_auth
    )
    authenticator.login()
    

    if st.session_state["authentication_status"]:
        authenticator.logout()
        st.write(f'Welcome *{st.session_state["name"]}*')
        # Load app
        load_content()
    elif st.session_state["authentication_status"] is False:
        st.error('Username/password is incorrect')
    elif st.session_state["authentication_status"] is None:
        st.warning('Please enter your username and password')

authenticate_user()