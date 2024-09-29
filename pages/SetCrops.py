import streamlit as st
import streamlit_authenticator as stauth
from pymongo import MongoClient
import certifi
import pandas as pd
from datetime import datetime
import ast

#Connect to database and initialise collections
uri = st.secrets.mongo.uri
client = MongoClient(uri, tlsCAFile=certifi.where())

# Set databases as variables
db = client.HallFarming
fields_collection = db.Land
crops_collection = db.Crops
user_db = client.Users
users_collection = user_db.Credentials

def get_crop(field, selected_year):
    cropping = field.get("Cropping", {})
    return_crop = ""
    if cropping:
        for crop in cropping:
            if str(crop.get("CropYear", "")) == str(selected_year):
                return_crop = crop
    
    return return_crop


def load_content():
    # Populated select box with list of farms
    selected_farm = st.selectbox("Select Farm", fields_collection.distinct("Farm"))
    selected_year = st.number_input("Select Crop Year (year crop is harvested)", value=datetime.now().year)
    # find all field names in the selected farm and add to the fields list
    # fields = [field["FieldName"] for field in fields_collection.find({"Farm": selected_farm}, {"FieldName": 1, "_id": 0})]
    fields = list(fields_collection.find({"Farm": selected_farm}))
    for field in fields:
        field_name = field["FieldName"]
        cropping = get_crop(field, selected_year)
        try:
            crop_name = cropping.get("Crop", "")
        except:
            crop_name = ""
        

    ''' # Get crop names from crop database and store in crops variable
    available_crops = [crop["Crop"] for crop in crops_collection.find({}, {"Crop": 1, "_id": 0})]
    # Add fields to dataframe
    # TODO - Populate crop with selected year crop
    # for field in fields_data:
        # field_name = field["FieldName"]
        # cropping_data = field.get("Cropping", "")
    


    df = pd.DataFrame({'Field': fields, 'Crop': ""})
    # Set crop column in df to catagory type, with crops as categories
    df['Crop'] = df['Crop'].astype(pd.CategoricalDtype(available_crops))

    # Store the user modified values in edited_df
    edited_df = st.data_editor(df, num_rows="dynamic", use_container_width = True)

    if st.button("Save Changes"):
        differences = edited_df.compare(df)
        changed_ids = differences.index.get_level_values(0).unique()
        print(changed_ids)

        for index in changed_ids:
            field_name = edited_df.loc[index, 'Field']
            selected_crop = edited_df.loc[index, 'Crop']

            result = fields_collection.update_one(
                {"FieldName": field_name, "Farm": selected_farm},  # Match by FieldName and Farm
                {"$set": {"Cropping": selected_crop}}  # Update the Cropping field with the new crop
            )

            if result.modified_count > 0:
                st.success(f"Updated {field_name} with crop {selected_crop}.")
            else:
                st.warning(f"No changes made for {field_name}.") '''


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