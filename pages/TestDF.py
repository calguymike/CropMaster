import streamlit as st
import streamlit_authenticator as stauth
from pymongo import MongoClient
import certifi
import pandas as pd

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
    # Read data from MongoDB
    cursor = crops_collection.find({})
    original_data = pd.DataFrame(list(cursor))  # Convert MongoDB cursor to DataFrame

    # Keep a copy of the _id field separately
    id_series = original_data['_id']

    # Drop the _id column from both original and displayed DataFrame
    original_data_without_id = original_data.drop(columns=['_id'])
    display_data = original_data_without_id.copy()

    # Display the DataFrame without the _id column in Streamlit for user editing
    edited_data = st.data_editor(display_data)

    # After the user finishes editing
    if st.button("Submit Changes"):
        # Compare the edited DataFrame with the original one (excluding _id column)
        differences = edited_data.compare(original_data_without_id)

        # Get the indices of rows with changes
        changed_ids = differences.index.get_level_values(0).unique()

        # Re-insert the _id column back into the edited DataFrame for updates
        edited_data['_id'] = id_series

        # Write back only the changed rows to the MongoDB collection
        for index in changed_ids:
            # Convert the changed row back to a dictionary
            changed_row = edited_data.loc[index].to_dict()

            # Use the MongoDB _id to update the corresponding document
            crops_collection.update_one({"_id": changed_row["_id"]}, {"$set": changed_row})

        st.success(f"Updated {len(changed_ids)} documents in the database.")

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
