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
    selected_farm = st.selectbox("Select Farm", fields_collection.distinct("Farm"))
   # fields = list(fields_collection.find({"Farm": selected_farm}, {"FieldName": 1, "_id": 0}))
    fields = [field["FieldName"] for field in fields_collection.find({"Farm": selected_farm}, {"FieldName": 1, "_id": 0})]
    crops = [crop["Crop"] for crop in crops_collection.find({}, {"Crop": 1, "_id": 0})]

    df = pd.DataFrame({'Field': fields, 'Crop': ""})
    df['Crop'] = df['Crop'].astype(pd.CategoricalDtype(crops))
    edited_df = st.data_editor(df, num_rows="dynamic", use_container_width = True)

    if st.button("Save Changes"):
        differences = edited_df.compare(df)
        changed_ids = differences.index.get_level_values(0).unique()
        print(changed_ids)

        # Step 7: Loop through changed rows and update MongoDB
        for index in changed_ids:
            # Get the field and crop for the changed row
            field_name = edited_df.loc[index, 'Field']
            selected_crop = edited_df.loc[index, 'Crop']

            # Update the document in MongoDB for this field
            result = fields_collection.update_one(
                {"FieldName": field_name, "Farm": selected_farm},  # Match by FieldName and Farm
                {"$set": {"Cropping": selected_crop}}  # Update the Cropping field with the new crop
            )

            if result.modified_count > 0:
                st.success(f"Updated {field_name} with crop {selected_crop}.")
            else:
                st.warning(f"No changes made for {field_name}.")
    



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