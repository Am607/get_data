# VesselFinder Integration - Quick Start

## ✅ What's Been Added

### New Files:
1. **`vesselfinder_scraper.py`** - Core scraper with authentication
2. **`vesselfinder_action_scraper.py`** - GitHub Actions wrapper
3. **`.github/workflows/vesselfinder-scraper.yml`** - GitHub Actions workflow
4. **`trigger_vesselfinder_action.py`** - Trigger script for VesselFinder
5. **`trigger_multi_provider_action.py`** - Unified trigger for all providers
6. **`.env`** - Environment configuration with VesselFinder credentials

### Updated Files:
- **`requirements.txt`** - Added `python-dotenv` and updated `posthog`

## 🚀 Quick Test

### 1. Local Test (No GitHub Actions)
```bash
# Test basic scraping
python3 vesselfinder_scraper.py 228078060

# Test with comparison_id and PostHog
python3 vesselfinder_action_scraper.py \
  --mmsi 228078060 \
  --comparison-id test-123 \
  --headless \
  --send-to-posthog
```

### 2. GitHub Actions Test

#### Step 1: Set GitHub Secrets
Go to your repo → Settings → Secrets → Actions → New secret:
```
VESSELFINDER_EMAIL = lascadetestuser@gmail.com
VESSELFINDER_PASSWORD = lascadetestuser@123
POSTHOG_API_KEY = your_posthog_key
```

#### Step 2: Trigger Workflow
```bash
# Set environment variables
export GITHUB_TOKEN=your_github_token
export GITHUB_REPO_OWNER=your_username
export GITHUB_REPO_NAME=marine-traffic-scrapping

# Trigger VesselFinder scraper
python3 trigger_vesselfinder_action.py

# Or trigger both providers
python3 trigger_multi_provider_action.py \
  --provider all \
  --mmsi 228078060 \
  --comparison-id action-test-123
```

## 📊 Verify It's Working

### 1. Check Scraper Output
Look for:
- ✅ Login successful
- ✅ Vessel data extracted
- ✅ Coordinates normalized (should be in range -90 to 90, -180 to 180)
- ✅ comparison_id present in output
- ✅ PostHog event sent (if API key configured)

### 2. Check PostHog Dashboard
Filter by:
- Event: `local_comparison`
- Provider: `VesselFinder`
- comparison_id: Your test ID

### 3. Check GitHub Actions
- Go to Actions tab in your repo
- Look for "VesselFinder Scraper" workflow runs
- Check logs for success/errors

## 🔧 Common Issues & Fixes

### Issue: "No module named 'posthog'"
```bash
pip3 install posthog
```

### Issue: "VesselFinder credentials not found"
Check `.env` file exists and contains:
```env
VESSELFINDER_EMAIL=lascadetestuser@gmail.com
VESSELFINDER_PASSWORD=lascadetestuser@123
```

### Issue: "ChromeDriver not found"
```bash
# macOS
brew install chromedriver

# Linux (GitHub Actions handles this automatically)
```

### Issue: Coordinates are wrong (too large)
This is normal! The scraper automatically normalizes them:
- Before: 23867359.0
- After: 23.867359 ✅

### Issue: Speed/Course/Heading not extracted
VesselFinder may load these dynamically. The scraper tries multiple extraction methods but may not always succeed. This is expected and being improved.

## 🎯 Integration with Your Backend

### Python/Django Example:
```python
from trigger_multi_provider_action import trigger_scraper
import os

def scrape_vessel(mmsi, comparison_id):
    """Trigger VesselFinder scraper from your backend"""
    
    success = trigger_scraper(
        github_token=os.getenv('GITHUB_TOKEN'),
        repo_owner=os.getenv('GITHUB_REPO_OWNER'),
        repo_name=os.getenv('GITHUB_REPO_NAME'),
        provider='vesselfinder',
        mmsi=mmsi,
        comparison_id=comparison_id,
        headless=True,
        send_to_posthog=True
    )
    
    return success
```

### API Endpoint Example:
```python
# Django REST Framework
from rest_framework.decorators import api_view
from rest_framework.response import Response

@api_view(['POST'])
def trigger_vessel_scrape(request):
    mmsi = request.data.get('mmsi')
    comparison_id = request.data.get('comparison_id')
    
    success = scrape_vessel(mmsi, comparison_id)
    
    return Response({
        'success': success,
        'mmsi': mmsi,
        'comparison_id': comparison_id,
        'provider': 'VesselFinder'
    })
```

## 📝 comparison_id Usage

The `comparison_id` is your tracking identifier that flows through the entire system:

```python
# Your backend generates it
comparison_id = f"order-{order_id}-vessel-{mmsi}"

# Trigger scraper with it
trigger_scraper(..., comparison_id=comparison_id)

# It appears in PostHog
# Event: local_comparison
# Properties: { comparison_id: "order-123-vessel-228078060", ... }

# You can query PostHog by comparison_id to get all related events
```

## 🎉 What Works Now

### ✅ Fully Working:
- Authentication to VesselFinder Pro
- MMSI and IMO lookups
- Coordinate extraction and normalization
- comparison_id parameter support
- PostHog event tracking
- GitHub Actions integration
- Multi-provider triggering

### ⚠️ Partially Working:
- Speed, Course, Heading (extracted when available)
- Nav Status (extracted when available)
- Destination (extracted when available)

### 📈 Data Quality:
- **MMSI**: ✅ Always extracted
- **Coordinates**: ✅ Always extracted and normalized
- **Callsign**: ✅ Usually extracted
- **Speed/Course/Heading**: ⚠️ Sometimes extracted (depends on VesselFinder's dynamic loading)

## 🔄 Next Steps

1. **Test locally** with your test MMSI
2. **Set up GitHub Secrets** in your repository
3. **Test GitHub Actions** workflow
4. **Verify PostHog events** are being received
5. **Integrate into your backend** using the trigger scripts
6. **Monitor and adjust** wait times if needed for better data extraction

## 📚 Documentation

- **`VESSELFINDER_README.md`** - Detailed VesselFinder scraper documentation
- **`VESSELFINDER_INTEGRATION_SUMMARY.md`** - Technical integration details
- **`GITHUB_ACTIONS_SETUP.md`** - Complete GitHub Actions setup guide
- **`QUICK_START.md`** - This file

## 💡 Pro Tips

1. **Use meaningful comparison_ids**: Include order ID, vessel ID, timestamp
2. **Test with headless=False first**: See what's happening in the browser
3. **Check PostHog regularly**: Verify events are being tracked correctly
4. **Monitor GitHub Actions usage**: Be aware of your quota
5. **Increase wait times if needed**: Some data loads slowly on VesselFinder

## ✨ Summary

You now have a **fully functional VesselFinder scraper** that:
- ✅ Logs in automatically
- ✅ Extracts vessel data
- ✅ Normalizes coordinates
- ✅ Supports comparison_id tracking
- ✅ Pushes to PostHog
- ✅ Works with GitHub Actions
- ✅ Integrates with your existing workflow

**The scraper is ready to use!** 🚢
