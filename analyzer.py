"""
Main analysis module
"""
import configparser
import os
import requests
from geopy.geocoders import Nominatim
from openai import OpenAI
import logging

class SolarAnalyzer:
    def __init__(self):
        self.config = configparser.ConfigParser()
        self.config.read('config.ini')
        self.geolocator = Nominatim(user_agent="solar_analyzer")
        self.openai_client = OpenAI(api_key=self.config['API_KEYS']['OPENAI'])

    def get_location_data(self, lat: float, lon: float) -> dict:
        """Get geographic data from coordinates"""
        try:
            location = self.geolocator.reverse(f"{lat}, {lon}")
            return {
                'country': location.raw.get('address', {}).get('country'),
                'city': location.raw.get('address', {}).get('city'),
                'population': None  # Placeholder for population data
            }
        except Exception as e:
            logging.error(f"Geocoding error: {str(e)}")
            return {}

    def get_solar_stats(self, lat: float, lon: float) -> dict:
        """Fetch solar radiation data from NASA POWER"""
        try:
            url = f"https://power.larc.nasa.gov/api/temporal/annual/point?parameters=ALLSKY_SFC_SW_DWN&community=RE&longitude={lon}&latitude={lat}&format=JSON"
            response = requests.get(url, timeout=10)
            data = response.json()
            return {
                'annual_radiation': data['properties']['parameter']['ALLSKY_SFC_SW_DWN'],
                'units': 'kWh/m²/day'
            }
        except Exception as e:
            logging.error(f"NASA API error: {str(e)}")
            return {}

    def get_country_dev_level(self, country_code: str) -> str:
        """Get country development status"""
        try:
            url = f"http://api.worldbank.org/v2/country/{country_code}?format=json"
            response = requests.get(url, timeout=5)
            return response.json()[1][0]['incomeLevel']['value']
        except:
            return self._ask_ai(f"Development status of {country_code}")

    def estimate_costs(self, country: str) -> dict:
        """Get installation cost estimates"""
        return self._ask_ai(f"Average solar installation costs in {country}")

    def _ask_ai(self, query: str) -> str:
        """Query OpenAI for missing data"""
        try:
            response = self.openai_client.chat.completions.create(
                model="gpt-4",
                messages=[{"role": "user", "content": query}]
            )
            return response.choices[0].message.content
        except Exception as e:
            logging.error(f"AI query failed: {str(e)}")
            return "Unknown"

    def analyze(self, lat: float, lon: float) -> dict:
        """Main analysis pipeline"""
        result = {
            'geographic': self.get_location_data(lat, lon),
            'solar': self.get_solar_stats(lat, lon),
            'economic': {}
        }
        
        if result['geographic'].get('country'):
            result['economic'] = {
                'development_level': self.get_country_dev_level(result['geographic']['country']),
                'cost_estimate': self.estimate_costs(result['geographic']['country'])
            }
            
        return result
