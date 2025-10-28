# 🚀 GitHub Actions MarineTraffic Scraper Setup

This setup allows you to run the MarineTraffic Selenium scraper in GitHub Actions and automatically send the data to PostHog.

## 📋 Setup Instructions

### 1. Repository Setup

1. **Push your code to GitHub**:
   ```bash
   git init
   git add .
   git commit -m "Initial commit"
   git branch -M main
   git remote add origin https://github.com/YOUR_USERNAME/marine-traffic-scrapping.git
   git push -u origin main
   ```

### 2. GitHub Secrets Configuration

Go to your GitHub repository → Settings → Secrets and variables → Actions, and add these secrets:

**Required Secrets:**
- `POSTHOG_API_KEY`: Your PostHog API key
- `POSTHOG_HOST`: Your PostHog host (default: `https://app.posthog.com`)

**Optional Secrets (for backend triggering):**
- `GITHUB_TOKEN`: Personal access token for triggering workflows

### 3. PostHog Setup

1. Get your PostHog API key from your PostHog dashboard
2. Add it to GitHub Secrets as `POSTHOG_API_KEY`

### 4. Backend Integration

Add to your Django `settings.py`:
```python
# GitHub Actions configuration
GITHUB_TOKEN = os.getenv('GITHUB_TOKEN')
GITHUB_REPO_OWNER = os.getenv('GITHUB_REPO_OWNER', 'your-username')
GITHUB_REPO_NAME = os.getenv('GITHUB_REPO_NAME', 'marine-traffic-scrapping')
```

## 🎯 Usage

### Method 1: Manual Trigger (GitHub UI)

1. Go to your repository on GitHub
2. Click "Actions" tab
3. Select "MarineTraffic Selenium Scraper"
4. Click "Run workflow"
5. Enter parameters:
   - **MMSI**: Ship MMSI number (required)
   - **Comparison ID**: Optional ID for tracking
   - **Headless**: Run browser in headless mode (default: true)
   - **Send to PostHog**: Send data to PostHog (default: true)

### Method 2: API Trigger (From Your Backend)

**Using the Django integration:**

```python
# In your Django view or service
from .django_github_integration import MarineTrafficScraperTrigger

scraper_trigger = MarineTrafficScraperTrigger()
result = scraper_trigger.trigger_scraper(
    mmsi="677350000",
    comparison_id="comparison-123"
)

if result['success']:
    print("✅ Scraper triggered successfully!")
else:
    print(f"❌ Error: {result['message']}")
```

**Using the standalone script:**

```python
from trigger_github_action import trigger_marine_traffic_scraper

success = trigger_marine_traffic_scraper(
    github_token="your_github_token",
    repo_owner="your-username",
    repo_name="marine-traffic-scrapping",
    mmsi="677350000",
    comparison_id="comparison-123"
)
```

**Using curl:**

```bash
curl -X POST \
  -H "Authorization: token YOUR_GITHUB_TOKEN" \
  -H "Accept: application/vnd.github.v3+json" \
  -H "Content-Type: application/json" \
  -d '{
    "event_type": "scrape-marine-traffic",
    "client_payload": {
      "mmsi": "677350000",
      "comparison_id": "comparison-123",
      "headless": true,
      "send_to_posthog": true
    }
  }' \
  https://api.github.com/repos/YOUR_USERNAME/marine-traffic-scrapping/dispatches
```

## 📊 PostHog Data Format

The scraper sends data to PostHog with this structure:

```json
{
  "provider": "MarineTraffic",
  "mmsi": "677350000",
  "name": "PRESIDO",
  "callsign": "5NVFA",
  "type": "Crew Boat",
  "lat": 4.808785,
  "lon": 7.0591569,
  "speed": 0,
  "course": 265,
  "heading": null,
  "draught": 2.5,
  "nav_status": "Stopped",
  "destination": "",
  "timestamp": "2024-01-01T12:00:00.000Z",
  "imo": "8975213",
  "comparison_id": "comparison-123",
  "data_source": "selenium_scraper"
}
```

## 🔧 Workflow Features

- **Automatic Chrome/ChromeDriver installation**
- **Headless browser support**
- **Error handling and logging**
- **Artifact upload on failure**
- **PostHog integration**
- **Flexible triggering (manual + API)**

## 📝 Environment Variables

| Variable | Description | Required | Default |
|----------|-------------|----------|---------|
| `POSTHOG_API_KEY` | PostHog API key | Yes | - |
| `POSTHOG_HOST` | PostHog host URL | No | `https://app.posthog.com` |
| `GITHUB_TOKEN` | GitHub personal access token | No* | - |

*Required only for API triggering from backend

## 🚨 Troubleshooting

### Common Issues:

1. **ChromeDriver not found**
   - The workflow automatically installs ChromeDriver
   - Check the "Install system dependencies" step logs

2. **PostHog connection failed**
   - Verify `POSTHOG_API_KEY` is set correctly
   - Check PostHog host URL

3. **GitHub API trigger failed**
   - Verify `GITHUB_TOKEN` has `repo` scope
   - Check repository name and owner

4. **Scraping failed**
   - Check if MarineTraffic blocked the request
   - Review scraper logs in the workflow

### Debug Steps:

1. Check workflow logs in GitHub Actions
2. Look for error messages in the "Run MarineTraffic scraper" step
3. Download artifacts if the workflow fails
4. Test locally first with `python github_action_scraper.py --mmsi YOUR_MMSI`

## 🎉 Success Indicators

When everything works correctly, you should see:

1. ✅ GitHub Actions workflow completes successfully
2. ✅ PostHog receives the ship data
3. ✅ Logs show "Successfully sent data to PostHog"
4. ✅ Ship coordinates are extracted correctly

## 📈 Monitoring

Monitor your scraping in:
- **GitHub Actions**: Workflow run history
- **PostHog**: Event tracking and analytics
- **Logs**: Detailed execution information

Your MarineTraffic scraper is now ready for production use! 🚢📍
