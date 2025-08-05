import time
from io import StringIO

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import requests
import streamlit as st

st.set_page_config(
    page_title="Weather Dashboard",
    page_icon="🌤️",
    layout="wide"
)

GITHUB_USERNAME = "FrancisTembo"
GITHUB_REPO = "cuddly-broccoli"
GITHUB_BRANCH = "main"
GITHUB_RAW_BASE_URL = f"https://raw.githubusercontent.com/{GITHUB_USERNAME}/{GITHUB_REPO}/{GITHUB_BRANCH}/weather_data"

CITY_FILES = {
    "Cape Town": "cape_town_weather.csv",
    "Kigali": "kigali_weather.csv",
    "Kampala": "kampala_weather.csv"
}

@st.cache_data(ttl=300)  # Cache data for 5 minutes (300 seconds)
def load_data_from_github(filename: str):
    """
    Downloads and parses a single CSV file from the GitHub repository.
    Returns a DataFrame and an error message if any.
    """
    url = f"{GITHUB_RAW_BASE_URL}/{filename}"
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        csv_content = StringIO(response.text)
        df = pd.read_csv(csv_content, parse_dates=['timestamp'])
        return df, None
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 404:
            return pd.DataFrame(), f"File not found: `{filename}`. It may not have been created yet."
        return pd.DataFrame(), f"HTTP error: {e}"
    except requests.exceptions.RequestException as e:
        return pd.DataFrame(), f"Network error: {e}"
    except pd.errors.EmptyDataError:
        return pd.DataFrame(), f"The file `{filename}` is empty."
    except Exception as e:
        return pd.DataFrame(), f"An unexpected error occurred while parsing `{filename}`: {e}"

@st.cache_data(ttl=300)
def load_all_weather_data():
    """
    Loads and combines weather data from all city CSV files on GitHub.
    """
    with st.spinner("Fetching latest weather data from GitHub..."):
        all_data = []
        errors = []

        for city, filename in CITY_FILES.items():
            df, error = load_data_from_github(filename)
            if error:
                errors.append(f"**{city}:** {error}")
            if not df.empty:
                df['timestamp'] = df['timestamp'].dt.tz_convert('Africa/Johannesburg')
                df['city'] = city
                all_data.append(df)

        if errors:
            st.warning("Some data could not be loaded. The data files may be generating.", icon="⚠️")
            with st.expander("Show Loading Errors"):
                for error in errors:
                    st.error(error)

        if not all_data:
            return pd.DataFrame(columns=['city', 'timestamp', 'temperature', 'humidity'])

        combined_df = pd.concat(all_data, ignore_index=True)
        return combined_df.sort_values(['city', 'timestamp'])


def create_time_series_chart(df: pd.DataFrame, y_value: str, title: str, y_title: str):
    """Creates an enhanced line chart for a given metric."""
    if df.empty:
        return go.Figure().update_layout(
            title=title,
            annotations=[dict(text="No data available for this selection.", showarrow=False)]
        )

    fig = px.line(
        df,
        x='timestamp',
        y=y_value,
        color='city',
        title=title,
        labels={'timestamp': 'Time (SAST)', y_value: y_title},
        markers=True,
        template="plotly_white"
    )
    fig.update_layout(
        hovermode='x unified',
        legend_title_text='City',
        height=450,
        margin=dict(l=40, r=40, t=80, b=40),
        title_font_size=20
    )
    fig.update_traces(marker=dict(size=4), hovertemplate='%{y:.1f}')
    return fig

def create_comparison_bar_chart(df: pd.DataFrame, value_col: str, title: str):
    """Creates a bar chart to compare the latest values across cities."""
    if df.empty:
        return go.Figure().update_layout(title=title, annotations=[dict(text="No data available.", showarrow=False)])

    latest_data = df.loc[df.groupby('city')['timestamp'].idxmax()]
    fig = px.bar(
        latest_data,
        x='city',
        y=value_col,
        color='city',
        title=title,
        labels={'city': 'City', value_col: value_col.capitalize()},
        text_auto='.1f',
        template="plotly_white"
    )
    fig.update_layout(showlegend=False)
    return fig

def display_summary_statistics(df: pd.DataFrame, metric: str):
    """Displays summary statistics (Avg, Max, Min) for a given metric."""
    if df.empty:
        st.info(f"No data to calculate {metric} statistics.")
        return

    st.subheader(f"📊 Summary Statistics for {metric.capitalize()}")
    cols = st.columns(3)
    summary = df.groupby('city')[metric].agg(['mean', 'max', 'min']).reset_index()

    for index, row in summary.iterrows():
        with cols[index % 3]:
            st.metric(
                label=f"📍 {row['city']} Average",
                value=f"{row['mean']:.1f}"
            )
            st.metric(
                label=f"📈 {row['city']} Max",
                value=f"{row['max']:.1f}"
            )
            st.metric(
                label=f"📉 {row['city']} Min",
                value=f"{row['min']:.1f}"
            )
            st.markdown("---")



def main():
    """Main function to run the Streamlit application."""
    st.title("Weather Dashboard")
    st.markdown("An interactive dashboard for monitoring hourly weather trends in key African cities.")

    df = load_all_weather_data()

    if df.empty:
        st.info("Waiting for data. The first data points should appear within an hour after deployment.")
        return

    st.sidebar.header("⚙️ Filters")

    min_date = df['timestamp'].min().date()
    max_date = df['timestamp'].max().date()

    date_range = st.sidebar.date_input(
        "Select Date Range",
        value=(min_date, max_date),
        min_value=min_date,
        max_value=max_date,
        help="Filter the data to a specific time window."
    )

    try:
        start_date, end_date = date_range
        mask = (df['timestamp'].dt.date >= start_date) & (df['timestamp'].dt.date <= end_date)
        filtered_df = df[mask]
    except (ValueError, IndexError):
        st.sidebar.error("Please select a valid date range (start and end date).")
        filtered_df = df # Use unfiltered data if range is invalid

    tab1, tab2, tab3 = st.tabs(["📊 Overview & Comparison", "🌡️ Temperature Analysis", "💧 Humidity Analysis"])

    with tab1:
        st.header("Latest Conditions at a Glance", divider='rainbow')
        if filtered_df.empty:
            st.info("No data available for the selected date range.")
        else:
            col1, col2 = st.columns(2)
            with col1:
                temp_bar_chart = create_comparison_bar_chart(filtered_df, 'temperature', "Latest Temperature Comparison (°C)")
                st.plotly_chart(temp_bar_chart, use_container_width=True)
            with col2:
                humidity_bar_chart = create_comparison_bar_chart(filtered_df, 'humidity', "Latest Humidity Comparison (%)")
                st.plotly_chart(humidity_bar_chart, use_container_width=True)

    with tab2:
        st.header("Temperature Analysis", divider='rainbow')
        temp_chart = create_time_series_chart(
            filtered_df,
            y_value='temperature',
            title='Hourly Temperature Trends (°C)',
            y_title='Temperature (°C)'
        )
        st.plotly_chart(temp_chart, use_container_width=True)
        st.markdown("---")
        display_summary_statistics(filtered_df, 'temperature')

    with tab3:
        st.header("Humidity Analysis", divider='rainbow')
        humidity_chart = create_time_series_chart(
            filtered_df,
            y_value='humidity',
            title='Hourly Humidity Trends (%)',
            y_title='Humidity (%)'
        )
        st.plotly_chart(humidity_chart, use_container_width=True)
        st.markdown("---")
        display_summary_statistics(filtered_df, 'humidity')

    with st.expander("📂 View Raw Data Table"):
        st.dataframe(
            filtered_df.sort_values('timestamp', ascending=False),
            use_container_width=True,
            hide_index=True
        )

    st.markdown("---")
    st.markdown(
        "**Data Source**: OpenWeatherMap API | "
        "**Update Frequency**: Hourly via GitHub Actions"
    )

if __name__ == "__main__":
    main()