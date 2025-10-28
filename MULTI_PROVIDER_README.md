# 🚢 Multi-Provider Marine Traffic Scraper with PostHog Integration

This enhanced GitHub Actions workflow can fetch data from **3 different providers** and send all data to PostHog for comparison analysis.

## 📊 **Supported Data Sources:**

### 1. **MarineTraffic** (Selenium Scraper)
- ✅ **Web Scraping**: Extracts real-time position data from MarineTraffic website
- ✅ **Network Interception**: Captures API calls for accurate coordinates
- ✅ **Data**: Ship name, position, speed, course, draught, navigation status

### 2. **Datadocked API**
- ✅ **REST API**: Direct API integration with Datadocked
- ✅ **Authentication**: Uses API key authentication
- ✅ **Data**: Vessel location and details

### 3. **Datadocked Satellite API**
- ✅ **Satellite Data**: Satellite-based vessel tracking
- ✅ **Separate Token**: Different API key for satellite data
- ✅ **Data**: Satellite-derived position information

## 🔧 **GitHub Secrets Setup:**

Add these secrets to your GitHub repository:

| Secret Name | Description | Required |
|-------------|-------------|----------|
| `POSTHOG_API_KEY` | Your PostHog API key | ✅ Yes |
| `POSTHOG_HOST` | PostHog host URL | Optional |
| `DATADOCKED_BASE_URL` | Base URL for Datadocked APIs | ✅ For Datadocked |
| `DATADOCKED_API_KEY` | API key for regular Datadocked | ✅ For Datadocked |
| `DATADOCKED_SATELLITE_API_KEY` | API key for satellite data | ✅ For Satellite |

## 🎯 **Usage Examples:**

### **Example 1: MarineTraffic Only**
```bash
curl -X POST \
  -H "Authorization: Bearer YOUR_GITHUB_TOKEN" \
  -H "Accept: application/vnd.github+json" \
  https://api.github.com/repos/USER/REPO/dispatches \
  -d '{
    "event_type": "scrape-marine-traffic",
    "client_payload": {
      "mmsi": "677350000",
      "comparison_id": "test-001",
      "headless": true,
      "send_to_posthog": true
    }
  }'
```

### **Example 2: All Three Data Sources**
```bash
curl -X POST \
  -H "Authorization: Bearer YOUR_GITHUB_TOKEN" \
  -H "Accept: application/vnd.github+json" \
  https://api.github.com/repos/USER/REPO/dispatches \
  -d '{
    "event_type": "scrape-marine-traffic",
    "client_payload": {
      "mmsi": "677350000",
      "comparison_id": "comparison-001",
      "headless": true,
      "send_to_posthog": true,
      "fetch_datadocked": true,
      "fetch_datadocked_satellite": true
    }
  }'
```

## 📈 **PostHog Event Structure:**

All three data sources are sent to PostHog with the **same event name** and **comparison_id**:

```json
{
  "event": "local_comparison",
  "distinct_id": "selenium_scraper",
  "properties": {
    "provider": "MarineTraffic" | "datadocked" | "datadocked_satellite",
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
    "timestamp": "2025-10-28T10:00:00.000Z",
    "imo": "8975213",
    "comparison_id": "comparison-001",
    "data_source": "MarineTraffic" | "datadocked" | "datadocked_satellite"
  }
}
```

## 🔄 **Data Flow:**

1. **Trigger**: API call to GitHub Actions
2. **Extract**: Get MMSI, comparison_id, and provider flags
3. **Fetch**: 
   - MarineTraffic (always)
   - Datadocked (if `fetch_datadocked: true`)
   - Datadocked Satellite (if `fetch_datadocked_satellite: true`)
4. **Process**: Format all data with consistent schema
5. **Send**: Push all available data to PostHog with same `comparison_id`
6. **Log**: Comprehensive logging for debugging

## 🔍 **API Response Examples:**

### **MarineTraffic Data:**
```json
{
  "provider": "MarineTraffic",
  "mmsi": "677350000",
  "name": "PRESIDO",
  "lat": 4.808785,
  "lon": 7.0591569,
  "speed": 0.0,
  "course": 265.0,
  "draught": 2.5,
  "nav_status": "Stopped",
  "data_source": "MarineTraffic"
}
```

### **Datadocked Data:**
```json
{
  "detail": {
    "mmsi": "677350000",
    "name": "PRESIDO",
    "typeSpecific": "Crew Boat",
    "latitude": 4.8087,
    "longitude": 7.0591,
    "speed": 0.2,
    "navigationalStatus": "Underway"
  }
}
```

## ⚡ **Performance Notes:**

- **MarineTraffic**: ~30-60 seconds (web scraping)
- **Datadocked**: ~2-5 seconds (API call)
- **Satellite**: ~2-5 seconds (API call)
- **Parallel**: APIs called sequentially after MarineTraffic completes

## 🎉 **Benefits:**

1. **Data Comparison**: Compare position data from 3 different sources
2. **Accuracy Validation**: Cross-verify vessel positions
3. **Historical Tracking**: All data tagged with same `comparison_id`
4. **Flexible Triggering**: Choose which providers to use per request
5. **Centralized Logging**: Single PostHog event for easy analysis

Perfect for vessel tracking validation, data accuracy studies, and multi-source position comparison! 🚢📊
