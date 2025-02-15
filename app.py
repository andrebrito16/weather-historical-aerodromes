import os
import pandas as pd
import numpy as np
import streamlit as st
import matplotlib.pyplot as plt
from windrose import WindroseAxes
from io import BytesIO

# Constants for wind speed conversions
WIND_SPEED_UNITS = {
    "knots": {"factor": 1.94384, "label": "knots"},
    "m/s": {"factor": 1.0, "label": "m/s"},
    "km/h": {"factor": 3.6, "label": "km/h"}
}

# Function to process and combine all uploaded CSV files
def process_csv_data(uploaded_files, output_unit="knots"):
    # List to hold all individual dataframes
    all_dataframes = []
    files_without_data = []

    conversion_factor = WIND_SPEED_UNITS[output_unit]["factor"]

    # Iterate through each uploaded file and process it
    for file in uploaded_files:
        # Read the CSV file without combining dates
        df = pd.read_csv(file, sep=';', decimal=',')

        # Rename columns
        df.columns = ['Data', 'Hora (UTC)', 'temp', 'humidity', 'pressure', 'wind_speed', 'wind_dir', 'cloudiness', 'insolation', 'max_temp', 'min_temp', 'rainfall']

        # Combine 'Data' and 'Hora (UTC)' into a single 'datetime' column after reading
        df['datetime'] = pd.to_datetime(df['Data'] + ' ' + df['Hora (UTC)'].astype(str).str.zfill(4), format='%d/%m/%Y %H%M')

        # Check for missing wind data
        no_wind_speed_data = df['wind_speed'].isnull().sum() == len(df)
        no_wind_dir_data = df['wind_dir'].isnull().sum() == len(df)

        if no_wind_speed_data or no_wind_dir_data:
            files_without_data.append(file.name)
            continue

        # Convert wind speed from m/s to selected unit
        df['wind_speed'] = df['wind_speed'] * conversion_factor

        # Drop rows with NaN values in wind speed or direction
        df = df.dropna(subset=['wind_speed', 'wind_dir'])

        # Append the dataframe to the list of dataframes
        all_dataframes.append(df)

    # Concatenate all dataframes into a single one
    if len(all_dataframes) == 0:
        return None, files_without_data
    combined_df = pd.concat(all_dataframes, ignore_index=True)

    # Drop any remaining NaNs, if they exist
    combined_df = combined_df.dropna(subset=['wind_speed', 'wind_dir'])

    return combined_df, files_without_data

# Function to create a wind rose plot
def create_wind_rose(wind_speed, wind_dir, title, output_unit, ax=None):
    if ax is None:
        ax = WindroseAxes.from_ax()

    # Clean data for plotting (ensure no NaN values)
    wind_speed_clean = wind_speed.dropna()
    wind_dir_clean = wind_dir.dropna()

    # Create windrose plot
    ax.bar(wind_dir_clean, wind_speed_clean, opening=0.8, edgecolor='white')
    # Move legend to upper right corner with more lateral padding
    ax.set_legend(title=f"Velocidade do vento ({WIND_SPEED_UNITS[output_unit]['label']})", bbox_to_anchor=(1.3, 1.1), loc='upper right')
    ax.set_title(title, fontsize=10, pad=20)

# Function to create combined wind roses (all bins in one figure)
def plot_combined_wind_roses(data, output_unit):
    # Adjust figure size to better fit corner legends
    fig = plt.figure(figsize=(22, 15))

    # Adjust speed ranges based on selected unit
    if output_unit == "knots":
        speed_ranges = [
            (1, 5, "Velocidade: 1-5 kt"),
            (6, 10, "Velocidade: 6-10 kt"),
            (11, 15, "Velocidade: 11-15 kt"),
            (16, 20, "Velocidade: 16-20 kt"),
            (21, 30, "Velocidade: 21-30 kt"),
            (31, np.inf, "Velocidade: > 30 kt")
        ]
    elif output_unit == "m/s":
        speed_ranges = [
            (0.5, 2.5, "Velocidade: 0.5-2.5 m/s"),
            (2.6, 5, "Velocidade: 2.6-5 m/s"),
            (5.1, 7.5, "Velocidade: 5.1-7.5 m/s"),
            (7.6, 10, "Velocidade: 7.6-10 m/s"),
            (10.1, 15, "Velocidade: 10.1-15 m/s"),
            (15.1, np.inf, "Velocidade: > 15 m/s")
        ]
    else:  # km/h
        speed_ranges = [
            (2, 9, "Velocidade: 2-9 km/h"),
            (10, 18, "Velocidade: 10-18 km/h"),
            (19, 27, "Velocidade: 19-27 km/h"),
            (28, 36, "Velocidade: 28-36 km/h"),
            (37, 54, "Velocidade: 37-54 km/h"),
            (55, np.inf, "Velocidade: > 54 km/h")
        ]

    for i, (min_speed, max_speed, title) in enumerate(speed_ranges, 1):
        mask = (data['wind_speed'] >= min_speed) & (data['wind_speed'] < max_speed)

        # Skip if no data for the speed range
        if mask.sum() == 0:
            continue

        ax = fig.add_subplot(2, 3, i, projection='windrose')
        create_wind_rose(data.loc[mask, 'wind_speed'], data.loc[mask, 'wind_dir'], title, output_unit, ax)

    # Adjust layout to prevent legend overlap
    plt.tight_layout(rect=[0, 0, 0.95, 0.95])
    return fig

# Function to plot a single wind rose for a given speed range
def plot_single_wind_rose(data, min_speed, max_speed, title, output_unit):
    # Adjust figure size for corner legend
    fig = plt.figure(figsize=(8, 8))
    mask = (data['wind_speed'] >= min_speed) & (data['wind_speed'] < max_speed)
    if mask.sum() == 0:  # Skip if no data in the range
        return None
    ax = fig.add_subplot(1, 1, 1, projection='windrose')
    create_wind_rose(data.loc[mask, 'wind_speed'], data.loc[mask, 'wind_dir'], title, output_unit, ax)
    # Adjust layout to prevent legend overlap
    plt.tight_layout(rect=[0, 0, 0.95, 0.95])
    return fig

# Function to convert Matplotlib figure to a downloadable PNG
def fig_to_png(fig):
    buf = BytesIO()
    fig.savefig(buf, format="png", dpi=300, bbox_inches='tight')
    buf.seek(0)
    return buf

# Streamlit app layout and logic
st.set_page_config(
    page_title="Wind Rose Generator - Meteorological Data",
    page_icon="🌪️",
    layout="wide"
)

# Title and description
st.title("🌪️ Wind Rose Plot Generator")
st.markdown("""
### Análise de Dados Meteorológicos
Gere rosa dos ventos a partir de dados meteorológicos. Faça upload de arquivos CSV contendo dados de velocidade e direção do vento.
""")

# Add a divider for better visual organization
st.divider()

# Add unit selection dropdown
output_unit = st.selectbox(
    "Select Wind Speed Unit",
    options=list(WIND_SPEED_UNITS.keys()),
    format_func=lambda x: WIND_SPEED_UNITS[x]["label"].upper(),
    index=0  # Default to knots
)

# Upload CSV files
uploaded_files = st.file_uploader("Upload CSV Files", accept_multiple_files=True, type=["csv"])

if uploaded_files:
    st.write(f"Uploaded {len(uploaded_files)} file(s).")

    if st.button("Generate Wind Rose Plots"):
        # Process the uploaded files with selected unit
        combined_data, invalid_files = process_csv_data(uploaded_files, output_unit)

        if len(invalid_files) == len(uploaded_files):
            st.write("No valid data found in the uploaded files.")
            st.stop()

        if len(invalid_files) > 0:
            st.warning(f"Data not found in the following files: {', '.join(invalid_files)}")
        
        # Generate the combined wind rose plot (all bins in one figure)
        st.subheader("Combined Wind Rose Plot")
        combined_fig = plot_combined_wind_roses(combined_data, output_unit)
        st.pyplot(combined_fig)

        # Provide a download button for the combined plot
        combined_png_data = fig_to_png(combined_fig)
        st.download_button(
            label="Download Combined Wind Rose",
            data=combined_png_data,
            file_name=f"combined_wind_rose_{output_unit}.png",
            mime="image/png"
        )

        # Get appropriate speed ranges based on selected unit
        if output_unit == "knots":
            speed_ranges = [
                (1, 5, "Velocidade: 1-5 kt"),
                (6, 10, "Velocidade: 6-10 kt"),
                (11, 15, "Velocidade: 11-15 kt"),
                (16, 20, "Velocidade: 16-20 kt"),
                (21, 30, "Velocidade: 21-30 kt"),
                (31, np.inf, "Velocidade: > 30 kt")
            ]
        elif output_unit == "m/s":
            speed_ranges = [
                (0.5, 2.5, "Velocidade: 0.5-2.5 m/s"),
                (2.6, 5, "Velocidade: 2.6-5 m/s"),
                (5.1, 7.5, "Velocidade: 5.1-7.5 m/s"),
                (7.6, 10, "Velocidade: 7.6-10 m/s"),
                (10.1, 15, "Velocidade: 10.1-15 m/s"),
                (15.1, np.inf, "Velocidade: > 15 m/s")
            ]
        else:  # km/h
            speed_ranges = [
                (2, 9, "Velocidade: 2-9 km/h"),
                (10, 18, "Velocidade: 10-18 km/h"),
                (19, 27, "Velocidade: 19-27 km/h"),
                (28, 36, "Velocidade: 28-36 km/h"),
                (37, 54, "Velocidade: 37-54 km/h"),
                (55, np.inf, "Velocidade: > 54 km/h")
            ]

        # Display wind roses for each speed range and provide download buttons
        for min_speed, max_speed, title in speed_ranges:
            st.subheader(title)
            fig = plot_single_wind_rose(combined_data, min_speed, max_speed, title, output_unit)
            if fig:
                st.pyplot(fig)

                # Provide download button for each plot
                png_data = fig_to_png(fig)
                st.download_button(
                    label=f"Download {title} Wind Rose",
                    data=png_data,
                    file_name=f"{title.replace(' ', '_').replace(':', '')}_{output_unit}.png",
                    mime="image/png"
                )
            else:
                st.write("No data available for this speed range.")