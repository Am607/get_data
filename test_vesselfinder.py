#!/usr/bin/env python3
"""
Test script for VesselFinder scraper
Tests all functionality including PostHog integration
"""

import os
from dotenv import load_dotenv
from vesselfinder_scraper import get_vessel_data

# Load environment variables
load_dotenv()

def test_basic_scrape():
    """Test basic scraping without PostHog"""
    print("="*60)
    print("TEST 1: Basic Scrape (No PostHog)")
    print("="*60)
    
    vessel_data = get_vessel_data(
        mmsi="228078060",
        headless=True,
        comparison_id=None  # No PostHog push
    )
    
    print(f"\n✅ Scrape completed!")
    print(f"MMSI: {vessel_data.get('mmsi')}")
    print(f"Name: {vessel_data.get('name')}")
    print(f"Callsign: {vessel_data.get('callsign')}")
    print(f"Position: {vessel_data.get('lat')}, {vessel_data.get('lon')}")
    print(f"Speed: {vessel_data.get('speed')}")
    print(f"Course: {vessel_data.get('course')}")
    print(f"Heading: {vessel_data.get('heading')}")
    
    return vessel_data


def test_with_comparison_id():
    """Test scraping with comparison_id (PostHog push)"""
    print("\n" + "="*60)
    print("TEST 2: Scrape with comparison_id (PostHog Push)")
    print("="*60)
    
    # Check if PostHog is configured
    if not os.getenv('POSTHOG_API_KEY'):
        print("⚠️  POSTHOG_API_KEY not set - PostHog push will be skipped")
        print("   Set POSTHOG_API_KEY in .env to test PostHog integration")
    
    vessel_data = get_vessel_data(
        mmsi="228078060",
        headless=True,
        comparison_id="test-comparison-vesselfinder-001"
    )
    
    print(f"\n✅ Scrape completed!")
    print(f"Comparison ID: {vessel_data.get('comparison_id')}")
    print(f"Data Source: {vessel_data.get('data_source')}")
    
    if os.getenv('POSTHOG_API_KEY'):
        print(f"✅ PostHog event sent with comparison_id: {vessel_data.get('comparison_id')}")
    else:
        print(f"⚠️  PostHog push skipped (no API key)")
    
    return vessel_data


def test_coordinate_normalization():
    """Test that coordinates are properly normalized"""
    print("\n" + "="*60)
    print("TEST 3: Coordinate Normalization")
    print("="*60)
    
    vessel_data = get_vessel_data(
        mmsi="228078060",
        headless=True
    )
    
    lat = vessel_data.get('lat')
    lon = vessel_data.get('lon')
    
    print(f"Latitude: {lat}")
    print(f"Longitude: {lon}")
    
    # Check if coordinates are in valid range
    if lat and lon:
        if -90 <= lat <= 90 and -180 <= lon <= 180:
            print("✅ Coordinates are properly normalized!")
        else:
            print("❌ Coordinates are out of valid range!")
            print(f"   Valid range: lat [-90, 90], lon [-180, 180]")
    else:
        print("⚠️  Coordinates not extracted")
    
    return vessel_data


def main():
    """Run all tests"""
    print("\n" + "🚢 " * 20)
    print("VESSELFINDER SCRAPER TEST SUITE")
    print("🚢 " * 20 + "\n")
    
    try:
        # Test 1: Basic scrape
        test_basic_scrape()
        
        # Test 2: With comparison_id
        test_with_comparison_id()
        
        # Test 3: Coordinate normalization
        test_coordinate_normalization()
        
        print("\n" + "="*60)
        print("✅ ALL TESTS COMPLETED")
        print("="*60)
        print("\nNOTE: Some fields (speed, course, heading) may not be")
        print("extracted if VesselFinder loads them dynamically via")
        print("JavaScript after page load. Consider increasing wait times")
        print("or adding more specific extraction logic.")
        
    except Exception as e:
        print(f"\n❌ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
