#!/usr/bin/env python3
"""
Unified script to trigger both MarineTraffic and VesselFinder scrapers
"""

import requests
import os
from typing import Optional, List


def trigger_scraper(
    github_token: str,
    repo_owner: str,
    repo_name: str,
    provider: str,
    mmsi: Optional[str] = None,
    imo: Optional[str] = None,
    comparison_id: Optional[str] = None,
    headless: bool = True,
    send_to_posthog: bool = True,
    **kwargs
) -> bool:
    """
    Trigger a scraper GitHub Action
    
    Args:
        github_token: GitHub personal access token
        repo_owner: GitHub repository owner
        repo_name: GitHub repository name
        provider: Provider name ('marinetraffic' or 'vesselfinder')
        mmsi: Ship MMSI number
        imo: Ship IMO number
        comparison_id: Optional comparison ID for PostHog
        headless: Run browser in headless mode
        send_to_posthog: Send data to PostHog
        **kwargs: Additional provider-specific parameters
        
    Returns:
        True if successful, False otherwise
    """
    
    provider = provider.lower()
    
    if provider == 'marinetraffic':
        event_type = "scrape-marine-traffic"
        if not mmsi:
            print("❌ MMSI is required for MarineTraffic")
            return False
    elif provider == 'vesselfinder':
        event_type = "scrape-vesselfinder"
        if not mmsi and not imo:
            print("❌ Either MMSI or IMO must be provided for VesselFinder")
            return False
    else:
        print(f"❌ Unknown provider: {provider}")
        return False
    
    url = f"https://api.github.com/repos/{repo_owner}/{repo_name}/dispatches"
    
    headers = {
        "Authorization": f"token {github_token}",
        "Accept": "application/vnd.github.v3+json",
        "Content-Type": "application/json"
    }
    
    # Build client payload
    client_payload = {
        "mmsi": mmsi,
        "comparison_id": comparison_id,
        "headless": headless,
        "send_to_posthog": send_to_posthog
    }
    
    # Add provider-specific fields
    if provider == 'vesselfinder':
        client_payload["imo"] = imo
    elif provider == 'marinetraffic':
        client_payload["fetch_datadocked"] = kwargs.get('fetch_datadocked', False)
        client_payload["fetch_datadocked_satellite"] = kwargs.get('fetch_datadocked_satellite', False)
    
    payload = {
        "event_type": event_type,
        "client_payload": client_payload
    }
    
    try:
        response = requests.post(url, headers=headers, json=payload)
        
        if response.status_code == 204:
            identifier = mmsi if mmsi else imo
            identifier_type = "MMSI" if mmsi else "IMO"
            print(f"✅ Successfully triggered {provider.upper()} scraper for {identifier_type}: {identifier}")
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


def trigger_all_providers(
    github_token: str,
    repo_owner: str,
    repo_name: str,
    mmsi: str,
    comparison_id: Optional[str] = None,
    headless: bool = True,
    send_to_posthog: bool = True
) -> dict:
    """
    Trigger all available providers for the same vessel
    
    Returns:
        Dictionary with provider names as keys and success status as values
    """
    results = {}
    
    print(f"\n{'='*60}")
    print(f"Triggering all providers for MMSI: {mmsi}")
    print(f"{'='*60}\n")
    
    # Trigger MarineTraffic
    print("1. Triggering MarineTraffic scraper...")
    results['marinetraffic'] = trigger_scraper(
        github_token=github_token,
        repo_owner=repo_owner,
        repo_name=repo_name,
        provider='marinetraffic',
        mmsi=mmsi,
        comparison_id=comparison_id,
        headless=headless,
        send_to_posthog=send_to_posthog
    )
    
    print()
    
    # Trigger VesselFinder
    print("2. Triggering VesselFinder scraper...")
    results['vesselfinder'] = trigger_scraper(
        github_token=github_token,
        repo_owner=repo_owner,
        repo_name=repo_name,
        provider='vesselfinder',
        mmsi=mmsi,
        comparison_id=comparison_id,
        headless=headless,
        send_to_posthog=send_to_posthog
    )
    
    print(f"\n{'='*60}")
    print("SUMMARY")
    print(f"{'='*60}")
    for provider, success in results.items():
        status = "✅ SUCCESS" if success else "❌ FAILED"
        print(f"{provider.upper()}: {status}")
    print(f"{'='*60}\n")
    
    return results


def main():
    """Example usage"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Trigger vessel scraper GitHub Actions')
    parser.add_argument('--provider', choices=['marinetraffic', 'vesselfinder', 'all'], 
                       default='all', help='Provider to trigger')
    parser.add_argument('--mmsi', help='Ship MMSI number')
    parser.add_argument('--imo', help='Ship IMO number')
    parser.add_argument('--comparison-id', help='Comparison ID for PostHog')
    parser.add_argument('--headless', action='store_true', default=True, help='Run in headless mode')
    parser.add_argument('--send-to-posthog', action='store_true', default=True, help='Send to PostHog')
    
    args = parser.parse_args()
    
    # Get configuration from environment
    GITHUB_TOKEN = os.getenv('GITHUB_TOKEN')
    REPO_OWNER = os.getenv('GITHUB_REPO_OWNER', 'your-username')
    REPO_NAME = os.getenv('GITHUB_REPO_NAME', 'marine-traffic-scrapping')
    
    if not GITHUB_TOKEN:
        print("❌ GITHUB_TOKEN environment variable is required")
        print("   Set it with: export GITHUB_TOKEN=your_token_here")
        return
    
    if not args.mmsi and not args.imo:
        print("❌ Either --mmsi or --imo must be provided")
        return
    
    if args.provider == 'all':
        if not args.mmsi:
            print("❌ MMSI is required when triggering all providers")
            return
        
        results = trigger_all_providers(
            github_token=GITHUB_TOKEN,
            repo_owner=REPO_OWNER,
            repo_name=REPO_NAME,
            mmsi=args.mmsi,
            comparison_id=args.comparison_id,
            headless=args.headless,
            send_to_posthog=args.send_to_posthog
        )
        
        # Exit with error if any provider failed
        if not all(results.values()):
            exit(1)
    else:
        success = trigger_scraper(
            github_token=GITHUB_TOKEN,
            repo_owner=REPO_OWNER,
            repo_name=REPO_NAME,
            provider=args.provider,
            mmsi=args.mmsi,
            imo=args.imo,
            comparison_id=args.comparison_id,
            headless=args.headless,
            send_to_posthog=args.send_to_posthog
        )
        
        if not success:
            exit(1)


if __name__ == "__main__":
    main()
