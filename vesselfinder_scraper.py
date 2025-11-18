"""
VesselFinder scraper with authentication
Extracts vessel data from VesselFinder.com with login support
"""

import json
import time
import re
import os
import logging
from datetime import datetime
from typing import Dict, Any, Optional
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# PostHog integration
try:
    import posthog
    POSTHOG_AVAILABLE = True
except ImportError:
    POSTHOG_AVAILABLE = False
    print("PostHog not available. Install with: pip install posthog")

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class VesselFinderScraper:
    """
    Selenium-based scraper for VesselFinder with authentication
    """
    
    def __init__(self, headless: bool = False):
        self.headless = headless
        self.driver = None
        self.logged_in = False
        
        # Get credentials from environment
        self.email = os.getenv('VESSELFINDER_EMAIL')
        self.password = os.getenv('VESSELFINDER_PASSWORD')
        
        if not self.email or not self.password:
            raise ValueError("VesselFinder credentials not found in environment variables")
        
        # PostHog setup
        self.posthog_api_key = os.getenv('POSTHOG_API_KEY')
        self.posthog_host = os.getenv('POSTHOG_HOST', 'https://app.posthog.com')
        
        if POSTHOG_AVAILABLE and self.posthog_api_key:
            posthog.api_key = self.posthog_api_key
            posthog.host = self.posthog_host
            logger.info("PostHog initialized successfully")
        
        self.setup_driver()
    
    def setup_driver(self):
        """Setup Chrome driver with options"""
        options = Options()
        
        if self.headless:
            options.add_argument('--headless=new')
        
        # Anti-detection options
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--disable-blink-features=AutomationControlled')
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option('useAutomationExtension', False)
        
        # Enable performance logging for network requests
        options.set_capability('goog:loggingPrefs', {'performance': 'ALL', 'browser': 'ALL'})
        
        # Set user agent
        options.add_argument('--user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
        
        # Window size
        options.add_argument('--window-size=1920,1080')
        
        try:
            self.driver = webdriver.Chrome(options=options)
            
            # Execute script to remove webdriver property
            self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            
            logger.info("Chrome driver initialized successfully")
            
        except Exception as e:
            raise Exception(f"Failed to setup Chrome driver: {e}. Make sure ChromeDriver is installed.")
    
    def login(self):
        """Login to VesselFinder"""
        if self.logged_in:
            logger.info("Already logged in")
            return True
        
        try:
            logger.info("Navigating to VesselFinder login page...")
            self.driver.get("https://www.vesselfinder.com/login")
            
            # Wait for page to load
            time.sleep(3)
            
            # Wait for email input field
            logger.info("Waiting for login form...")
            email_input = WebDriverWait(self.driver, 15).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "input[type='email'], input[name='email'], input#email"))
            )
            
            # Find password field
            password_input = self.driver.find_element(By.CSS_SELECTOR, "input[type='password'], input[name='password'], input#password")
            
            # Enter credentials
            logger.info("Entering credentials...")
            email_input.clear()
            email_input.send_keys(self.email)
            time.sleep(1)
            
            password_input.clear()
            password_input.send_keys(self.password)
            time.sleep(1)
            
            # Find and click login button
            login_button = self.driver.find_element(By.CSS_SELECTOR, "button[type='submit'], input[type='submit'], button.btn-login")
            logger.info("Clicking login button...")
            login_button.click()
            
            # Wait for login to complete
            time.sleep(5)
            
            # Check if login was successful
            current_url = self.driver.current_url
            if 'login' not in current_url.lower():
                self.logged_in = True
                logger.info("Login successful!")
                return True
            else:
                logger.error("Login may have failed - still on login page")
                return False
                
        except Exception as e:
            logger.error(f"Error during login: {e}")
            return False
    
    def get_vessel_details(self, mmsi: str = None, imo: str = None, comparison_id: str = None) -> Dict[str, Any]:
        """
        Extract vessel details from VesselFinder
        
        Args:
            mmsi: Maritime Mobile Service Identity number
            imo: International Maritime Organization number
            comparison_id: Optional comparison ID for tracking
            
        Returns:
            Dictionary containing vessel details
        """
        if not self.driver:
            raise Exception("Driver not initialized")
        
        # Login first if not already logged in
        if not self.logged_in:
            if not self.login():
                raise Exception("Failed to login to VesselFinder")
        
        # Clean MMSI/IMO - remove quotes if present
        if mmsi:
            mmsi = str(mmsi).strip('"').strip()
        if imo:
            imo = str(imo).strip('"').strip()
        
        # Construct URL
        if mmsi:
            url = f"https://www.vesselfinder.com/pro/map#vessel-details?imo=0&mmsi={mmsi}"
            identifier = mmsi
            identifier_type = "MMSI"
        elif imo:
            url = f"https://www.vesselfinder.com/pro/map#vessel-details?imo={imo}&mmsi=0"
            identifier = imo
            identifier_type = "IMO"
        else:
            raise ValueError("Either MMSI or IMO must be provided")
        
        # Initialize vessel data
        vessel_data = {
            'provider': 'vesselfinder_data',
            'mmsi': mmsi,
            'imo': imo,
            'name': None,
            'callsign': None,
            'type': None,
            'lat': None,
            'lon': None,
            'speed': None,
            'course': None,
            'heading': None,
            'draught': None,
            'nav_status': None,
            'destination': None,
            'timestamp': None,
            'comparison_id': comparison_id,
            'data_source': 'vesselfinder_data',
            'length': None,
            'width': None,
            'flag': None,
            'built': None,
            'eta': None
        }
        
        try:
            logger.info(f"Loading vessel page for {identifier_type}: {identifier}")
            self.driver.get(url)
            
            # Wait for page to load
            time.sleep(8)
            
            # Wait for vessel details to load
            try:
                WebDriverWait(self.driver, 30).until(
                    EC.presence_of_element_located((By.TAG_NAME, "body"))
                )
                logger.info("Page body loaded, waiting for vessel data...")
                time.sleep(12)  # Additional wait for dynamic content and API calls
            except TimeoutException:
                logger.warning("Page load timeout")
            
            # Wait for map and vessel data to load
            logger.info("Waiting for map and vessel markers to load...")
            time.sleep(5)
            
            # Try to wait for vessel info panel
            try:
                WebDriverWait(self.driver, 10).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "div[class*='vessel'], div[class*='ship'], div[class*='info']"))
                )
                logger.info("Vessel info panel detected")
            except TimeoutException:
                logger.warning("Vessel info panel not detected, continuing anyway...")
            
            # Extract data from network requests (API calls) - PRIORITY
            logger.info("Extracting data from network requests...")
            self._extract_from_network_requests(vessel_data)
            
            # Try to extract from JavaScript variables
            logger.info("Extracting data from JavaScript variables...")
            self._extract_from_javascript(vessel_data)
            
            # Extract data from page elements
            logger.info("Extracting data from page elements...")
            self._extract_from_page_elements(vessel_data)
            
            # Extract from page source
            logger.info("Extracting data from page source...")
            page_source = self.driver.page_source
            self._extract_from_html(page_source, vessel_data)
            
            # Send event to PostHog if available
            if POSTHOG_AVAILABLE and self.posthog_api_key:
                posthog.capture(
                    distinct_id=f"vesselfinder_{identifier}",
                    event='vessel_data_scraped',
                    properties={
                        'provider': 'vesselfinder_data',
                        'identifier_type': identifier_type,
                        'identifier': identifier,
                        'success': True
                    }
                )
            
            logger.info(f"Successfully extracted vessel data for {identifier_type}: {identifier}")
            
            # Send to PostHog if available and comparison_id provided
            if comparison_id and POSTHOG_AVAILABLE and self.posthog_api_key:
                self._send_to_posthog(vessel_data, comparison_id)
            
            return vessel_data
            
        except Exception as e:
            logger.error(f"Error scraping vessel data: {str(e)}")
            
            # Send error event to PostHog
            if POSTHOG_AVAILABLE and self.posthog_api_key:
                posthog.capture(
                    distinct_id=f"vesselfinder_{identifier}",
                    event='vessel_data_scrape_failed',
                    properties={
                        'provider': 'vesselfinder_data',
                        'identifier_type': identifier_type,
                        'identifier': identifier,
                        'error': str(e)
                    }
                )
            
            raise Exception(f"Error scraping vessel data: {str(e)}")
    
    def _extract_from_network_requests(self, vessel_data: Dict[str, Any]):
        """Extract data from network requests captured in browser logs"""
        try:
            logs = self.driver.get_log('performance')
            
            for log in logs:
                try:
                    log_message = json.loads(log['message'])
                    message = log_message.get('message', {})
                    method = message.get('method', '')
                    
                    # Look for network response
                    if method == 'Network.responseReceived':
                        response = message.get('params', {}).get('response', {})
                        url = response.get('url', '')
                        
                        # Look for vessel API endpoints
                        if any(keyword in url.lower() for keyword in ['vessel', 'ship', 'ais', 'position', 'track']):
                            request_id = message.get('params', {}).get('requestId')
                            
                            if request_id:
                                try:
                                    # Get response body
                                    response_body = self.driver.execute_cdp_cmd('Network.getResponseBody', {'requestId': request_id})
                                    body = response_body.get('body', '')
                                    
                                    if body:
                                        try:
                                            data = json.loads(body)
                                            self._parse_api_response(data, vessel_data)
                                        except json.JSONDecodeError:
                                            pass
                                except:
                                    pass
                
                except Exception as e:
                    continue
                    
        except Exception as e:
            logger.warning(f"Error extracting from network requests: {e}")
    
    def _parse_api_response(self, data: Any, vessel_data: Dict[str, Any]):
        """Parse API response data"""
        try:
            if isinstance(data, dict):
                # Extract common fields
                for key, value in data.items():
                    key_lower = key.lower()
                    
                    if 'mmsi' in key_lower and not vessel_data['mmsi']:
                        vessel_data['mmsi'] = str(value)
                    elif 'imo' in key_lower and not vessel_data['imo']:
                        vessel_data['imo'] = str(value)
                    elif 'name' in key_lower and not vessel_data['name']:
                        vessel_data['name'] = str(value)
                    elif 'callsign' in key_lower and not vessel_data['callsign']:
                        vessel_data['callsign'] = str(value)
                    elif 'type' in key_lower and not vessel_data['type']:
                        vessel_data['type'] = str(value)
                    elif key_lower in ['lat', 'latitude'] and not vessel_data['lat']:
                        try:
                            lat_val = float(value) if value else None
                            # Normalize if value is too large (likely in micro-degrees)
                            if lat_val and abs(lat_val) > 180:
                                lat_val = lat_val / 1000000.0
                            vessel_data['lat'] = lat_val
                        except:
                            pass
                    elif key_lower in ['lon', 'lng', 'longitude'] and not vessel_data['lon']:
                        try:
                            lon_val = float(value) if value else None
                            # Normalize if value is too large (likely in micro-degrees)
                            if lon_val and abs(lon_val) > 180:
                                lon_val = lon_val / 1000000.0
                            vessel_data['lon'] = lon_val
                        except:
                            pass
                    elif 'speed' in key_lower and not vessel_data['speed']:
                        vessel_data['speed'] = float(value) if value else None
                    elif 'course' in key_lower and not vessel_data['course']:
                        vessel_data['course'] = float(value) if value else None
                    elif 'heading' in key_lower and not vessel_data['heading']:
                        vessel_data['heading'] = float(value) if value else None
                    elif 'draught' in key_lower and not vessel_data['draught']:
                        vessel_data['draught'] = float(value) if value else None
                    elif 'destination' in key_lower and not vessel_data['destination']:
                        vessel_data['destination'] = str(value)
                    elif 'status' in key_lower and not vessel_data['nav_status']:
                        vessel_data['nav_status'] = str(value)
                    elif 'flag' in key_lower and not vessel_data['flag']:
                        vessel_data['flag'] = str(value)
                    elif 'length' in key_lower and not vessel_data['length']:
                        vessel_data['length'] = float(value) if value else None
                    elif 'width' in key_lower and not vessel_data['width']:
                        vessel_data['width'] = float(value) if value else None
                    elif 'built' in key_lower and not vessel_data['built']:
                        vessel_data['built'] = str(value)
                    elif 'eta' in key_lower and not vessel_data['eta']:
                        vessel_data['eta'] = str(value)
                
                # Recursively search nested objects
                for value in data.values():
                    if isinstance(value, (dict, list)):
                        self._parse_api_response(value, vessel_data)
            
            elif isinstance(data, list):
                for item in data:
                    self._parse_api_response(item, vessel_data)
                    
        except Exception as e:
            logger.warning(f"Error parsing API response: {e}")
    
    def _extract_from_page_elements(self, vessel_data: Dict[str, Any]):
        """Extract data from visible page elements"""
        try:
            # Get all text content
            body_text = self.driver.find_element(By.TAG_NAME, 'body').text
            
            # Extract vessel name from title or headings
            try:
                # Try multiple selectors for vessel name
                name_selectors = [
                    'h1',
                    'h2',
                    '.vessel-name',
                    '.ship-name',
                    'div[class*="vessel"] h1',
                    'div[class*="ship"] h1',
                    'span[class*="name"]'
                ]
                
                for selector in name_selectors:
                    try:
                        elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                        for element in elements:
                            text = element.text.strip()
                            if text and len(text) > 2 and text.lower() not in ['vesselfinder', 'vessel finder', 'map']:
                                if not vessel_data['name'] or vessel_data['name'] == 'VesselFinder':
                                    vessel_data['name'] = text
                                    logger.info(f"Found vessel name from {selector}: {text}")
                                    break
                    except:
                        continue
                    if vessel_data['name'] and vessel_data['name'] != 'VesselFinder':
                        break
            except Exception as e:
                logger.warning(f"Error extracting vessel name: {e}")
            
            # Try to extract from all visible text using regex patterns
            try:
                # Look for speed in various formats
                if not vessel_data['speed']:
                    speed_patterns = [
                        r'speed[:\s]+(\d+\.?\d*)\s*(?:kn|knots|kt)?',
                        r'sog[:\s]+(\d+\.?\d*)',
                        r'(\d+\.?\d*)\s*(?:kn|knots)',
                    ]
                    for pattern in speed_patterns:
                        matches = re.findall(pattern, body_text, re.IGNORECASE)
                        if matches:
                            try:
                                vessel_data['speed'] = float(matches[0])
                                logger.info(f"Found speed from text: {vessel_data['speed']}")
                                break
                            except:
                                pass
                
                # Look for course
                if not vessel_data['course']:
                    course_patterns = [
                        r'course[:\s]+(\d+\.?\d*)\s*°?',
                        r'cog[:\s]+(\d+\.?\d*)',
                    ]
                    for pattern in course_patterns:
                        matches = re.findall(pattern, body_text, re.IGNORECASE)
                        if matches:
                            try:
                                vessel_data['course'] = float(matches[0])
                                logger.info(f"Found course from text: {vessel_data['course']}")
                                break
                            except:
                                pass
                
                # Look for heading
                if not vessel_data['heading']:
                    heading_patterns = [
                        r'heading[:\s]+(\d+\.?\d*)\s*°?',
                        r'hdg[:\s]+(\d+\.?\d*)',
                    ]
                    for pattern in heading_patterns:
                        matches = re.findall(pattern, body_text, re.IGNORECASE)
                        if matches:
                            try:
                                vessel_data['heading'] = float(matches[0])
                                logger.info(f"Found heading from text: {vessel_data['heading']}")
                                break
                            except:
                                pass
            except Exception as e:
                logger.warning(f"Error extracting from body text: {e}")
            
            # Look for data in tables or lists
            try:
                # Find all text that might contain vessel information
                all_elements = self.driver.find_elements(By.XPATH, "//*[contains(text(), ':')]")
                
                for element in all_elements:
                    text = element.text.strip()
                    if ':' in text:
                        parts = text.split(':', 1)
                        if len(parts) == 2:
                            label = parts[0].strip().lower()
                            value = parts[1].strip()
                            
                            if 'mmsi' in label and not vessel_data['mmsi']:
                                vessel_data['mmsi'] = value
                            elif 'imo' in label and not vessel_data['imo']:
                                vessel_data['imo'] = value
                            elif 'call sign' in label and not vessel_data['callsign']:
                                vessel_data['callsign'] = value
                            elif 'type' in label and not vessel_data['type']:
                                vessel_data['type'] = value
                            elif 'speed' in label and not vessel_data['speed']:
                                try:
                                    vessel_data['speed'] = float(re.findall(r'\d+\.?\d*', value)[0])
                                except:
                                    pass
                            elif 'course' in label and not vessel_data['course']:
                                try:
                                    vessel_data['course'] = float(re.findall(r'\d+\.?\d*', value)[0])
                                except:
                                    pass
                            elif 'heading' in label and not vessel_data['heading']:
                                try:
                                    vessel_data['heading'] = float(re.findall(r'\d+\.?\d*', value)[0])
                                except:
                                    pass
                            elif 'draught' in label and not vessel_data['draught']:
                                try:
                                    vessel_data['draught'] = float(re.findall(r'\d+\.?\d*', value)[0])
                                except:
                                    pass
                            elif 'destination' in label and not vessel_data['destination']:
                                vessel_data['destination'] = value
                            elif 'status' in label and not vessel_data['nav_status']:
                                vessel_data['nav_status'] = value
                            elif 'flag' in label and not vessel_data['flag']:
                                vessel_data['flag'] = value
                            elif 'length' in label and not vessel_data['length']:
                                try:
                                    vessel_data['length'] = float(re.findall(r'\d+\.?\d*', value)[0])
                                except:
                                    pass
                            elif 'width' in label or 'beam' in label and not vessel_data['width']:
                                try:
                                    vessel_data['width'] = float(re.findall(r'\d+\.?\d*', value)[0])
                                except:
                                    pass
                            elif 'built' in label or 'year' in label and not vessel_data['built']:
                                vessel_data['built'] = value
                            elif 'eta' in label and not vessel_data['eta']:
                                vessel_data['eta'] = value
            except Exception as e:
                logger.warning(f"Error extracting from page elements: {e}")
                
        except Exception as e:
            logger.warning(f"Error extracting from page elements: {e}")
    
    def _extract_from_html(self, html: str, vessel_data: Dict[str, Any]):
        """Extract data from HTML source"""
        try:
            # Look for JSON data in script tags
            json_pattern = r'<script[^>]*>(.*?)</script>'
            scripts = re.findall(json_pattern, html, re.DOTALL)
            
            for script in scripts:
                # Look for JSON objects
                try:
                    # Find potential JSON objects
                    json_matches = re.findall(r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}', script)
                    
                    for json_str in json_matches:
                        try:
                            data = json.loads(json_str)
                            self._parse_api_response(data, vessel_data)
                        except:
                            pass
                except:
                    pass
            
            # Look for coordinates in various formats
            if not vessel_data['lat'] or not vessel_data['lon']:
                # Pattern for coordinates
                coord_patterns = [
                    r'lat["\']?\s*[:=]\s*([+-]?\d+\.?\d*)',
                    r'latitude["\']?\s*[:=]\s*([+-]?\d+\.?\d*)',
                    r'lon["\']?\s*[:=]\s*([+-]?\d+\.?\d*)',
                    r'lng["\']?\s*[:=]\s*([+-]?\d+\.?\d*)',
                    r'longitude["\']?\s*[:=]\s*([+-]?\d+\.?\d*)',
                ]
                
                for pattern in coord_patterns:
                    matches = re.findall(pattern, html, re.IGNORECASE)
                    if matches:
                        value = float(matches[0])
                        if 'lat' in pattern.lower() and not vessel_data['lat']:
                            vessel_data['lat'] = value
                        elif ('lon' in pattern.lower() or 'lng' in pattern.lower()) and not vessel_data['lon']:
                            vessel_data['lon'] = value
                            
        except Exception as e:
            logger.warning(f"Error extracting from HTML: {e}")
    
    def _extract_from_javascript(self, vessel_data: Dict[str, Any]):
        """Extract data from JavaScript variables in the page"""
        try:
            # Try to execute JavaScript to get vessel data
            scripts_to_try = [
                # Try to get vessel object
                "return window.vessel || window.vesselData || window.ship || null;",
                # Try to get map markers
                "return window.markers || window.vesselMarkers || null;",
                # Try to get AIS data
                "return window.aisData || window.ais || null;",
            ]
            
            for script in scripts_to_try:
                try:
                    result = self.driver.execute_script(script)
                    if result:
                        logger.info(f"Found JavaScript data: {type(result)}")
                        self._parse_api_response(result, vessel_data)
                except Exception as e:
                    logger.debug(f"Script execution failed: {e}")
                    continue
            
            # Try to extract specific fields from window object
            field_scripts = {
                'speed': "return window.vesselSpeed || window.speed || null;",
                'course': "return window.vesselCourse || window.course || null;",
                'heading': "return window.vesselHeading || window.heading || null;",
                'lat': "return window.vesselLat || window.lat || window.latitude || null;",
                'lon': "return window.vesselLon || window.lon || window.lng || window.longitude || null;",
            }
            
            for field, script in field_scripts.items():
                if not vessel_data.get(field):
                    try:
                        result = self.driver.execute_script(script)
                        if result is not None:
                            vessel_data[field] = float(result) if isinstance(result, (int, float, str)) else result
                            logger.info(f"Extracted {field} from JavaScript: {result}")
                    except:
                        pass
                        
        except Exception as e:
            logger.warning(f"Error extracting from JavaScript: {e}")
    
    def _send_to_posthog(self, vessel_data: Dict[str, Any], comparison_id: str):
        """Send vessel data to PostHog"""
        try:
            import posthog
            from datetime import datetime
            
            timestamp_dt = datetime.now()
            
            # Prepare PostHog properties matching the format from github_action_scraper
            posthog_properties = {
                "provider": "vesselfinder_data",
                "mmsi": str(vessel_data.get("mmsi", "")),
                "name": vessel_data.get("name"),
                "callsign": vessel_data.get("callsign"),
                "type": vessel_data.get("type"),
                "lat": float(vessel_data.get("lat")) if vessel_data.get("lat") else None,
                "lon": float(vessel_data.get("lon")) if vessel_data.get("lon") else None,
                "speed": float(vessel_data.get("speed")) if vessel_data.get("speed") else None,
                "course": float(vessel_data.get("course")) if vessel_data.get("course") else None,
                "heading": float(vessel_data.get("heading")) if vessel_data.get("heading") else None,
                "draught": float(vessel_data.get("draught")) if vessel_data.get("draught") else None,
                "nav_status": vessel_data.get("nav_status"),
                "destination": vessel_data.get("destination", ""),
                "timestamp": timestamp_dt.isoformat(),
                "imo": vessel_data.get("imo"),
                "comparison_id": comparison_id,
                "data_source": "vesselfinder_data"
            }
            
            logger.info(f"Sending VesselFinder data to PostHog with comparison_id: {comparison_id}")
            logger.info(f"PostHog properties: {posthog_properties}")
            
            # Send to PostHog
            posthog.capture(
                distinct_id="vesselfinder_scraper",
                event="local_comparison",
                properties=posthog_properties,
                timestamp=timestamp_dt
            )
            
            logger.info(f"Successfully sent VesselFinder data to PostHog for MMSI: {vessel_data.get('mmsi')}")
            
        except Exception as e:
            logger.error(f"Error sending VesselFinder data to PostHog: {e}")
    
    def close(self):
        """Close the browser"""
        if self.driver:
            self.driver.quit()
            logger.info("Browser closed")
    
    def __enter__(self):
        """Context manager entry"""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.close()


def get_vessel_data(mmsi: str = None, imo: str = None, headless: bool = False, comparison_id: str = None) -> Dict[str, Any]:
    """
    Convenience function to get vessel data from VesselFinder
    
    Args:
        mmsi: Maritime Mobile Service Identity number
        imo: International Maritime Organization number
        headless: Run browser in headless mode
        comparison_id: Optional comparison ID for tracking
        
    Returns:
        Dictionary containing vessel details
    """
    with VesselFinderScraper(headless=headless) as scraper:
        return scraper.get_vessel_details(mmsi=mmsi, imo=imo, comparison_id=comparison_id)


if __name__ == "__main__":
    # Example usage
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python vesselfinder_scraper.py <MMSI or IMO>")
        print("Example: python vesselfinder_scraper.py 228078060")
        sys.exit(1)
    
    identifier = sys.argv[1]
    
    # Determine if it's MMSI or IMO (IMO is usually 7 digits, MMSI is 9 digits)
    if len(identifier) == 7:
        vessel_data = get_vessel_data(imo=identifier, headless=False)
    else:
        vessel_data = get_vessel_data(mmsi=identifier, headless=False)
    
    print("\n" + "="*50)
    print("VESSEL DATA")
    print("="*50)
    print(json.dumps(vessel_data, indent=2))
