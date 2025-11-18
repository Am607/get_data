# VesselFinder Scraper

This scraper extracts vessel data from VesselFinder.com with authentication support.

## Features

- **Authentication**: Automatic login to VesselFinder Pro account
- **Comprehensive Data Extraction**: Extracts vessel details including position, speed, course, and more
- **Multiple Data Sources**: Captures data from API calls, page elements, and HTML source
- **PostHog Integration**: Optional analytics tracking
- **Anti-Detection**: Browser automation with anti-detection measures

## Setup

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure Environment Variables

Create a `.env` file in the project root with your VesselFinder credentials:

```env
# VesselFinder Credentials
VESSELFINDER_EMAIL=your-email@example.com
VESSELFINDER_PASSWORD=your-password

# PostHog Configuration (optional)
POSTHOG_API_KEY=your-posthog-key
POSTHOG_HOST=https://app.posthog.com
```

**Note**: The credentials are already configured in the `.env` file:
- Email: `lascadetestuser@gmail.com`
- Password: `lascadetestuser@123`

### 3. Install ChromeDriver

Make sure you have ChromeDriver installed and in your PATH:

```bash
# macOS (using Homebrew)
brew install chromedriver

# Or download from: https://chromedriver.chromium.org/
```

## Usage

### Command Line

```bash
# By MMSI (9 digits)
python vesselfinder_scraper.py 228078060

# By IMO (7 digits)
python vesselfinder_scraper.py 9876543
```

### Python Script

```python
from vesselfinder_scraper import get_vessel_data

# Get vessel data by MMSI
vessel_data = get_vessel_data(mmsi="228078060", headless=False)
print(vessel_data)

# Get vessel data by IMO
vessel_data = get_vessel_data(imo="9876543", headless=False)
print(vessel_data)
```

### Using the Class

```python
from vesselfinder_scraper import VesselFinderScraper

# Create scraper instance
with VesselFinderScraper(headless=False) as scraper:
    # Get vessel details
    vessel_data = scraper.get_vessel_details(mmsi="228078060")
    print(vessel_data)
```

## Extracted Data Fields

The scraper extracts the following fields:

- `provider` - Data provider (VesselFinder)
- `mmsi` - Maritime Mobile Service Identity
- `imo` - International Maritime Organization number
- `name` - Vessel name
- `callsign` - Radio call sign
- `type` - Vessel type
- `lat` - Latitude
- `lon` - Longitude
- `speed` - Speed over ground (knots)
- `course` - Course over ground (degrees)
- `heading` - Vessel heading (degrees)
- `draught` - Current draught (meters)
- `nav_status` - Navigation status
- `destination` - Destination port
- `timestamp` - Last position timestamp
- `comparison_id` - Internal comparison ID
- `data_source` - Source of the data
- `length` - Vessel length (meters)
- `width` - Vessel width/beam (meters)
- `flag` - Flag state
- `built` - Year built
- `eta` - Estimated time of arrival

## Example Output

```json
{
  "provider": "VesselFinder",
  "mmsi": "228078060",
  "imo": "9876543",
  "name": "VESSEL NAME",
  "callsign": "CALL123",
  "type": "Cargo",
  "lat": 45.123456,
  "lon": -73.654321,
  "speed": 12.5,
  "course": 180.0,
  "heading": 185.0,
  "draught": 8.5,
  "nav_status": "Under way using engine",
  "destination": "PORT NAME",
  "timestamp": "2024-01-01T12:00:00Z",
  "comparison_id": null,
  "data_source": "VesselFinder",
  "length": 150.0,
  "width": 25.0,
  "flag": "France",
  "built": "2015",
  "eta": "2024-01-02 14:00"
}
```

## How It Works

1. **Authentication**: The scraper logs into VesselFinder using the credentials from `.env`
2. **Navigation**: Navigates to the vessel details page using MMSI or IMO
3. **Data Extraction**: Extracts data from multiple sources:
   - Network API calls (captured from browser logs)
   - Page elements (tables, lists, text)
   - HTML source code (JSON in script tags, embedded data)
4. **Data Parsing**: Parses and normalizes the extracted data
5. **Return**: Returns a structured dictionary with vessel information

## Headless Mode

By default, the scraper runs with the browser visible (`headless=False`). This is useful for:
- Debugging
- Seeing the login process
- Verifying data extraction

To run in headless mode (no browser window):

```python
vessel_data = get_vessel_data(mmsi="228078060", headless=True)
```

## Error Handling

The scraper includes comprehensive error handling:

```python
try:
    vessel_data = get_vessel_data(mmsi="228078060")
    print("Success:", vessel_data)
except Exception as e:
    print(f"Error: {e}")
```

## Integration with Existing Code

### Django Integration

You can integrate this scraper with the existing Django models:

```python
from vesselfinder_scraper import get_vessel_data
from your_app.models import Ship

# Get vessel data
vessel_data = get_vessel_data(mmsi="228078060")

# Create or update Ship record
ship, created = Ship.objects.update_or_create(
    mmsi=vessel_data['mmsi'],
    defaults=vessel_data
)
```

### Multi-Provider Support

Combine with the existing MarineTraffic scraper:

```python
from vesselfinder_scraper import get_vessel_data as get_vesselfinder_data
from selenium_scraper import SeleniumMarineTrafficScraper

def get_vessel_data_multi_provider(mmsi):
    """Try multiple providers"""
    
    # Try VesselFinder first
    try:
        return get_vesselfinder_data(mmsi=mmsi, headless=True)
    except Exception as e:
        print(f"VesselFinder failed: {e}")
    
    # Fallback to MarineTraffic
    try:
        scraper = SeleniumMarineTrafficScraper(headless=True)
        return scraper.get_ship_details(mmsi)
    except Exception as e:
        print(f"MarineTraffic failed: {e}")
    
    return None
```

## Troubleshooting

### Login Issues

If login fails:
1. Verify credentials in `.env` file
2. Check if VesselFinder has changed their login page
3. Try running with `headless=False` to see what's happening
4. Check for CAPTCHA or additional verification steps

### Data Extraction Issues

If data is not being extracted:
1. Run with `headless=False` to see the page
2. Check browser console logs
3. Verify the vessel exists on VesselFinder
4. Check if the page structure has changed

### ChromeDriver Issues

If ChromeDriver fails:
```bash
# Update ChromeDriver
brew upgrade chromedriver

# Or download matching version for your Chrome browser
```

## Rate Limiting

- The scraper includes delays to avoid overwhelming the server
- Login is performed once per session
- Consider implementing additional rate limiting for batch operations

## Legal and Ethical Considerations

- **Terms of Service**: Ensure compliance with VesselFinder's terms of service
- **Rate Limiting**: Respect server resources with appropriate delays
- **Authentication**: Only use valid credentials you own
- **Data Usage**: Use scraped data responsibly and legally
- **Official API**: Consider using VesselFinder's official API for production use

## PostHog Analytics

If you have PostHog configured, the scraper will automatically track:
- Successful vessel data scrapes
- Failed scrape attempts
- Error details

Events tracked:
- `vessel_data_scraped` - Successful scrape
- `vessel_data_scrape_failed` - Failed scrape

## License

This project is provided as-is for educational purposes. Please ensure compliance with all applicable terms of service and laws.
