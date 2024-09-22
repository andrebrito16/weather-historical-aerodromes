import os
import pandas as pd
import numpy as np
import streamlit as st
import matplotlib.pyplot as plt
from windrose import WindroseAxes
from io import BytesIO

# Function to process and combine all uploaded CSV files
def process_csv_data(uploaded_files):
    # List to hold all individual dataframes
    all_dataframes = []

    # Iterate through each uploaded file and process it
    for file in uploaded_files:
        # Read the CSV file without combining dates
        df = pd.read_csv(file, sep=';')

        # Rename columns
        df.columns = ['Data', 'Hora (UTC)', 'temp', 'humidity', 'pressure', 'wind_speed', 'wind_dir', 'cloudiness', 'insolation', 'max_temp', 'min_temp', 'rainfall']

        # Combine 'Data' and 'Hora (UTC)' into a single 'datetime' column after reading
        df['datetime'] = pd.to_datetime(df['Data'] + ' ' + df['Hora (UTC)'].astype(str).str.zfill(4), format='%d/%m/%Y %H%M')

        # Convert wind speed from m/s to knots and ensure it's numeric
        df['wind_speed'] = pd.to_numeric(df['wind_speed'].str.replace(',', '.'), errors='coerce') * 1.94384

        # Ensure wind direction is numeric
        df['wind_dir'] = pd.to_numeric(df['wind_dir'].str.replace(',', '.'), errors='coerce')

        # Drop rows with NaN values in wind speed or direction
        df = df.dropna(subset=['wind_speed', 'wind_dir'])

        # Append the dataframe to the list of dataframes
        all_dataframes.append(df)

    # Concatenate all dataframes into a single one
    combined_df = pd.concat(all_dataframes, ignore_index=True)

    # Drop any remaining NaNs, if they exist
    combined_df = combined_df[combined_df['wind_speed'].notna() & combined_df['wind_dir'].notna()]

    return combined_df

# Function to create a wind rose plot
def create_wind_rose(wind_speed, wind_dir, title, ax=None):
    if ax is None:
        ax = WindroseAxes.from_ax()

    # Clean data for plotting (ensure no NaN values)
    wind_speed_clean = wind_speed.dropna()
    wind_dir_clean = wind_dir.dropna()

    # Create windrose plot
    ax.bar(wind_dir_clean, wind_speed_clean, opening=0.8, edgecolor='white')
    ax.set_legend(title="Wind speed (knots)")
    ax.set_title(title, fontsize=10)

# Function to plot all wind roses for different speed ranges
def plot_wind_roses(data):
    fig = plt.figure(figsize=(20, 15))

    speed_ranges = [
        (1, 5, "Velocidade: 1-5 kt"),
        (6, 10, "Velocidade: 6-10 kt"),
        (11, 15, "Velocidade: 11-15 kt"),
        (16, 20, "Velocidade: 16-20 kt"),
        (21, 30, "Velocidade: 21-30 kt"),
        (31, np.inf, "Velocidade: > 30 kt")
    ]

    for i, (min_speed, max_speed, title) in enumerate(speed_ranges, 1):
        mask = (data['wind_speed'] >= min_speed) & (data['wind_speed'] < max_speed)

        # Skip if no data for the speed range
        if mask.sum() == 0:
            continue

        ax = fig.add_subplot(2, 3, i, projection='windrose')
        create_wind_rose(data.loc[mask, 'wind_speed'], data.loc[mask, 'wind_dir'], title, ax)

    plt.tight_layout()
    return fig

# Function to convert Matplotlib figure to a downloadable PNG
def fig_to_png(fig):
    buf = BytesIO()
    fig.savefig(buf, format="png", dpi=300, bbox_inches='tight')
    buf.seek(0)
    return buf

# Streamlit app layout and logic
st.title("Wind Rose Plot Generator")

# Upload CSV files
uploaded_files = st.file_uploader("Upload CSV Files", accept_multiple_files=True, type=["csv"])

if uploaded_files:
    st.write(f"Uploaded {len(uploaded_files)} file(s).")

    if st.button("Generate Wind Rose Plot"):
        # Process the uploaded files
        combined_data = process_csv_data(uploaded_files)

        # Generate wind roses
        fig = plot_wind_roses(combined_data)

        # Display the plot in the Streamlit app
        st.pyplot(fig)

        # Provide a download button for the plot
        png_data = fig_to_png(fig)
        st.download_button(
            label="Download Wind Rose Plot",
            data=png_data,
            file_name="wind_roses.png",
            mime="image/png"
        )