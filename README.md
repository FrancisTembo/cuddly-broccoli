# Weather Dashboard

This project is a data pipeline and visualisation dashboard that fetches, stores, and displays hourly weather data for Cape Town, Kigali, and Kampala.

The data pipeline runs on a schedule using GitHub Actions, retrieving hourly temperature and humidity data from the OpenWeatherMap API. The Streamlit application then reads this data from the repository to provide an interactive dashboard.

## Live Dashboard

A live version of the dashboard is hosted on Streamlit Community Cloud.

**Dashboard URL**: https://cuddly-broccoli.streamlit.app/

## Architecture

The project is composed of two main components that operate independently:

1.  **Data Fetching Pipeline**: A Python script (`weather_fetcher.py`) is executed hourly by a GitHub Actions workflow (`.github/workflows/fetch_weather.yml`). This script fetches the latest weather data for the target cities from the OpenWeatherMap API, processes it, and commits the updated data as CSV files to the `weather_data/` directory in this repository.
2.  **Streamlit Dashboard**: The dashboard (`app.py`) is a standalone Streamlit application. When a user visits the public URL, the app loads the latest weather data directly from the CSV files stored in the public GitHub repository. 

## Setup and Installation

TO set up your own version of this dashboard, you will need to fork this repository and configure it with your own credentials.

### 1. Fork the Repository

First, create a fork of this repository to your own GitHub account. This is necessary because the GitHub Action will commit data to the repository, and the Streamlit app will read data from it.

### 2. GitHub Configuration

#### A. Set up Repository Secret

THe data fetching script requires an API key from OpenWeatherMap. This should be stored as a secret in your forked GitHub repository.

1.  Sign up for a free account on [OpenWeatherMap](https://openweathermap.org/api) and get an API key.
2.  In your forked GitHub repository, go to **Settings** > **Secrets and variables** > **Actions**.
3.  Click **New repository secret**.
4.  Set the **Name** to `OPEN_WEATHER_API_KEY`.
5.  Paste your OpenWeatherMap API key into the **Value** field.
6.  Click **Add secret**.

#### B. Update `app.py`

The Streamlit app needs to know your GitHub username and repository name to fetch the data files.

1.  Open the `app.py` file in your forked repository.
2.  Update the `GITHUB_USERNAME` and `GITHUB_REPO` variables with your details:

```python
GITHUB_USERNAME = "your-github-username"
GITHUB_REPO = "your-forked-repo-name"
```

#### C. Grant Write Permissions to GitHub Action
For the GitHub Action to commit the fetched weather data back to your repository, it needs write permissions.

1. In your forked repository, navigate to Settings.
2. In the left sidebar, under "Code and automation," click Actions, then select General.
3. Scroll down to the Workflow permissions section.
4. Select the Read and write permissions option.
5. Click Saved.

### 3. Running Locally (Optional)

You can also run the project on your local machine for testing.

#### A. Clone Your Forked Repository

```bash
git clone https://github.com/your-github-username/your-forked-repo-name.git
cd your-forked-repo-name
```

#### B. Create a Virtual Environment

```bash
python -m venv venv
source venv/bin/activate
```

#### C. Install Dependencies

```bash
pip install -r requirements.txt
```

#### D. Create a `.env` file for Local API Key

For local testing, the script can load the API key from a `.env` file.

1.  Create a file named `.env` in the root of your project.
2.  Add your API key to it:

```
OPEN_WEATHER_API_KEY="your_api_key_here"
```
**Note**: The `.gitignore` file is configured to ignore `.env`, so this file will not be committed to your repository.

#### E. Run the Fetcher and Dashboard

First, run the fetcher to get initial data, push the data to your github repository, then launch the Streamlit app.

```bash
# Run the data fetcher
python weather_fetcher.py

git add . && git commit -m "Your commit message here"

# Run the dashboard
streamlit run app.py
```

## Data Fetching and Scheduling

The weather data retrieval is automated using GitHub Actions.

*   **Script**: `weather_fetcher.py`
*   **Workflow**: `.github/workflows/fetch_weather.yml`

The workflow is configured to run on a schedule (e.g., hourly). It executes the `weather_fetcher.py` script, which performs the following actions:
1.  For each target city (Cape Town, Kigali, Kampala), it checks if data for the most recent complete hour is missing.
2.  It uses the OpenWeatherMap Geocoding API to get the coordinates for each city.
3.  It calls the One Call API 3.0 `/timemachine` endpoint to fetch historical data.
4.  It extracts the temperature and humidity for the required hour.
5.  The new data is appended to the corresponding city's CSV file in the `weather_data/` directory.
6.  The GitHub Actions workflow then commits and pushes the updated CSV files back to the repository.

To enable the workflow, go to the **Actions** tab in your forked repository, find the "Fetch Weather Data" workflow, and enable it. THe workflow can also be manually configured. 

***NOTE: The Fetcher is configured to fetch data at the 10th minute of every hour - this is to allow data to reach the OpenWeatherMap API before it is pulled by the action.***

## Data Source

The weather data is stored in individual CSV files for each city within the `weather_data/` directory.

**Schema**:
*   `timestamp`: The UTC timestamp of the weather reading.
*   `temperature`: The temperature in Celsius.
*   `humidity`: The relative humidity as a percentage.

## Sample Outputs

The Streamlit dashboard provides several views of the weather data:

*   **Overview Tab**: Displays bar charts comparing the latest recorded temperature and humidity across all cities.
*   **Temperature Analysis Tab**: Features a line chart showing hourly temperature trends for all cities. It also includes summary statistics (average, max, min) for temperature for each city.
*   **Humidity Analysis Tab**: Features a line chart for hourly humidity trends and corresponding summary statistics.
*   **Raw Data Table**: An expandable section that shows the complete, filtered dataset in a table format.

***NOTE: The data is retrieved from the weather API in UTC and displayed in SAST. This is to avoid data looking three hours behind as opposed to just one.***