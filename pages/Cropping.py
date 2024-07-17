from pymongo import MongoClient
import certifi
import streamlit as st
import pandas as pd
import plotly.graph_objects as go

#Connect to database and initialise collections
uri = st.secrets.mongo.uri
client = MongoClient(uri, tlsCAFile=certifi.where())
db = client.HallFarming
fields_collection = db.Land
crops_collection = db.Crops

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
            drill_date = st.text_input("Drill Date", "")

        # Column 2
        with col2:
            origin = st.text_input("Origin", "")
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

client.close()