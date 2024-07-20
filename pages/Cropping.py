from pymongo import MongoClient
import certifi
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import streamlit_authenticator as stauth


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
    # Set tabs at top of page
    tab1, tab2, tab3 = st.tabs(["Manage Crops", "Manage Fields", "Settings"])

    # Manage Crops tab
    with tab1:
        st.title("Manage crops")
        # Fetch distinct farms
        farms = fields_collection.distinct("Farm")
        selected_farm = st.radio("Select Farm", farms)

        if selected_farm:
            # Fetch fields for the selected farm
            fields = list(fields_collection.find({"Farm": selected_farm}))

            # Prepare data for the table
            data = []
            for field in fields:
                field_name = field["FieldName"]
                size = field.get("Size", "")
                cropping = field.get("Cropping", {}).get("Crops", [])
                if cropping:
                    latest_crop = cropping[-1]
                    crop = latest_crop.get("Crop", "")
                    dressing = latest_crop.get("Dressing", "")
                    drill_date = latest_crop.get("DrillDate", "")
                    origin = latest_crop.get("Origin", "")
                    quantity = latest_crop.get("Quantity", "")
                    variety = latest_crop.get("Variety", "")
                else:
                    crop = dressing = drill_date = origin = quantity = variety = ""
                data.append({
                    "FieldName": field_name,
                    "Size": size,
                    "Crop": crop,
                    "Dressing": dressing,
                    "DrillDate": drill_date,
                    "Origin": origin,
                    "Quantity": quantity,
                    "Variety": variety
                })

            # Display data in a table
            df = pd.DataFrame(data)
            st.dataframe(df)


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

            fig.update_layout(title_text=f"Crop Distribution for {selected_farm}", font_size=10)
            st.plotly_chart(fig)


            # Dropdown to select a specific field
            field_names = df["FieldName"].tolist()
            selected_field = st.selectbox("Select Field", field_names)

            # Fetch crop names from the Crops collection
            crop_names = crops_collection.distinct("Crop")

            # Input fields for the new crop object
            st.subheader("Add a New Crop")

            col1, col2 = st.columns(2)
            # Column 1
            with col1:
                crop_name = st.selectbox("Crop Name", crop_names)
                quantity = st.text_input("Quantity", "")
                drill_date = st.date_input("Drill Date")

            # Column 2
            with col2:
                origin = st.radio("Seed Source", ["Bought", "Home Saved"], horizontal=True)
                dressing = st.text_input("Dressing", "")
                variety = st.text_input("Variety", "")

            # Button to submit the new crop object
            if st.button("Add Crop"):
                # Define the new crop object
                new_crop = {
                    "Crop": crop_name,
                    "Dressing": dressing,
                    "DrillDate": drill_date,
                    "Origin": origin,
                    "Quantity": quantity,
                    "Variety": variety
                }

                # Update the selected document
                fields_collection.update_one(
                    {"FieldName": selected_field},
                    {"$push": {"Cropping.Crops": new_crop}}
                )

                st.success(f"Crops added successfully to {selected_field}!")

    # Manage Fields tab
    with tab2:
        st.title("Manage Fields")


    with tab3:
        st.title("Settings")

        if st.button("Delete all crops from all fields"):
            # Update all documents to remove the Cropping field
            result = fields_collection.update_many({}, {"$unset": {"Cropping": ""}})

            st.success(f"Deleted {result.modified_count} documents!")
    client.close()

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