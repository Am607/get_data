#!/usr/bin/env python3
"""
GitHub Actions script for MarineTraffic Selenium scraper with PostHog integration
"""

import os
import sys
import argparse
import logging
from selenium_scraper import get_ship_data_selenium

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def main():
    """Main function for GitHub Actions"""
    parser = argparse.ArgumentParser(description='Scrape MarineTraffic data and send to PostHog')
    parser.add_argument('--mmsi', required=True, help='Ship MMSI number')
    parser.add_argument('--comparison-id', help='Comparison ID for PostHog')
    parser.add_argument('--headless', action='store_true', default=True, help='Run in headless mode')
    parser.add_argument('--send-to-posthog', action='store_true', default=True, help='Send data to PostHog')
    
    args = parser.parse_args()
    
    # Validate environment variables
    required_env_vars = ['POSTHOG_API_KEY']
    missing_vars = [var for var in required_env_vars if not os.getenv(var)]
    
    if missing_vars and args.send_to_posthog:
        logger.error(f"Missing required environment variables: {missing_vars}")
        sys.exit(1)
    
    try:
        logger.info(f"Starting scrape for MMSI: {args.mmsi}")
        logger.info(f"Comparison ID: {args.comparison_id}")
        logger.info(f"PostHog enabled: {args.send_to_posthog}")
        
        # Scrape data
        ship_data = get_ship_data_selenium(
            mmsi=args.mmsi,
            headless=args.headless,
            comparison_id=args.comparison_id,
            send_to_posthog=args.send_to_posthog
        )
        
        if ship_data:
            logger.info("✅ Scraping completed successfully")
            logger.info(f"Extracted data for ship: {ship_data.get('name', 'Unknown')}")
            logger.info(f"Position: {ship_data.get('lat')}, {ship_data.get('lon')}")
            
            if args.send_to_posthog:
                logger.info("✅ Data sent to PostHog")
            
            # Output summary for GitHub Actions
            print(f"::notice title=Scraping Success::Successfully scraped data for MMSI {args.mmsi}")
            # Use Environment Files instead of deprecated set-output
            with open(os.environ['GITHUB_OUTPUT'], 'a') as fh:
                print(f"ship_name={ship_data.get('name', 'Unknown')}", file=fh)
                print(f"latitude={ship_data.get('lat', 'N/A')}", file=fh)
                print(f"longitude={ship_data.get('lon', 'N/A')}", file=fh)
            
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
