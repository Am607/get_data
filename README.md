# MarineTraffic Ship Data Scraper

This project provides tools to extract ship details from MarineTraffic and integrate them into a Django application.

## Features

- Extract ship data including MMSI, name, position, speed, course, and more
- Django model and API integration
- Enhanced anti-detection measures
- Comprehensive error handling
- Management commands for batch processing

## Required Ship Data Fields

The scraper extracts the following fields:
- `provider` - Data provider (MarineTraffic)
- `mmsi` - Maritime Mobile Service Identity
- `name` - Ship name
- `callsign` - Radio call sign
- `type` - Vessel type
- `lat` - Latitude
- `lon` - Longitude
- `speed` - Speed over ground
- `course` - Course over ground
- `heading` - Ship heading
- `draught` - Current draught
- `nav_status` - Navigation status
- `destination` - Destination port
- `timestamp` - Last position timestamp
- `imo` - International Maritime Organization number
- `comparison_id` - Internal comparison ID
- `data_source` - Source of the data

## Installation

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. For Django integration, add to your `INSTALLED_APPS`:
```python
INSTALLED_APPS = [
    # ... your other apps
    'your_app_name',  # where you put the ship model
]
```

## Usage

### Standalone Scraper

```python
from marine_traffic_scraper import get_ship_data

# Get ship data by MMSI
mmsi = "677350000"
ship_data = get_ship_data(mmsi)
print(ship_data)
```

### Enhanced Scraper (Better Anti-Detection)

```python
from enhanced_scraper import get_ship_data

# Get ship data with enhanced anti-detection
mmsi = "677350000"
ship_data = get_ship_data(mmsi)
print(ship_data)
```

### Django Integration

1. **Add the model to your Django app:**
```python
# Copy the Ship model from django_integration.py to your models.py
```

2. **Run migrations:**
```bash
python manage.py makemigrations
python manage.py migrate
```

3. **Add URLs to your project:**
```python
# urls.py
from django.urls import path, include

urlpatterns = [
    # ... your other URLs
    path('ships/', include('your_app.urls')),
]
```

4. **Use the API endpoints:**

**GET ship data from database:**
```bash
curl http://localhost:8000/ships/api/ships/677350000/
```

**POST to fetch and store ship data:**
```bash
curl -X POST http://localhost:8000/ships/api/ships/ \
  -H "Content-Type: application/json" \
  -d '{"mmsi": "677350000"}'
```

### Management Command

```bash
# Scrape a single ship
python manage.py scrape_ship 677350000

# Force update existing ship
python manage.py scrape_ship 677350000 --force
```

## API Response Format

```json
{
  "success": true,
  "data": {
    "provider": "MarineTraffic",
    "mmsi": "677350000",
    "name": "SHIP_NAME",
    "callsign": "CALL_SIGN",
    "type": "Cargo",
    "lat": 12.345,
    "lon": 67.890,
    "speed": 15.2,
    "course": 180.0,
    "heading": 185.0,
    "draught": 8.5,
    "nav_status": "Under way using engine",
    "destination": "PORT_NAME",
    "timestamp": "2024-01-01T12:00:00Z",
    "imo": "1234567",
    "comparison_id": null,
    "data_source": "MarineTraffic",
    "created_at": "2024-01-01T12:00:00Z",
    "updated_at": "2024-01-01T12:00:00Z"
  },
  "created": true,
  "source": "marinetraffic"
}
```

## Important Notes

### Rate Limiting and Ethics
- **Respect robots.txt**: Always check MarineTraffic's robots.txt
- **Add delays**: The scraper includes random delays between requests
- **Use official API**: Consider using MarineTraffic's official API for production use
- **Legal compliance**: Ensure your use complies with MarineTraffic's terms of service

### Anti-Detection Measures
The enhanced scraper includes:
- Rotating user agents
- Random delays between requests
- Session management
- Proper HTTP headers
- Multiple extraction strategies

### Limitations
- MarineTraffic actively blocks automated requests
- Some data may not be available for all ships
- Real-time data requires frequent updates
- Free access may be limited

## Alternative Approaches

### 1. Official MarineTraffic API
```python
# Use their official API (requires subscription)
import requests

api_key = "YOUR_API_KEY"
url = f"https://services.marinetraffic.com/api/exportvessel/{api_key}/v:5/mmsi:{mmsi}/protocol:json"
response = requests.get(url)
```

### 2. AIS Data Providers
Consider alternative AIS data providers:
- VesselFinder API
- ShipAIS API
- AISHub
- MarineTraffic API (official)

### 3. Selenium-based Scraping
For heavily protected sites:
```python
from selenium import webdriver
from selenium.webdriver.chrome.options import Options

options = Options()
options.add_argument('--headless')
driver = webdriver.Chrome(options=options)
# ... scraping logic
```

## Troubleshooting

### Common Issues

1. **403 Forbidden Error**
   - MarineTraffic is blocking the request
   - Try the enhanced scraper with better headers
   - Consider using proxies or VPN
   - Use official API instead

2. **No Data Extracted**
   - Website structure may have changed
   - Check if the ship exists in MarineTraffic
   - Verify MMSI format

3. **Rate Limiting**
   - Increase delays between requests
   - Use session management
   - Implement exponential backoff

### Debug Mode
```python
# Enable debug logging
import logging
logging.basicConfig(level=logging.DEBUG)

# Test with enhanced scraper
from enhanced_scraper import EnhancedMarineTrafficScraper
scraper = EnhancedMarineTrafficScraper()
data = scraper.get_ship_details("677350000")
```

## Legal Disclaimer

This tool is for educational and research purposes. Always:
- Respect website terms of service
- Follow robots.txt guidelines
- Consider rate limiting and server load
- Use official APIs when available
- Ensure compliance with applicable laws

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## License

This project is provided as-is for educational purposes. Please ensure compliance with all applicable terms of service and laws.
