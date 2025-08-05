import csv
import os
from datetime import datetime, timedelta, timezone
from typing import Any

import pandas as pd
import requests
from dotenv import load_dotenv

DATA_DIR = "weather_data"
BASE_GEOCODING_URL = "http://api.openweathermap.org/geo/1.0/direct"
BASE_WEATHER_URL = "https://api.openweathermap.org/data/3.0/onecall/timemachine"

CITIES = {
    "Cape Town": {"query": "Cape Town,ZA", "filename": "cape_town_weather.csv"},
    "Kigali": {"query": "Kigali,RW", "filename": "kigali_weather.csv"},
    "Kampala": {"query": "Kampala,UG", "filename": "kampala_weather.csv"},
}


class WeatherFetcher:
    """
    Class to fetch and store historical weather data for specified cities using OpenWeatherMap API.
    This class handles fetching city coordinates, historical weather data, and saving it to CSV files.
    It also checks for missing data and can fetch the latest complete hour of weather data.
    """

    def __init__(self):
        self.api_key: str = os.getenv("OPEN_WEATHER_API_KEY", "")
        self.base_geocoding_url = BASE_GEOCODING_URL
        self.base_weather_url = BASE_WEATHER_URL
        self.data_dir = DATA_DIR

    def get_city_coordinates(self, city_query: str) -> tuple[float, float]:
        """Get latitude and longitude for a given city query using OpenWeatherMap's Geocoding API.

        Parameters
        ----------
        city_query : str
            The city name and country code (e.g., "Cape Town,ZA").

        Returns
        -------
        tuple[float, float]
            Latitude and longitude of the city"""

        params = {"q": city_query, "limit": 1, "appid": self.api_key}

        response = requests.get(self.base_geocoding_url, params=params)  # type: ignore
        response.raise_for_status()

        data = response.json()
        if not data:
            raise ValueError(f"City not found: {city_query}")

        return data[0]["lat"], data[0]["lon"]

    def get_historical_weather(
        self, lat: float, lon: float, timestamp: int
    ) -> dict[str, Any]:
        """Get historical weather data for specific coordinates and timestamp

        Parameters
        ----------
        lat : float
            Latitude of the location.
        lon : float
            Longitude of the location.
        timestamp : int
            Unix timestamp for the desired hour.

        Returns
        -------
        dict[str, Any]
            Weather data including temperature and humidity.
        """
        params: dict[str, Any] = {
            "lat": lat,
            "lon": lon,
            "dt": int(timestamp),
            "appid": self.api_key,
            "units": "metric",
        }

        response = requests.get(self.base_weather_url, params=params)
        response.raise_for_status()

        return response.json()

    def get_csv_path(self, city_name: str) -> str:
        """Get the full path to the CSV file for a city"""
        filename = CITIES[city_name]["filename"]
        return os.path.join(self.data_dir, filename)

    def load_existing_data(self, city_name: str) -> pd.DataFrame:
        """Load existing weather data for a specific city"""
        csv_path = self.get_csv_path(city_name)

        if os.path.exists(csv_path):
            try:
                df = pd.read_csv(csv_path)
                df["timestamp"] = pd.to_datetime(df["timestamp"])
                return df
            except Exception as e:
                print(f"Error loading existing data for {city_name}: {e}")
                return pd.DataFrame(columns=["timestamp", "temperature", "humidity"])
        return pd.DataFrame(columns=["timestamp", "temperature", "humidity"])

    def data_exists(self, existing_df: pd.DataFrame, timestamp: int | datetime) -> bool:
        """Check if data already exists for a specific timestamp"""
        if existing_df.empty:
            return False

        if isinstance(timestamp, int):
            timestamp = datetime.fromtimestamp(timestamp, tz=timezone.utc)

        matches = existing_df[existing_df["timestamp"] == timestamp]
        return len(matches) > 0

    def extract_hourly_data(self, weather_data, target_timestamp):
        """Extract relevant hourly data from API response"""
        if "data" in weather_data and len(weather_data["data"]) > 0:
            hour_data = weather_data["data"][0]

            return {
                "timestamp": datetime.fromtimestamp(hour_data["dt"], tz=timezone.utc),
                "temperature": hour_data["temp"],
                "humidity": hour_data["humidity"],
            }
        return None

    def save_to_csv(self, city_name: str, data_records: list[dict[str, Any]]):
        """Save weather data to city-specific CSV file"""
        if not data_records:
            return

        csv_path = self.get_csv_path(city_name)
        file_exists = os.path.isfile(csv_path)

        with open(csv_path, "a", newline="") as csvfile:
            fieldnames = ["timestamp", "temperature", "humidity"]
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)

            if not file_exists:
                writer.writeheader()

            for record in data_records:
                writer.writerow(
                    {
                        "timestamp": record["timestamp"].isoformat(),
                        "temperature": record["temperature"],
                        "humidity": record["humidity"],
                    }
                )

    def get_missing_hours(self, city_name: str, hours_back: int = 24) -> list[datetime]:
        """Identify missing hours for a specific city"""
        existing_df = self.load_existing_data(city_name)
        now = datetime.now(timezone.utc)
        missing_hours = []

        for i in range(1, hours_back + 1):  # Start from 1 hour ago
            target_hour = (now - timedelta(hours=i)).replace(
                minute=0, second=0, microsecond=0
            )

            if not self.data_exists(existing_df, target_hour):
                missing_hours.append(target_hour)

        return missing_hours

    def fetch_city_data(self, city_name: str, target_times: list[datetime]):
        """Fetch weather data for a specific city and list of timestamps"""
        if not target_times:
            print(f"No missing data for {city_name}")
            return

        city_info = CITIES[city_name]
        new_records = []

        try:
            # Get coordinates
            print(f"Getting coordinates for {city_name}...")
            lat, lon = self.get_city_coordinates(city_info["query"])

            for target_time in target_times:
                try:
                    print(
                        f"Fetching {city_name} data for {target_time.strftime('%Y-%m-%d %H:%M UTC')}"
                    )

                    weather_data = self.get_historical_weather(
                        lat, lon, int(target_time.timestamp())
                    )
                    record = self.extract_hourly_data(
                        weather_data, int(target_time.timestamp())
                    )

                    if record:
                        new_records.append(record)
                        print(f"✓ {record['temperature']:.1f}°C, {record['humidity']}%")
                except Exception as e:
                    print(f"✗ Error fetching {city_name} at {target_time}: {e}")
                    continue

            if new_records:
                self.save_to_csv(city_name, new_records)
                print(f"Saved {len(new_records)} records for {city_name}\n")

        except Exception as e:
            print(f"✗ Error processing {city_name}: {e}")

    def fetch_missing_data(self, max_hours_back: int = 24):
        """Fetch missing weather data for all cities"""
        print(f"Checking for missing data in the last {max_hours_back} hours...\n")

        for city_name in CITIES.keys():
            missing_hours = self.get_missing_hours(city_name, max_hours_back)
            print(f"{city_name}: {len(missing_hours)} missing hours")

            if missing_hours:
                self.fetch_city_data(city_name, missing_hours)

    def fetch_latest_hour(self):
        """Fetch only the latest complete hour for all cities"""
        now = datetime.now(timezone.utc)
        latest_hour = (now - timedelta(hours=1)).replace(
            minute=0, second=0, microsecond=0
        )

        print(f"Fetching data for {latest_hour.strftime('%Y-%m-%d %H:%M UTC')}\n")

        for city_name in CITIES.keys():
            existing_df = self.load_existing_data(city_name)

            if self.data_exists(existing_df, latest_hour):
                print(f"✓ {city_name}: Data already exists")
                continue

            print(f"Fetching latest data for {city_name}...")
            self.fetch_city_data(city_name, [latest_hour])


if __name__ == "__main__":

    load_dotenv()

    os.makedirs(DATA_DIR, exist_ok=True)

    fetcher = WeatherFetcher()
    fetcher.fetch_missing_data(max_hours_back=24)
