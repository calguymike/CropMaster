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

# Function to fetch the latest cropping information for a selected farm
def get_latest_cropping_for_farm(selected_farm):
    global HF
    # Query MongoDB for fields in the selected farm
    fields = HF["fields_collection"].find({"Farm": selected_farm})
    
    # Prepare a list to hold the data
    data = []
    
    # Loop through each field
    for field in fields:
        field_name = field.get("FieldName", "Unknown Field")
        cropping_info = field.get("Cropping", {}).get("Crops", [])
        
        if cropping_info:
            # Find the latest cropping info by DrillDate
            latest_crop = max(cropping_info, key=lambda crop: crop.get("DrillDate", datetime.datetime.min))
            
            # Prepare the data row with field name and cropping information
            row = {
                "FieldName": field_name,
                "Crop": latest_crop.get("Crop", "Unknown"),
                "Dressing": latest_crop.get("Dressing", ""),
                "DrillDate": latest_crop.get("DrillDate", ""),
                "CutDate": latest_crop.get("CutDate", ""),
                "HomeSaved": latest_crop.get("HomeSaved", False),
                "Quantity": latest_crop.get("Quantity", 0),
                "Variety": latest_crop.get("Variety", ""),
                "Yield": latest_crop.get("Yield", 0)
            }
            data.append(row)
    
    # Convert the data to a pandas DataFrame
    df = pd.DataFrame(data)
    df.set_index("FieldName", inplace=True)  # Set FieldName as index for Y-axis
    return df


def update_cropping_in_db(selected_farm, updated_df):
    global HF
    # Loop through the DataFrame and update the corresponding field in the database
    for field_name, row in updated_df.iterrows():
        # Find the field in the database
        field = HF["fields_collection"].find_one({"Farm": selected_farm, "FieldName": field_name})
        
        if field:
            # Extract the cropping information
            cropping_info = field.get("Cropping", {}).get("Crops", [])
            
            if cropping_info:
                # Find the latest cropping entry by DrillDate
                latest_crop = max(cropping_info, key=lambda crop: crop.get("DrillDate", datetime.datetime.min))
                
                # Update the latest crop with values from the DataFrame
                latest_crop["Crop"] = row["Crop"]
                latest_crop["Dressing"] = row["Dressing"]
                latest_crop["DrillDate"] = row["DrillDate"]
                latest_crop["CutDate"] = row["CutDate"]
                latest_crop["HomeSaved"] = row["HomeSaved"]
                latest_crop["Quantity"] = row["Quantity"]
                latest_crop["Variety"] = row["Variety"]
                latest_crop["Yield"] = row["Yield"]
                
                # Write the updated cropping information back to the database
                HF["fields_collection"].update_one(
                    {"Farm": selected_farm, "FieldName": field_name},
                    {"$set": {"Cropping.Crops": cropping_info}}
                )
    

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
            cropping = get_crop(selected_field, selected_farm)


    with tab2:
        st.title("Manage Crops")
        # Step 1: Select a farm
        farms = HF_loc["fields_collection"].distinct("Farm")
        farm_name = st.selectbox("Select a Farm", farms)  # Replace with actual farm names
        
        if farm_name:
            # Step 2: Fetch and display the latest cropping information for the selected farm
            df = get_latest_cropping_for_farm(farm_name)
            edited_df = st.dataframe(df)
            
            # Step 3: Allow the user to update cropping information and write it back to the database
            if st.button("Update Cropping Information"):
                update_cropping_in_db(farm_name, edited_df)
                st.success("Cropping information updated successfully!")

    with tab3:
        st.title("Manage Fields")

    with tab4:
        st.title("Settings")
    

initialize_db()