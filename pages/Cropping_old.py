
from pymongo import MongoClient
import certifi
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import streamlit_authenticator as stauth
from datetime import datetime
from bson import ObjectId


#Connect to database and initialise collections
uri = st.secrets.mongo.uri
client = MongoClient(uri, tlsCAFile=certifi.where())

# Set databases as variables
db = client.HallFarming
fields_collection = db.Land
crops_collection = db.Crops
dressings_collection = db.Dressings
varieties_collection = db.Varieties
user_db = client.Users
users_collection = user_db.Credentials

def get_crop(field):
    cropping = field.get("Cropping", {}).get("Crops", [])
    if cropping:
        latest_crop = cropping[-1]
        crop = latest_crop.get("Crop", "")
        dressing = latest_crop.get("Dressing", "")
        drill_date = latest_crop.get("DrillDate", "").date() if latest_crop.get("DrillDate", "") else ""
        cut_date = latest_crop.get("CutDate", "").date() if latest_crop.get("CutDate", "") else ""
        home_saved = latest_crop.get("HomeSaved", "")
        quantity = latest_crop.get("Quantity", "")
        variety = latest_crop.get("Variety", "")
        crop_yield = latest_crop.get("Yield", "")
    else:
        crop = dressing = drill_date = cut_date = home_saved = quantity = variety = crop_yield = ""
    
    return {
        "Crop": crop,
        "Dressing": dressing,
        "DrillDate": drill_date,
        "CutDate": cut_date,
        "HomeSaved": home_saved,
        "Quantity": quantity,
        "Variety": variety,
        "Yield": crop_yield
    }

def load_content():
    # Set tabs at top of page
    tab1, tab2, tab3 = st.tabs(["Field Cropping", "Manage Crops & Fields", "Settings"])

    # Manage Crops tab
    with tab1:
        st.title("Manage crops")
        # Fetch distinct farms
        farms = fields_collection.distinct("Farm")
        selected_farm = st.selectbox("Select Farm", farms)

        if selected_farm:
            # Fetch fields for the selected farm
            fields = list(fields_collection.find({"Farm": selected_farm}))

            # Prepare data for the table
            data = []
            for field in fields:
                field_name = field["FieldName"]
                size = field.get("Size", "")
                latest_crop = get_crop(field)
                data.append({
                    "FieldName": field_name,
                    "Size": size,
                    **latest_crop})

            # Display data in a table
            df = pd.DataFrame(data)
            #st.dataframe(df)


            # Prepare data for the Sankey diagram for the selected farm
            total_size = sum([field["Size"] for field in fields])
            crop_sizes = {}
            for field in fields:
                cropping = field.get("Cropping", {}).get("Crops", [])
                if cropping:
                    latest_crop = cropping[-1]
                    crop = latest_crop.get("Crop", "")
                    crop_sizes[crop] = crop_sizes.get(crop, 0) + field["Size"]

            # Create lists for Sankey chart
            labels = [selected_farm] + list(crop_sizes.keys())
            sources = [0] * len(crop_sizes)  # All start from the farm
            targets = list(range(1, len(crop_sizes) + 1))
            values = list(crop_sizes.values())

            # Create a Sankey chart
            fig = go.Figure(data=[go.Sankey(
                node=dict(
                    pad=15,
                    thickness=20,
                    line=dict(color="black", width=0.5),
                    label=labels
                ),
                link=dict(
                    source=sources,
                    target=targets,
                    value=values
                ))])

            tab4, tab5 = st.tabs(["Data View", "Chart View"])
            with tab4:
                st.dataframe(df)

            with tab5:
                fig.update_layout(title_text=f"Crop Distribution for {selected_farm}", font_size=10)
                st.plotly_chart(fig)

            # Dropdown to select a specific field
            field_names = df["FieldName"].tolist()
            selected_field = st.selectbox("Select Field", field_names)

            # Fetch crop data for the selected field
            field = fields_collection.find_one({"FieldName": selected_field})
            latest_crop = get_crop(field)

            # Fetch crop names from the Crops collection
            crop_names = crops_collection.distinct("Crop")
            dressing_names = dressings_collection.distinct("Treatments")

            # Input fields for the new crop object
            st.subheader("Modify Cropping")     

            col1, col2 = st.columns(2)
            # Column 1
            with col1:
                crop_name_mod = st.selectbox("Crop", crop_names)
                quantity = st.number_input("Seed Quantity (kg)", step=5)
                if quantity == 0:
                    quantity = ""
                variety = st.text_input("Variety", "")
                drilled = st.toggle("Drilled")
                if drilled:
                    drill_date = datetime.combine(st.date_input("Drill Date"), datetime.min.time())
                else:
                    drill_date = ""

            # Column 2
            with col2:
                origin = st.radio("Seed Source", ["Bought", "Home Saved"], horizontal=True)
                home_saved = False
                if origin == "Home Saved":
                    home_saved = True
                dressing = st.selectbox("Dressing", dressing_names)
                crop_yield = st.number_input("Yield (ton/ha)", step=5)
                harvested = st.toggle("Harvested")
                if harvested:
                    cut_date = datetime.combine(st.date_input("Cut Date"), datetime.min.time())
                else:
                    cut_date = ""
                
        
            if st.button("Add Crop"):
                # Define the new crop object
                new_crop = {
                    "Crop": crop_name_mod,
                    "Dressing": dressing,
                    "DrillDate": drill_date,
                    "CutDate": cut_date,
                    "HomeSaved": home_saved,
                    "Quantity": quantity,
                    "Variety": variety,
                    "Yield": crop_yield
                }

                # Update the selected document
                fields_collection.update_one(
                    {"FieldName": selected_field},
                    {"$push": {"Cropping.Crops": new_crop}}
                )

                st.success(f"Crop added successfully to {selected_field}!")       

    # Manage Fields tab
    with tab2:
        # Fetch data from MongoDB
        def fetch_data():
            crops = list(crops_collection.find({}))
            return crops

        # Update data in MongoDB
        def update_data(data, ids):
            for index, row in data.iterrows():
                filter = {"_id": ids[index]}
                new_values = {"$set": {"Crop": row["Crop"], "identifier": row["identifier"], "N_Max": row["N_Max"], "P_Max": row["P_Max"]}}
                crops_collection.update_one(filter, new_values)

        # Load data into a DataFrame
        crops = fetch_data()
        df = pd.DataFrame(crops)

        # Keep track of _id values separately
        id_list = df["_id"].apply(str).tolist()
        df = df.drop(columns=["_id"])  # Drop the _id column for display

        st.title("Edit Crop Information")
        st.write("Edit the table below and click 'Save Changes' to update the data in the database.")

        # Display editable table with a unique key
        edited_df = st.data_editor(df, key='data_editor')

        # Button to save changes
        if st.button("Save Changes"):
            # Ensure the order of ids matches the edited_df
            update_data(edited_df, [ObjectId(id_str) for id_str in id_list])
            st.success("Data updated successfully!")


    with tab3:
        st.title("Settings")

        if st.button("Delete all crops from all fields"):
            # Update all documents to remove the Cropping field
            result = fields_collection.update_many({}, {"$unset": {"Cropping": ""}})
            st.success(f"Deleted {result.modified_count} documents!")

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
