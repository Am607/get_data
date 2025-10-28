#!/usr/bin/env python3
"""
Script to trigger GitHub Actions workflow from your backend
"""

import requests
import json
import os
from typing import Optional


def trigger_marine_traffic_scraper(
    github_token: str,
    repo_owner: str,
    repo_name: str,
    mmsi: str,
    comparison_id: Optional[str] = None,
    headless: bool = True,
    send_to_posthog: bool = True
) -> bool:
    """
    Trigger the MarineTraffic scraper GitHub Action
    
    Args:
        github_token: GitHub personal access token
        repo_owner: GitHub repository owner
        repo_name: GitHub repository name
        mmsi: Ship MMSI number
        comparison_id: Optional comparison ID for PostHog
        headless: Run browser in headless mode
        send_to_posthog: Send data to PostHog
        
    Returns:
        True if successful, False otherwise
    """
    
    url = f"https://api.github.com/repos/{repo_owner}/{repo_name}/dispatches"
    
    headers = {
        "Authorization": f"token {github_token}",
        "Accept": "application/vnd.github.v3+json",
        "Content-Type": "application/json"
    }
    
    payload = {
        "event_type": "scrape-marine-traffic",
        "client_payload": {
            "mmsi": mmsi,
            "comparison_id": comparison_id,
            "headless": headless,
            "send_to_posthog": send_to_posthog
        }
    }
    
    try:
        response = requests.post(url, headers=headers, json=payload)
        
        if response.status_code == 204:
            print(f"✅ Successfully triggered scraper for MMSI: {mmsi}")
            if comparison_id:
                print(f"   Comparison ID: {comparison_id}")
            return True
        else:
            print(f"❌ Failed to trigger scraper. Status: {response.status_code}")
            print(f"   Response: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Error triggering scraper: {e}")
        return False


def main():
    """Example usage"""
    # These should come from your environment or configuration
    GITHUB_TOKEN = os.getenv('GITHUB_TOKEN')
    REPO_OWNER = os.getenv('GITHUB_REPO_OWNER', 'your-username')
    REPO_NAME = os.getenv('GITHUB_REPO_NAME', 'marine-traffic-scrapping')
    
    if not GITHUB_TOKEN:
        print("❌ GITHUB_TOKEN environment variable is required")
        return
    
    # Example trigger
    success = trigger_marine_traffic_scraper(
        github_token=GITHUB_TOKEN,
        repo_owner=REPO_OWNER,
        repo_name=REPO_NAME,
        mmsi="677350000",
        comparison_id="test-comparison-123",
        headless=True,
        send_to_posthog=True
    )
    
    if success:
        print("🚀 GitHub Action triggered successfully!")
    else:
        print("💥 Failed to trigger GitHub Action")


if __name__ == "__main__":
    main()
