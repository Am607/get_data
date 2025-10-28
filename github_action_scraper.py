#!/usr/bin/env python3
"""
GitHub Actions script for MarineTraffic Selenium scraper with PostHog integration
"""

import os
import sys
import argparse
import logging
import requests
from datetime import datetime
from selenium_scraper import get_ship_data_selenium

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def fetch_datadocked_data(mmsi: str, api_key: str, base_url: str, data_type: str = "datadocked") -> dict:
    """Fetch data from Datadocked API"""
    try:
        logger.warning(f"[{data_type.upper()}] FETCHED - Calling {data_type} API for MMSI {mmsi}")
        params = {"imo_or_mmsi": mmsi}
        headers = {"api_key": api_key}
        
        api_result = requests.get(f"{base_url}get-vessel-location", params=params, headers=headers, timeout=20)
        
        if api_result.status_code == 200:
            response_json = api_result.json()
            logger.info(f"[{data_type.upper()}] RAW RESPONSE - {response_json}")
            
            if response_json:  # Check if response is not empty
                # Check if the response contains valid vessel data
                if response_json.get("detail") or (response_json.get("mmsi") and response_json.get("latitude") and response_json.get("longitude")):
                    logger.info(f"[{data_type.upper()}] SUCCESS - Got valid data for MMSI {mmsi}")
                    return response_json
                else:
                    logger.warning(f"[{data_type.upper()}] NO VESSEL DATA - API returned response but no vessel data for MMSI {mmsi}")
                    return None
            else:
                logger.warning(f"[{data_type.upper()}] EMPTY - API returned empty data for MMSI {mmsi}")
                return None
        else:
            logger.warning(f"[{data_type.upper()}] HTTP {api_result.status_code} - {api_result.text[:200]} for MMSI {mmsi}")
            return None
            
    except Exception as e:
        logger.error(f"[{data_type.upper()}] ERROR - Exception occurred for MMSI {mmsi}: {str(e)}")
        return None


def send_to_posthog(data: dict, event_name: str, distinct_id: str, comparison_id: str = None, data_source: str = None):
    """Send data to PostHog"""
    try:
        # Import here to avoid circular import issues
        import posthog
        
        posthog.api_key = os.getenv('POSTHOG_API_KEY')
        posthog.host = os.getenv('POSTHOG_HOST', 'https://app.posthog.com')
        
        # Get current timestamp
        timestamp_dt = datetime.now()
        timestamp_iso = timestamp_dt.isoformat()
        
        logger.info(f"Processing {data_source} data for PostHog: {data}")
        logger.info(f"PostHog comparison_id: {comparison_id}")
        
        # Clean MMSI - remove quotes if present
        mmsi_value = data.get("mmsi")
        if mmsi_value and isinstance(mmsi_value, str):
            mmsi_value = mmsi_value.strip('"')
        
        # Format data according to your specification
        posthog_properties = {
            "provider": data_source,
            "mmsi": str(mmsi_value) if mmsi_value else str(data.get("mmsi", "")),
            "name": data.get("name"),
            "callsign": data.get("callsign"),
            "type": data.get("typeSpecific") if data_source != "MarineTraffic" else data.get("type"),
            "lat": float(data.get("latitude")) if data.get("latitude") else float(data.get("lat")) if data.get("lat") else None,
            "lon": float(data.get("longitude")) if data.get("longitude") else float(data.get("lon")) if data.get("lon") else None,
            "speed": data.get("speed") if data.get("speed") else None,
            "course": data.get("course") if data.get("course") else None,
            "heading": data.get("heading") if data.get("heading") else None,
            "draught": data.get("draught") if data.get("draught") else None,
            "nav_status": data.get("navigationalStatus") if data_source != "MarineTraffic" else data.get("nav_status"),
            "destination": data.get("destination", ""),
            "timestamp": timestamp_iso,
            "imo": data.get("imo"),
            "comparison_id": comparison_id,
            "data_source": data_source
        }
        
        logger.info(f"PostHog properties to send: {posthog_properties}")
        
        # Send to PostHog
        posthog.capture(
            distinct_id=distinct_id,
            event=event_name,
            properties=posthog_properties,
            timestamp=timestamp_dt
        )
        
        logger.info(f"Successfully sent {data_source} data to PostHog for MMSI: {data.get('mmsi')}")
        return True
        
    except Exception as e:
        logger.error(f"Error sending {data_source} data to PostHog: {e}")
        return False


def has_valid_data(data: dict) -> bool:
    """Check if data has valid vessel information"""
    if not data:
        return False
    
    # Check if key fields have data
    mmsi = data.get("mmsi")
    lat = data.get("latitude") or data.get("lat")
    lon = data.get("longitude") or data.get("lon")
    
    return mmsi is not None and str(mmsi).strip() != "None" and lat is not None and lon is not None


def push_all_data_to_posthog(marinetraffic_data: dict, datadocked_data: dict, datadocked_satellite_data: dict, mmsi: str, comparison_id: str):
    """Push all three data sources to PostHog"""
    success_count = 0
    total_sources = 0
    
    # Send MarineTraffic data
    if marinetraffic_data:
        total_sources += 1
        if send_to_posthog(marinetraffic_data, "local_comparison", "selenium_scraper", comparison_id, "MarineTraffic"):
            success_count += 1
        else:
            logger.error("Failed to send MarineTraffic data to PostHog")
    
    # Send Datadocked data
    if datadocked_data:
        dd_detail = datadocked_data.get("detail", datadocked_data)
        total_sources += 1
        if has_valid_data(dd_detail):
            if send_to_posthog(dd_detail, "local_comparison", "selenium_scraper", comparison_id, "datadocked"):
                success_count += 1
            else:
                logger.error("Failed to send Datadocked data to PostHog")
        else:
            logger.warning("Skipping Datadocked data - no valid vessel data received")
    
    # Send Datadocked Satellite data
    if datadocked_satellite_data:
        dd_sat_detail = datadocked_satellite_data.get("detail", datadocked_satellite_data)
        total_sources += 1
        if has_valid_data(dd_sat_detail):
            if send_to_posthog(dd_sat_detail, "local_comparison", "selenium_scraper", comparison_id, "datadocked_satellite"):
                success_count += 1
            else:
                logger.error("Failed to send Datadocked Satellite data to PostHog")
        else:
            logger.warning("Skipping Datadocked Satellite data - no valid vessel data received")
    
    logger.warning(f"Successfully pushed {success_count}/{total_sources} valid data sources to PostHog for MMSI {mmsi}")


def main():
    """Main function for GitHub Actions"""
    parser = argparse.ArgumentParser(description='Scrape MarineTraffic data and send to PostHog')
    parser.add_argument('--mmsi', required=True, help='Ship MMSI number')
    parser.add_argument('--comparison-id', help='Comparison ID for PostHog')
    parser.add_argument('--headless', action='store_true', default=True, help='Run in headless mode')
    parser.add_argument('--send-to-posthog', action='store_true', default=True, help='Send data to PostHog')
    parser.add_argument('--fetch-datadocked', action='store_true', default=False, help='Fetch data from Datadocked API')
    parser.add_argument('--fetch-datadocked-satellite', action='store_true', default=False, help='Fetch data from Datadocked Satellite API')
    
    args = parser.parse_args()
    
    # Validate environment variables
    required_env_vars = ['POSTHOG_API_KEY']
    if args.fetch_datadocked:
        required_env_vars.extend(['DATADOCKED_BASE_URL', 'DATADOCKED_API_KEY'])
    if args.fetch_datadocked_satellite:
        required_env_vars.extend(['DATADOCKED_BASE_URL', 'DATADOCKED_SATELLITE_API_KEY'])
    
    missing_vars = [var for var in required_env_vars if not os.getenv(var)]
    
    if missing_vars and args.send_to_posthog:
        logger.error(f"Missing required environment variables: {missing_vars}")
        sys.exit(1)
    
    try:
        logger.info(f"Starting scrape for MMSI: {args.mmsi}")
        logger.info(f"Comparison ID: {args.comparison_id}")
        logger.info(f"PostHog enabled: {args.send_to_posthog}")
        logger.info(f"Fetch Datadocked: {args.fetch_datadocked}")
        logger.info(f"Fetch Datadocked Satellite: {args.fetch_datadocked_satellite}")
        
        # Initialize data containers
        marinetraffic_data = None
        datadocked_data = None
        datadocked_satellite_data = None
        
        # Scrape MarineTraffic data
        marinetraffic_data = get_ship_data_selenium(
            mmsi=args.mmsi,
            headless=args.headless,
            comparison_id=args.comparison_id,
            send_to_posthog=False  # We'll handle PostHog manually
        )
        
        # Fetch Datadocked data if requested
        if args.fetch_datadocked:
            datadocked_data = fetch_datadocked_data(
                args.mmsi, 
                os.getenv('DATADOCKED_API_KEY'), 
                os.getenv('DATADOCKED_BASE_URL'),
                "datadocked"
            )
        
        # Fetch Datadocked Satellite data if requested
        if args.fetch_datadocked_satellite:
            datadocked_satellite_data = fetch_datadocked_data(
                args.mmsi,
                os.getenv('DATADOCKED_SATELLITE_API_KEY'),
                os.getenv('DATADOCKED_BASE_URL'),
                "datadocked_satellite"
            )
        
        # Send all data to PostHog if requested
        if args.send_to_posthog and (marinetraffic_data or datadocked_data or datadocked_satellite_data):
            push_all_data_to_posthog(
                marinetraffic_data,
                datadocked_data,
                datadocked_satellite_data,
                args.mmsi,
                args.comparison_id
            )
        
        # Check if we got any data
        if marinetraffic_data:
            logger.info("✅ Scraping completed successfully")
            logger.info(f"Extracted data for ship: {marinetraffic_data.get('name', 'Unknown')}")
            logger.info(f"Position: {marinetraffic_data.get('lat')}, {marinetraffic_data.get('lon')}")
            
            if args.send_to_posthog:
                logger.info("✅ Data sent to PostHog")
            
            # Output summary for GitHub Actions
            print(f"::notice title=Scraping Success::Successfully scraped data for MMSI {args.mmsi}")
            # Use Environment Files instead of deprecated set-output
            with open(os.environ['GITHUB_OUTPUT'], 'a') as fh:
                print(f"ship_name={marinetraffic_data.get('name', 'Unknown')}", file=fh)
                print(f"latitude={marinetraffic_data.get('lat', 'N/A')}", file=fh)
                print(f"longitude={marinetraffic_data.get('lon', 'N/A')}", file=fh)
            
        else:
            logger.error("❌ No data extracted")
            print("::error title=Scraping Failed::No data was extracted")
            sys.exit(1)
            
    except Exception as e:
        logger.error(f"❌ Error during scraping: {e}")
        print(f"::error title=Scraping Error::{str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()
