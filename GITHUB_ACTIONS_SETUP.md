# GitHub Actions Setup Guide

## Overview

This project includes GitHub Actions workflows for automated vessel data scraping from multiple providers:
- **MarineTraffic** - Existing workflow
- **VesselFinder** - New workflow with authentication

## 📋 Prerequisites

### 1. GitHub Repository Secrets

You need to configure the following secrets in your GitHub repository:

**Settings → Secrets and variables → Actions → New repository secret**

#### Required for VesselFinder:
```
VESSELFINDER_EMAIL=your_vesselfinder_email
VESSELFINDER_PASSWORD=your_vesselfinder_password
```

#### Required for PostHog (both providers):
```
POSTHOG_API_KEY=your_posthog_api_key
POSTHOG_HOST=https://app.posthog.com
```

#### Required for MarineTraffic (if using Datadocked):
```
DATADOCKED_BASE_URL=your_datadocked_url
DATADOCKED_API_KEY=your_datadocked_key
DATADOCKED_SATELLITE_API_KEY=your_satellite_key
```

### 2. GitHub Personal Access Token

For triggering workflows via API, you need a GitHub Personal Access Token with `repo` scope:

1. Go to GitHub Settings → Developer settings → Personal access tokens → Tokens (classic)
2. Generate new token with `repo` scope
3. Save the token securely

## 🚀 Workflows

### 1. MarineTraffic Scraper
**File**: `.github/workflows/marine-traffic-scraper.yml`

**Trigger Event**: `scrape-marine-traffic`

**Features**:
- Scrapes MarineTraffic data
- Optional Datadocked API integration
- PostHog event tracking
- comparison_id support

### 2. VesselFinder Scraper (NEW)
**File**: `.github/workflows/vesselfinder-scraper.yml`

**Trigger Event**: `scrape-vesselfinder`

**Features**:
- Scrapes VesselFinder with authentication
- Supports both MMSI and IMO lookups
- PostHog event tracking
- comparison_id support
- Coordinate normalization

## 🎯 Triggering Workflows

### Option 1: Manual Trigger (GitHub UI)

1. Go to your repository on GitHub
2. Click **Actions** tab
3. Select the workflow (MarineTraffic or VesselFinder)
4. Click **Run workflow**
5. Fill in the parameters:
   - MMSI or IMO
   - comparison_id (optional)
   - Other options

### Option 2: API Trigger (Programmatic)

#### Using Python Scripts

##### Trigger VesselFinder Only:
```bash
python3 trigger_vesselfinder_action.py
```

##### Trigger MarineTraffic Only:
```bash
python3 trigger_github_action.py
```

##### Trigger Both Providers:
```bash
# Set environment variables
export GITHUB_TOKEN=your_github_token
export GITHUB_REPO_OWNER=your_username
export GITHUB_REPO_NAME=marine-traffic-scrapping

# Trigger all providers
python3 trigger_multi_provider_action.py \
  --provider all \
  --mmsi 228078060 \
  --comparison-id test-123

# Or trigger specific provider
python3 trigger_multi_provider_action.py \
  --provider vesselfinder \
  --mmsi 228078060 \
  --comparison-id test-123
```

#### Using curl:

##### VesselFinder:
```bash
curl -X POST \
  -H "Authorization: token YOUR_GITHUB_TOKEN" \
  -H "Accept: application/vnd.github.v3+json" \
  https://api.github.com/repos/YOUR_USERNAME/YOUR_REPO/dispatches \
  -d '{
    "event_type": "scrape-vesselfinder",
    "client_payload": {
      "mmsi": "228078060",
      "comparison_id": "test-123",
      "headless": true,
      "send_to_posthog": true
    }
  }'
```

##### MarineTraffic:
```bash
curl -X POST \
  -H "Authorization: token YOUR_GITHUB_TOKEN" \
  -H "Accept: application/vnd.github.v3+json" \
  https://api.github.com/repos/YOUR_USERNAME/YOUR_REPO/dispatches \
  -d '{
    "event_type": "scrape-marine-traffic",
    "client_payload": {
      "mmsi": "228078060",
      "comparison_id": "test-123",
      "headless": true,
      "send_to_posthog": true
    }
  }'
```

### Option 3: From Your Backend

#### Python Example:
```python
from trigger_multi_provider_action import trigger_scraper

# Trigger VesselFinder
trigger_scraper(
    github_token="your_github_token",
    repo_owner="your_username",
    repo_name="marine-traffic-scrapping",
    provider="vesselfinder",
    mmsi="228078060",
    comparison_id="backend-trigger-123",
    headless=True,
    send_to_posthog=True
)
```

#### Django Integration Example:
```python
# In your Django view or API endpoint
from trigger_multi_provider_action import trigger_all_providers
import os

def trigger_vessel_scrape(request):
    mmsi = request.POST.get('mmsi')
    comparison_id = request.POST.get('comparison_id')
    
    results = trigger_all_providers(
        github_token=os.getenv('GITHUB_TOKEN'),
        repo_owner=os.getenv('GITHUB_REPO_OWNER'),
        repo_name=os.getenv('GITHUB_REPO_NAME'),
        mmsi=mmsi,
        comparison_id=comparison_id,
        headless=True,
        send_to_posthog=True
    )
    
    return JsonResponse(results)
```

## 📊 Workflow Parameters

### VesselFinder Workflow

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `mmsi` | string | No* | - | Ship MMSI number |
| `imo` | string | No* | - | Ship IMO number |
| `comparison_id` | string | No | "" | Comparison ID for PostHog |
| `headless` | boolean | No | true | Run browser in headless mode |
| `send_to_posthog` | boolean | No | true | Send data to PostHog |

*Either `mmsi` or `imo` must be provided

### MarineTraffic Workflow

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `mmsi` | string | Yes | - | Ship MMSI number |
| `comparison_id` | string | No | "" | Comparison ID for PostHog |
| `headless` | boolean | No | true | Run browser in headless mode |
| `send_to_posthog` | boolean | No | true | Send data to PostHog |
| `fetch_datadocked` | boolean | No | false | Fetch from Datadocked API |
| `fetch_datadocked_satellite` | boolean | No | false | Fetch from Datadocked Satellite |

## 🔍 Monitoring Workflows

### View Workflow Runs:
1. Go to **Actions** tab in your repository
2. Click on a workflow run to see details
3. View logs for each step

### Check PostHog Events:
1. Go to your PostHog dashboard
2. Filter events by:
   - Event name: `local_comparison`
   - Property: `provider` = "VesselFinder" or "MarineTraffic"
   - Property: `comparison_id` = your comparison ID

### Download Logs on Failure:
- Logs are automatically uploaded as artifacts when a workflow fails
- Go to the failed workflow run → Artifacts section
- Download `vesselfinder-scraper-logs` or `scraper-logs`

## 🔧 Troubleshooting

### Workflow Not Triggering

**Check:**
1. GitHub token has `repo` scope
2. Repository owner and name are correct
3. Event type matches workflow configuration
4. Check Actions tab for any error messages

### VesselFinder Login Fails

**Check:**
1. `VESSELFINDER_EMAIL` and `VESSELFINDER_PASSWORD` secrets are set correctly
2. VesselFinder account is active
3. No CAPTCHA or additional verification required

### PostHog Events Not Appearing

**Check:**
1. `POSTHOG_API_KEY` is set correctly
2. `comparison_id` is provided
3. `send_to_posthog` is set to `true`
4. Check PostHog project settings

### ChromeDriver Issues

**The workflow automatically:**
- Installs Chrome stable
- Matches ChromeDriver version to Chrome version
- Falls back to known stable version if matching fails

**If issues persist:**
- Check workflow logs for ChromeDriver installation step
- Verify Chrome and ChromeDriver versions match

## 📝 comparison_id Flow

The `comparison_id` parameter flows through the entire system:

```
Backend/Trigger Script
    ↓
GitHub Actions Workflow
    ↓
Scraper Script (vesselfinder_action_scraper.py)
    ↓
VesselFinder Scraper (vesselfinder_scraper.py)
    ↓
PostHog Event (local_comparison)
```

### Example Flow:
```python
# 1. Trigger from backend
trigger_scraper(
    ...,
    comparison_id="order-12345-vessel-check"  # ← Your tracking ID
)

# 2. GitHub Action receives it
# client_payload.comparison_id = "order-12345-vessel-check"

# 3. Scraper uses it
vessel_data = get_vessel_data(
    mmsi="228078060",
    comparison_id="order-12345-vessel-check"  # ← Passed through
)

# 4. PostHog receives it
{
  "event": "local_comparison",
  "properties": {
    "comparison_id": "order-12345-vessel-check",  # ← Tracked
    "provider": "VesselFinder",
    ...
  }
}
```

## 🎯 Best Practices

### 1. Use Meaningful comparison_ids
```python
# Good
comparison_id = f"order-{order_id}-vessel-{mmsi}-{timestamp}"

# Bad
comparison_id = "test123"
```

### 2. Error Handling
```python
try:
    result = trigger_scraper(...)
    if not result:
        # Handle failure
        log_error("Scraper trigger failed")
except Exception as e:
    # Handle exception
    log_error(f"Error: {e}")
```

### 3. Rate Limiting
- Don't trigger too many workflows simultaneously
- Add delays between triggers
- Monitor GitHub Actions usage

### 4. Security
- Never commit GitHub tokens
- Use environment variables
- Rotate tokens regularly
- Use GitHub Secrets for sensitive data

## 📦 Files Reference

### Workflow Files:
- `.github/workflows/marine-traffic-scraper.yml` - MarineTraffic workflow
- `.github/workflows/vesselfinder-scraper.yml` - VesselFinder workflow (NEW)

### Trigger Scripts:
- `trigger_github_action.py` - MarineTraffic trigger
- `trigger_vesselfinder_action.py` - VesselFinder trigger (NEW)
- `trigger_multi_provider_action.py` - Multi-provider trigger (NEW)

### Scraper Scripts:
- `github_action_scraper.py` - MarineTraffic action scraper
- `vesselfinder_action_scraper.py` - VesselFinder action scraper (NEW)
- `vesselfinder_scraper.py` - VesselFinder core scraper (NEW)

## ✅ Quick Start Checklist

- [ ] Set up GitHub repository secrets (VESSELFINDER_EMAIL, VESSELFINDER_PASSWORD, POSTHOG_API_KEY)
- [ ] Generate GitHub Personal Access Token
- [ ] Set environment variables (GITHUB_TOKEN, GITHUB_REPO_OWNER, GITHUB_REPO_NAME)
- [ ] Test VesselFinder workflow manually from GitHub UI
- [ ] Test programmatic trigger with Python script
- [ ] Verify PostHog events are being received
- [ ] Integrate into your backend/application

## 🎉 Summary

You now have two fully functional GitHub Actions workflows:

1. **MarineTraffic Scraper** - Existing, unchanged
2. **VesselFinder Scraper** - New, with authentication and PostHog integration

Both workflows:
- ✅ Support `comparison_id` parameter
- ✅ Send events to PostHog
- ✅ Can be triggered via API or manually
- ✅ Include error handling and logging
- ✅ Work in headless mode for automation

The workflows are **ready to use** and will work with your existing comparison_id tracking system!
