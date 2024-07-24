from pymongo import MongoClient
import certifi
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import streamlit_authenticator as stauth
from datetime import datetime
from bson import ObjectId

# Set global variables 
HF = {}         # Original database pulled from cloud
HF_loc = {}     # Database to apply modifications to

def update_local():
    global HF_loc
    global HF
    HF_loc = HF

def initialize_db():
    global HF
    #Connect to database
    uri = st.secrets.mongo.uri
    client = MongoClient(uri, tlsCAFile=certifi.where())
    db = client.HallFarming
    users_db = client.Users
    HF = {"fields_collection": db.Land, 
          "crops_collection": db.Crops,
          "dressings_collection": db.Dressings,
          "varieties_collection": db.Varieties,
          "users_collection": users_db.Credentials}
    if HF:
        authenticate_user()
    else:
        print("Error: Could not connect to database")

def get_crop(field, farm):
    global HF
    # Take farm and field name as arguments (field name not unique)
    # Find the field in the dictionary
    returned_field = HF["fields_collection"].find_one({"FieldName": field, "Farm": farm})
    # Return the cropping information for the field as a dictionary
    cropping = returned_field.get("Cropping", {}).get("Crops", [])
    return cropping
    

def authenticate_user():
    global HF
    credentials = HF["users_collection"].find_one({}, {"_id": 0, "usernames": 1})
    cookie_name = HF["users_collection"].find_one({}, {"cookie.name": 1, "_id": 0})['cookie']['name']
    cookie_key = HF["users_collection"].find_one({}, {"cookie.key": 1, "_id": 0})['cookie']['key']
    cookie_expiry = HF["users_collection"].find_one({}, {"cookie.expiry_days": 1, "_id": 0})['cookie']['expiry_days']
    pre_auth = HF["users_collection"].find_one({}, {"pre-authorized.emails": 1, "_id": 0}).get('pre-authorized', {}).get('emails', [])

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


def load_content():
    # last_crop = get_crop("Shed Field", "Kingthorpe")[-1].get("Crop", "")
    # st.write(last_crop)
    # Set tabs at top of page
    global HF_loc
    update_local()
    
    tab1, tab2, tab3, tab4 = st.tabs(["Field Cropping", "Manage Crops", "Manage Fields", "Settings"])
    with tab1:
        st.title("Field Cropping")
        selected_farm = st.selectbox("Select Farm", HF_loc["fields_collection"].distinct("Farm"))
        fields_in_farm = HF_loc["fields_collection"].distinct("FieldName", {"Farm": selected_farm})
        if selected_farm:
            selected_field = st.selectbox("Select a field", fields_in_farm)
            num_crops = len(get_crop(selected_field, selected_farm))
            st.write(f"Number of crops: {num_crops}")

        

    with tab2:
        st.title("Manage Crops")

    with tab3:
        st.title("Manage Fields")

    with tab4:
        st.title("Settings")
    

initialize_db()