# WeatherOnWay - Route Weather Forecast App

## Connection Timeout Fix

The application was experiencing connection timeout issues with the error: `('Connection aborted.', RemoteDisconnected('Remote end closed connection without response'))`. The following changes were made to fix this issue:

1. **Added Timeout Parameters**:
   - Set explicit timeout values (10 seconds) for all API requests to prevent indefinite waiting
   - Applied to Google Maps Directions API, Geocoding API, and OpenWeatherMap API calls

2. **Implemented Retry Logic**:
   - Added retry mechanism with exponential backoff for all API requests
   - Set maximum retry attempts to 3 for each API call
   - Implemented progressive waiting periods between retries (1s, 2s, 4s)

3. **Enhanced Error Handling**:
   - Added specific exception handling for connection and timeout errors
   - Provided graceful fallbacks for failed API calls
   - For geocoding: returns coordinates if place name can't be retrieved
   - For weather: returns "Forecast Unavailable" if weather data can't be fetched

These changes make the application more robust against network issues and temporary API service disruptions.

## Usage

1. Start the server: `python manage.py runserver`
2. Access the application at: http://127.0.0.1:8000/
3. Enter origin, destination, and departure time to get weather forecasts along your route