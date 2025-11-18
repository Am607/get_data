#!/usr/bin/env python3
"""
VesselFinder scraper for GitHub Actions with PostHog integration
Similar to github_action_scraper.py but for VesselFinder
"""

import os
import sys
import argparse
import logging
from datetime import datetime
from vesselfinder_scraper import get_vessel_data

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def send_to_posthog(data: dict, comparison_id: str = None):
    """Send VesselFinder data to PostHog"""
    try:
        import posthog
        
        posthog.api_key = os.getenv('POSTHOG_API_KEY')
        posthog.host = os.getenv('POSTHOG_HOST', 'https://app.posthog.com')
        
        if not posthog.api_key:
            logger.warning("PostHog API key not found, skipping PostHog push")
            return False
        
        timestamp_dt = datetime.now()
        
        logger.info(f"Processing VesselFinder data for PostHog: {data}")
        logger.info(f"PostHog comparison_id: {comparison_id}")
        
        # Clean MMSI - remove quotes if present
        mmsi_value = data.get("mmsi")
        if mmsi_value and isinstance(mmsi_value, str):
            mmsi_value = mmsi_value.strip('"')
        
        # Format data according to PostHog specification
        posthog_properties = {
            "provider": "VesselFinder",
            "mmsi": str(mmsi_value) if mmsi_value else str(data.get("mmsi", "")),
            "name": data.get("name"),
            "callsign": data.get("callsign"),
            "type": data.get("type"),
            "lat": float(data.get("lat")) if data.get("lat") else None,
            "lon": float(data.get("lon")) if data.get("lon") else None,
            "speed": float(data.get("speed")) if data.get("speed") else None,
            "course": float(data.get("course")) if data.get("course") else None,
            "heading": float(data.get("heading")) if data.get("heading") else None,
            "draught": float(data.get("draught")) if data.get("draught") else None,
            "nav_status": data.get("nav_status"),
            "destination": data.get("destination", ""),
            "timestamp": timestamp_dt.isoformat(),
            "imo": data.get("imo"),
            "comparison_id": comparison_id,
            "data_source": "VesselFinder"
        }
        
        logger.info(f"PostHog properties to send: {posthog_properties}")
        
        # Send to PostHog
        posthog.capture(
            distinct_id="vesselfinder_scraper",
            event="local_comparison",
            properties=posthog_properties,
            timestamp=timestamp_dt
        )
        
        logger.info(f"Successfully sent VesselFinder data to PostHog for MMSI: {data.get('mmsi')}")
        return True
        
    except Exception as e:
        logger.error(f"Error sending VesselFinder data to PostHog: {e}")
        return False


def main():
    """Main function for GitHub Actions or standalone use"""
    parser = argparse.ArgumentParser(description='Scrape VesselFinder data and send to PostHog')
    parser.add_argument('--mmsi', help='Ship MMSI number')
    parser.add_argument('--imo', help='Ship IMO number')
    parser.add_argument('--comparison-id', help='Comparison ID for PostHog')
    parser.add_argument('--headless', action='store_true', default=True, help='Run in headless mode')
    parser.add_argument('--send-to-posthog', action='store_true', default=True, help='Send data to PostHog')
    
    args = parser.parse_args()
    
    # Validate that either MMSI or IMO is provided
    if not args.mmsi and not args.imo:
        logger.error("Either --mmsi or --imo must be provided")
        sys.exit(1)
    
    # Validate environment variables
    if args.send_to_posthog:
        if not os.getenv('POSTHOG_API_KEY'):
            logger.warning("POSTHOG_API_KEY not set, PostHog push will be skipped")
    
    # Check VesselFinder credentials
    if not os.getenv('VESSELFINDER_EMAIL') or not os.getenv('VESSELFINDER_PASSWORD'):
        logger.error("VesselFinder credentials not found. Set VESSELFINDER_EMAIL and VESSELFINDER_PASSWORD")
        sys.exit(1)
    
    try:
        identifier = args.mmsi or args.imo
        identifier_type = "MMSI" if args.mmsi else "IMO"
        
        logger.info(f"Starting VesselFinder scrape for {identifier_type}: {identifier}")
        logger.info(f"Comparison ID: {args.comparison_id}")
        logger.info(f"PostHog enabled: {args.send_to_posthog}")
        logger.info(f"Headless mode: {args.headless}")
        
        # Scrape VesselFinder data
        vessel_data = get_vessel_data(
            mmsi=args.mmsi,
            imo=args.imo,
            headless=args.headless,
            comparison_id=args.comparison_id
        )
        
        if vessel_data:
            logger.info(f"Successfully scraped VesselFinder data for {identifier_type}: {identifier}")
            logger.info(f"Vessel data: {vessel_data}")
            
            # Send to PostHog if enabled
            if args.send_to_posthog and args.comparison_id:
                logger.info("Sending data to PostHog...")
                if send_to_posthog(vessel_data, args.comparison_id):
                    logger.info("✅ Data successfully sent to PostHog")
                else:
                    logger.error("❌ Failed to send data to PostHog")
            elif args.send_to_posthog and not args.comparison_id:
                logger.warning("⚠️ PostHog enabled but no comparison_id provided, skipping PostHog push")
            
            # Print summary
            print("\n" + "="*60)
            print("VESSELFINDER SCRAPE SUMMARY")
            print("="*60)
            print(f"Provider: VesselFinder")
            print(f"{identifier_type}: {identifier}")
            print(f"Vessel Name: {vessel_data.get('name', 'N/A')}")
            print(f"Callsign: {vessel_data.get('callsign', 'N/A')}")
            print(f"Type: {vessel_data.get('type', 'N/A')}")
            print(f"Position: {vessel_data.get('lat', 'N/A')}, {vessel_data.get('lon', 'N/A')}")
            print(f"Speed: {vessel_data.get('speed', 'N/A')} knots")
            print(f"Course: {vessel_data.get('course', 'N/A')}°")
            print(f"Heading: {vessel_data.get('heading', 'N/A')}°")
            print(f"Destination: {vessel_data.get('destination', 'N/A')}")
            print(f"Comparison ID: {args.comparison_id or 'N/A'}")
            print("="*60)
            
            sys.exit(0)
        else:
            logger.error(f"Failed to scrape VesselFinder data for {identifier_type}: {identifier}")
            sys.exit(1)
            
    except Exception as e:
        logger.error(f"Error in main execution: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
