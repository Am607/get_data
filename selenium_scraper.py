"""
Selenium-based scraper for MarineTraffic (alternative approach)
This approach uses a real browser to avoid detection
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


class SeleniumMarineTrafficScraper:
    """
    Selenium-based scraper for MarineTraffic
    Uses a real browser to avoid detection
    """
    
    def __init__(self, headless: bool = True):
        self.headless = headless
        self.driver = None
        self.posthog_api_key = os.getenv('POSTHOG_API_KEY')
        self.posthog_host = os.getenv('POSTHOG_HOST', 'https://app.posthog.com')
        
        # Initialize PostHog if available
        if POSTHOG_AVAILABLE and self.posthog_api_key:
            posthog.api_key = self.posthog_api_key
            posthog.host = self.posthog_host
            logger.info("PostHog initialized successfully")
        else:
            logger.warning("PostHog not initialized - missing API key or library")
        self.setup_driver()
    
    def setup_driver(self):
        """Setup Chrome driver with options"""
        options = Options()
        
        if self.headless:
            options.add_argument('--headless')
        
        # Anti-detection options
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--disable-blink-features=AutomationControlled')
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option('useAutomationExtension', False)
        
        # Enable logging to capture network requests
        options.add_experimental_option('useAutomationExtension', False)
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_argument('--enable-logging')
        options.add_argument('--log-level=0')
        options.set_capability('goog:loggingPrefs', {'performance': 'ALL'})
        
        # Set user agent
        options.add_argument('--user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
        
        try:
            self.driver = webdriver.Chrome(options=options)
            
            # Execute script to remove webdriver property
            self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            
        except Exception as e:
            raise Exception(f"Failed to setup Chrome driver: {e}. Make sure ChromeDriver is installed.")
    
    def get_ship_details(self, mmsi: str) -> Dict[str, Any]:
        """
        Extract ship details for a given MMSI using Selenium
        
        Args:
            mmsi: Maritime Mobile Service Identity number
            
        Returns:
            Dictionary containing ship details
        """
        if not self.driver:
            raise Exception("Driver not initialized")
        
        url = f"https://www.marinetraffic.com/en/ais/details/ships/mmsi:{mmsi}"
        
        # Initialize ship data
        ship_data = {
            'provider': 'MarineTraffic',
            'mmsi': mmsi,
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
            'imo': None,
            'comparison_id': None,
            'data_source': 'MarineTraffic'
        }
        
        try:
            print(f"Loading page for MMSI: {mmsi}")
            self.driver.get(url)
            
            # Wait for page to load
            time.sleep(5)
            
            # Wait for content to load
            try:
                WebDriverWait(self.driver, 15).until(
                    EC.presence_of_element_located((By.TAG_NAME, "body"))
                )
                # Wait a bit more for dynamic content
                time.sleep(3)
            except TimeoutException:
                print("Page load timeout")
            
            # Try to click any "Show more" or "Expand" buttons
            self._expand_content()
            
            # Scroll to load more content
            self._scroll_page()
            
            # Extract ship name from title or heading
            self._extract_ship_name(ship_data)
            
            # PRIORITY: Extract from network requests (API calls) FIRST
            # Wait a bit more for position API calls to be made
            time.sleep(5)
            self._extract_from_network_requests(ship_data)
            
            # Only extract from other sources if we don't have API data
            if not ship_data.get('_coordinates_from_api', False):
                # Try to extract from all visible text
                self._extract_from_all_text(ship_data)
                
                # Extract data from page elements
                self._extract_vessel_details(ship_data)
                self._extract_position_data(ship_data)
                self._extract_voyage_data(ship_data)
            
            # Extract from page source as fallback
            page_source = self.driver.page_source
            self._extract_from_html(page_source, ship_data)
            
            # Clean up internal flags before returning
            if '_coordinates_from_api' in ship_data:
                del ship_data['_coordinates_from_api']
            
            return ship_data
            
        except Exception as e:
            raise Exception(f"Error scraping ship data: {str(e)}")
    
    def _extract_ship_name(self, ship_data: Dict[str, Any]):
        """Extract ship name from page title or headings"""
        try:
            # Try different selectors for ship name
            selectors = [
                'h1',
                '.page-title',
                '.vessel-name',
                '.ship-name'
            ]
            
            for selector in selectors:
                try:
                    element = self.driver.find_element(By.CSS_SELECTOR, selector)
                    name = element.text.strip()
                    if name and name.lower() not in ['unknown', 'n/a', '-']:
                        ship_data['name'] = name
                        print(f"Found ship name: {name}")
                        break
                except NoSuchElementException:
                    continue
                    
        except Exception as e:
            print(f"Error extracting ship name: {e}")
    
    def _expand_content(self):
        """Try to click buttons that might expand content"""
        try:
            # Common button texts that might expand content
            button_texts = [
                'Show more', 'Show all', 'Expand', 'More details',
                'View more', 'See more', 'Full details'
            ]
            
            for text in button_texts:
                try:
                    buttons = self.driver.find_elements(By.XPATH, f"//button[contains(text(), '{text}')]")
                    for button in buttons:
                        if button.is_displayed():
                            button.click()
                            time.sleep(1)
                            print(f"Clicked '{text}' button")
                except:
                    continue
                    
            # Try clicking elements with common expand classes
            expand_selectors = [
                '.expand', '.show-more', '.toggle', '.accordion-toggle'
            ]
            
            for selector in expand_selectors:
                try:
                    elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    for element in elements:
                        if element.is_displayed():
                            element.click()
                            time.sleep(1)
                            print(f"Clicked expand element: {selector}")
                except:
                    continue
                    
        except Exception as e:
            print(f"Error expanding content: {e}")
    
    def _scroll_page(self):
        """Scroll the page to load more content"""
        try:
            # Scroll down to load any lazy-loaded content
            self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight/2);")
            time.sleep(2)
            self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(2)
            self.driver.execute_script("window.scrollTo(0, 0);")
            time.sleep(1)
            print("Scrolled page to load content")
            
            # Try to click on different tabs if they exist
            self._click_tabs()
            
        except Exception as e:
            print(f"Error scrolling page: {e}")
    
    def _click_tabs(self):
        """Try to click on different tabs to reveal more data"""
        try:
            tab_selectors = [
                'a[href*="tab"]', '.tab', '.nav-tab', '.tab-link',
                'button[role="tab"]', '[data-tab]'
            ]
            
            for selector in tab_selectors:
                try:
                    tabs = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    for tab in tabs:
                        if tab.is_displayed() and tab.is_enabled():
                            tab_text = tab.text.lower()
                            # Click on tabs that might have vessel info
                            if any(word in tab_text for word in ['general', 'details', 'info', 'vessel', 'ship', 'position', 'voyage']):
                                tab.click()
                                time.sleep(2)
                                print(f"Clicked tab: {tab.text}")
                                break
                except:
                    continue
                    
        except Exception as e:
            print(f"Error clicking tabs: {e}")
    
    def _extract_from_all_text(self, ship_data: Dict[str, Any]):
        """Extract data from all visible text on the page"""
        try:
            # Get all text from the page
            all_text = self.driver.find_element(By.TAG_NAME, 'body').text
            
            # Split into lines for better parsing
            lines = all_text.split('\n')
            
            for line in lines:
                line = line.strip()
                if not line:
                    continue
                
                # Look for key-value pairs in each line
                if ':' in line:
                    parts = line.split(':', 1)
                    if len(parts) == 2:
                        key = parts[0].strip().lower()
                        value = parts[1].strip()
                        
                        # Extract based on key patterns
                        if 'imo' in key and not ship_data['imo']:
                            imo_match = re.search(r'(\d{7})', value)
                            if imo_match:
                                ship_data['imo'] = imo_match.group(1)
                                print(f"Found IMO from text: {ship_data['imo']}")
                        
                        elif any(word in key for word in ['call', 'sign']) and not ship_data['callsign']:
                            if value and value.lower() not in ['unknown', 'n/a', '-', 'upgrade to unlock']:
                                ship_data['callsign'] = value
                                print(f"Found callsign from text: {value}")
                        
                        elif 'type' in key and not ship_data['type']:
                            if value and value.lower() not in ['unknown', 'n/a', '-', 'upgrade to unlock']:
                                ship_data['type'] = value
                                print(f"Found type from text: {value}")
                        
                        elif any(word in key for word in ['lat', 'latitude']) and not ship_data['lat']:
                            try:
                                lat_val = float(re.search(r'([+-]?\d+\.?\d*)', value).group(1))
                                ship_data['lat'] = lat_val
                                print(f"Found latitude from text: {lat_val}")
                            except (ValueError, AttributeError):
                                pass
                        
                        elif any(word in key for word in ['lon', 'longitude']) and not ship_data['lon']:
                            try:
                                lon_val = float(re.search(r'([+-]?\d+\.?\d*)', value).group(1))
                                ship_data['lon'] = lon_val
                                print(f"Found longitude from text: {lon_val}")
                            except (ValueError, AttributeError):
                                pass
                        
                        elif 'destination' in key and not ship_data['destination']:
                            if value and value.lower() not in ['unknown', 'n/a', '-', 'upgrade to unlock']:
                                ship_data['destination'] = value
                                print(f"Found destination from text: {value}")
                        
                        elif any(word in key for word in ['draught', 'draft']) and not ship_data['draught']:
                            try:
                                draught_val = float(re.search(r'([0-9.]+)', value).group(1))
                                ship_data['draught'] = draught_val
                                print(f"Found draught from text: {draught_val}")
                            except (ValueError, AttributeError):
                                pass
                
        except Exception as e:
            print(f"Error extracting from all text: {e}")
    
    def _extract_vessel_details(self, ship_data: Dict[str, Any]):
        """Extract vessel details from tables or sections"""
        try:
            # Look for tables with vessel information
            tables = self.driver.find_elements(By.TAG_NAME, 'table')
            
            for table in tables:
                rows = table.find_elements(By.TAG_NAME, 'tr')
                for row in rows:
                    cells = row.find_elements(By.TAG_NAME, 'td')
                    if len(cells) >= 2:
                        key = cells[0].text.strip().lower()
                        value = cells[1].text.strip()
                        
                        if 'imo' in key and not ship_data['imo']:
                            imo_match = re.search(r'(\d{7})', value)
                            if imo_match:
                                ship_data['imo'] = imo_match.group(1)
                                print(f"Found IMO: {ship_data['imo']}")
                        
                        elif 'call' in key and 'sign' in key and not ship_data['callsign']:
                            if value and value.lower() not in ['unknown', 'n/a', '-', '']:
                                ship_data['callsign'] = value
                                print(f"Found call sign: {value}")
                        
                        elif 'type' in key and not ship_data['type']:
                            if value and value.lower() not in ['unknown', 'n/a', '-', '']:
                                ship_data['type'] = value
                                print(f"Found type: {value}")
            
            # Try alternative selectors for vessel details
            self._extract_from_detail_sections(ship_data)
            self._extract_from_data_attributes(ship_data)
                                
        except Exception as e:
            print(f"Error extracting vessel details: {e}")
    
    def _extract_from_detail_sections(self, ship_data: Dict[str, Any]):
        """Extract data from detail sections and divs"""
        try:
            # Look for specific data in various containers
            selectors_to_try = [
                '.vessel-details',
                '.ship-details', 
                '.vessel-info',
                '.ship-info',
                '[data-vessel]',
                '[data-ship]'
            ]
            
            for selector in selectors_to_try:
                try:
                    elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    for element in elements:
                        text = element.text
                        self._parse_text_for_data(text, ship_data)
                except:
                    continue
                    
        except Exception as e:
            print(f"Error in detail sections: {e}")
    
    def _extract_from_data_attributes(self, ship_data: Dict[str, Any]):
        """Extract data from HTML data attributes"""
        try:
            # Look for elements with data attributes
            data_attributes = [
                'data-mmsi', 'data-imo', 'data-callsign', 'data-type',
                'data-lat', 'data-lon', 'data-speed', 'data-course'
            ]
            
            for attr in data_attributes:
                try:
                    elements = self.driver.find_elements(By.CSS_SELECTOR, f'[{attr}]')
                    for element in elements:
                        value = element.get_attribute(attr)
                        if value:
                            field_name = attr.replace('data-', '')
                            if field_name == 'lat' or field_name == 'lon':
                                try:
                                    ship_data[field_name] = float(value)
                                    print(f"Found {field_name} from data attribute: {value}")
                                except ValueError:
                                    pass
                            elif not ship_data.get(field_name):
                                ship_data[field_name] = value
                                print(f"Found {field_name} from data attribute: {value}")
                except:
                    continue
                    
        except Exception as e:
            print(f"Error in data attributes: {e}")
    
    def _parse_text_for_data(self, text: str, ship_data: Dict[str, Any]):
        """Parse text content for ship data"""
        try:
            # IMO pattern
            if not ship_data['imo']:
                imo_match = re.search(r'IMO[:\s]*(\d{7})', text, re.I)
                if imo_match:
                    ship_data['imo'] = imo_match.group(1)
                    print(f"Found IMO in text: {ship_data['imo']}")
            
            # Call sign pattern
            if not ship_data['callsign']:
                callsign_patterns = [
                    r'Call\s*Sign[:\s]*([A-Z0-9]+)',
                    r'Callsign[:\s]*([A-Z0-9]+)',
                    r'Call[:\s]*([A-Z0-9]{4,8})'
                ]
                for pattern in callsign_patterns:
                    match = re.search(pattern, text, re.I)
                    if match:
                        ship_data['callsign'] = match.group(1)
                        print(f"Found callsign in text: {ship_data['callsign']}")
                        break
            
            # Vessel type patterns
            if not ship_data['type']:
                type_patterns = [
                    r'Type[:\s]*([^,\n\r]+)',
                    r'Vessel\s*Type[:\s]*([^,\n\r]+)',
                    r'Ship\s*Type[:\s]*([^,\n\r]+)'
                ]
                for pattern in type_patterns:
                    match = re.search(pattern, text, re.I)
                    if match:
                        vessel_type = match.group(1).strip()
                        if vessel_type.lower() not in ['unknown', 'n/a', '-', '']:
                            ship_data['type'] = vessel_type
                            print(f"Found type in text: {vessel_type}")
                            break
                            
        except Exception as e:
            print(f"Error parsing text: {e}")
    
    def _extract_position_data(self, ship_data: Dict[str, Any]):
        """Extract position and movement data"""
        try:
            # Look for position data in various elements
            page_text = self.driver.find_element(By.TAG_NAME, 'body').text
            
            # Try multiple coordinate patterns (but don't overwrite API data)
            if not ship_data['lat'] and not ship_data.get('_coordinates_from_api', False):
                lat_patterns = [
                    r'Lat[itude]*[:\s]*([+-]?\d+\.?\d*)',
                    r'Latitude[:\s]*([+-]?\d+\.?\d*)',
                    r'([+-]?\d{1,2}\.\d+)[°\s]*[NS]',
                    r'Position[:\s]*([+-]?\d+\.?\d*)[°\s,]*[+-]?\d+\.?\d*'
                ]
                for pattern in lat_patterns:
                    lat_match = re.search(pattern, page_text, re.I)
                    if lat_match:
                        try:
                            lat_val = float(lat_match.group(1))
                            if -90 <= lat_val <= 90:  # Validate range
                                ship_data['lat'] = lat_val
                                print(f"Found latitude: {lat_val}")
                                break
                        except ValueError:
                            continue
            
            if not ship_data['lon'] and not ship_data.get('_coordinates_from_api', False):
                lon_patterns = [
                    r'Lon[gitude]*[:\s]*([+-]?\d+\.?\d*)',
                    r'Longitude[:\s]*([+-]?\d+\.?\d*)',
                    r'([+-]?\d{1,3}\.\d+)[°\s]*[EW]',
                    r'Position[:\s]*[+-]?\d+\.?\d*[°\s,]*([+-]?\d+\.?\d*)'
                ]
                for pattern in lon_patterns:
                    lon_match = re.search(pattern, page_text, re.I)
                    if lon_match:
                        try:
                            lon_val = float(lon_match.group(1))
                            if -180 <= lon_val <= 180:  # Validate range
                                ship_data['lon'] = lon_val
                                print(f"Found longitude: {lon_val}")
                                break
                        except ValueError:
                            continue
            
            # Extract speed with multiple patterns
            if not ship_data['speed']:
                speed_patterns = [
                    r'Speed[:\s]*([0-9.]+)',
                    r'SOG[:\s]*([0-9.]+)',
                    r'Speed\s*over\s*Ground[:\s]*([0-9.]+)'
                ]
                for pattern in speed_patterns:
                    speed_match = re.search(pattern, page_text, re.I)
                    if speed_match:
                        try:
                            ship_data['speed'] = float(speed_match.group(1))
                            print(f"Found speed: {ship_data['speed']}")
                            break
                        except ValueError:
                            continue
            
            # Extract course with multiple patterns
            if not ship_data['course']:
                course_patterns = [
                    r'Course[:\s]*([0-9.]+)',
                    r'COG[:\s]*([0-9.]+)',
                    r'Course\s*over\s*Ground[:\s]*([0-9.]+)'
                ]
                for pattern in course_patterns:
                    course_match = re.search(pattern, page_text, re.I)
                    if course_match:
                        try:
                            ship_data['course'] = float(course_match.group(1))
                            print(f"Found course: {ship_data['course']}")
                            break
                        except ValueError:
                            continue
            
            # Extract heading
            if not ship_data['heading']:
                heading_patterns = [
                    r'Heading[:\s]*([0-9.]+)',
                    r'HDG[:\s]*([0-9.]+)',
                    r'True\s*Heading[:\s]*([0-9.]+)'
                ]
                for pattern in heading_patterns:
                    heading_match = re.search(pattern, page_text, re.I)
                    if heading_match:
                        try:
                            ship_data['heading'] = float(heading_match.group(1))
                            print(f"Found heading: {ship_data['heading']}")
                            break
                        except ValueError:
                            continue
            
            # Try to extract from specific position elements
            self._extract_from_position_elements(ship_data)
            
            # Try to extract coordinates from map elements
            self._extract_coordinates_from_map(ship_data)
                    
        except Exception as e:
            print(f"Error extracting position data: {e}")
    
    def _extract_from_position_elements(self, ship_data: Dict[str, Any]):
        """Extract position data from specific HTML elements"""
        try:
            # Look for position-specific selectors
            position_selectors = [
                '.position', '.coordinates', '.lat', '.lon', 
                '.latitude', '.longitude', '[data-lat]', '[data-lon]',
                '.vessel-position', '.ship-position'
            ]
            
            for selector in position_selectors:
                try:
                    elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    for element in elements:
                        text = element.text.strip()
                        if text and text.replace('.', '').replace('-', '').isdigit():
                            try:
                                value = float(text)
                                if 'lat' in selector.lower() and not ship_data['lat']:
                                    ship_data['lat'] = value
                                    print(f"Found lat from element: {value}")
                                elif 'lon' in selector.lower() and not ship_data['lon']:
                                    ship_data['lon'] = value
                                    print(f"Found lon from element: {value}")
                            except ValueError:
                                continue
                except:
                    continue
                    
        except Exception as e:
            print(f"Error in position elements: {e}")
    
    def _extract_coordinates_from_map(self, ship_data: Dict[str, Any]):
        """Extract coordinates from map elements and JavaScript variables"""
        try:
            print("Searching for coordinates in map elements...")
            
            # Look for map-related elements
            map_selectors = [
                '.leaflet-marker', '.map-marker', '.vessel-marker',
                '.ship-marker', '[data-lat]', '[data-lng]', '[data-lon]',
                '.leaflet-popup', '.map-popup', '.coordinate-display',
                '.position-display', '.lat-lon', '.coordinates'
            ]
            
            for selector in map_selectors:
                try:
                    elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    for element in elements:
                        # Check data attributes
                        lat_attr = element.get_attribute('data-lat') or element.get_attribute('data-latitude')
                        lon_attr = element.get_attribute('data-lon') or element.get_attribute('data-lng') or element.get_attribute('data-longitude')
                        
                        if lat_attr and not ship_data['lat']:
                            try:
                                ship_data['lat'] = float(lat_attr)
                                print(f"Found latitude from map attribute: {ship_data['lat']}")
                            except ValueError:
                                pass
                        
                        if lon_attr and not ship_data['lon']:
                            try:
                                ship_data['lon'] = float(lon_attr)
                                print(f"Found longitude from map attribute: {ship_data['lon']}")
                            except ValueError:
                                pass
                        
                        # Check element text for coordinates
                        text = element.text.strip()
                        if text:
                            self._parse_coordinate_text(text, ship_data)
                            
                except Exception:
                    continue
            
            # Extract from JavaScript variables
            self._extract_coordinates_from_js(ship_data)
            
            # Look for coordinate patterns in page source
            self._extract_coordinates_from_source(ship_data)
            
            # Try to interact with map to reveal coordinates
            self._interact_with_map(ship_data)
            
            
        except Exception as e:
            print(f"Error extracting coordinates from map: {e}")
    
    def _parse_coordinate_text(self, text: str, ship_data: Dict[str, Any]):
        """Parse coordinate text for lat/lon values"""
        try:
            # Common coordinate patterns
            coordinate_patterns = [
                r'([+-]?\d{1,2}\.\d+)[°\s]*[NS][,\s]*([+-]?\d{1,3}\.\d+)[°\s]*[EW]',
                r'([+-]?\d{1,2}\.\d+)[,\s]+([+-]?\d{1,3}\.\d+)',
                r'Lat[itude]*[:\s]*([+-]?\d{1,2}\.\d+)[,\s]*Lon[gitude]*[:\s]*([+-]?\d{1,3}\.\d+)',
                r'([+-]?\d{1,2}\.\d+)[°\s]*N[,\s]*([+-]?\d{1,3}\.\d+)[°\s]*E',
                r'([+-]?\d{1,2}\.\d+)[°\s]*S[,\s]*([+-]?\d{1,3}\.\d+)[°\s]*W'
            ]
            
            for pattern in coordinate_patterns:
                match = re.search(pattern, text, re.I)
                if match:
                    try:
                        lat_val = float(match.group(1))
                        lon_val = float(match.group(2))
                        
                        # Validate coordinate ranges
                        if -90 <= lat_val <= 90 and -180 <= lon_val <= 180:
                            # Don't overwrite API coordinates
                            if not ship_data.get('_coordinates_from_api', False):
                                if not ship_data['lat']:
                                    ship_data['lat'] = lat_val
                                    print(f"Found latitude from text: {lat_val}")
                                if not ship_data['lon']:
                                    ship_data['lon'] = lon_val
                                    print(f"Found longitude from text: {lon_val}")
                            break
                    except ValueError:
                        continue
                        
        except Exception as e:
            print(f"Error parsing coordinate text: {e}")
    
    def _extract_coordinates_from_js(self, ship_data: Dict[str, Any]):
        """Extract coordinates from JavaScript variables"""
        try:
            # Execute JavaScript to get map center or vessel position
            js_commands = [
                "return window.vesselLat || null;",
                "return window.vesselLon || null;",
                "return window.vesselPosition || null;",
                "return window.shipLat || null;",
                "return window.shipLon || null;",
                "return window.mapCenter || null;",
                "return window.vessel && vessel.lat || null;",
                "return window.vessel && vessel.lon || null;",
                "return typeof map !== 'undefined' && map.getCenter ? map.getCenter() : null;"
            ]
            
            for cmd in js_commands:
                try:
                    result = self.driver.execute_script(cmd)
                    if result:
                        if isinstance(result, dict):
                            if 'lat' in result and not ship_data['lat']:
                                ship_data['lat'] = float(result['lat'])
                                print(f"Found latitude from JS: {ship_data['lat']}")
                            if 'lng' in result and not ship_data['lon']:
                                ship_data['lon'] = float(result['lng'])
                                print(f"Found longitude from JS: {ship_data['lon']}")
                            elif 'lon' in result and not ship_data['lon']:
                                ship_data['lon'] = float(result['lon'])
                                print(f"Found longitude from JS: {ship_data['lon']}")
                        elif isinstance(result, (int, float)):
                            if 'Lat' in cmd and not ship_data['lat']:
                                ship_data['lat'] = float(result)
                                print(f"Found latitude from JS variable: {result}")
                            elif 'Lon' in cmd and not ship_data['lon']:
                                ship_data['lon'] = float(result)
                                print(f"Found longitude from JS variable: {result}")
                except Exception:
                    continue
                    
        except Exception as e:
            print(f"Error extracting coordinates from JS: {e}")
    
    def _extract_coordinates_from_source(self, ship_data: Dict[str, Any]):
        """Extract coordinates from page source"""
        try:
            page_source = self.driver.page_source
            
            # Look for coordinate patterns in the source
            source_patterns = [
                r'"lat"[:\s]*([+-]?\d{1,2}\.\d+)',
                r'"lng"[:\s]*([+-]?\d{1,3}\.\d+)',
                r'"lon"[:\s]*([+-]?\d{1,3}\.\d+)',
                r'"latitude"[:\s]*([+-]?\d{1,2}\.\d+)',
                r'"longitude"[:\s]*([+-]?\d{1,3}\.\d+)',
                r'lat[:\s]*([+-]?\d{1,2}\.\d+)',
                r'lng[:\s]*([+-]?\d{1,3}\.\d+)',
                r'position[:\s]*\[[^\]]*([+-]?\d{1,2}\.\d+)[,\s]*([+-]?\d{1,3}\.\d+)',
                r'center[:\s]*\[[^\]]*([+-]?\d{1,2}\.\d+)[,\s]*([+-]?\d{1,3}\.\d+)'
            ]
            
            for pattern in source_patterns:
                matches = re.findall(pattern, page_source, re.I)
                for match in matches:
                    try:
                        if isinstance(match, tuple) and len(match) == 2:
                            lat_val, lon_val = float(match[0]), float(match[1])
                        else:
                            if 'lat' in pattern.lower() and not ship_data['lat']:
                                lat_val = float(match)
                                if -90 <= lat_val <= 90:
                                    ship_data['lat'] = lat_val
                                    print(f"Found latitude from source: {lat_val}")
                            elif ('lng' in pattern.lower() or 'lon' in pattern.lower()) and not ship_data['lon']:
                                lon_val = float(match)
                                if -180 <= lon_val <= 180:
                                    ship_data['lon'] = lon_val
                                    print(f"Found longitude from source: {lon_val}")
                            continue
                        
                        # Validate ranges for tuple matches
                        if -90 <= lat_val <= 90 and -180 <= lon_val <= 180:
                            if not ship_data['lat']:
                                ship_data['lat'] = lat_val
                                print(f"Found latitude from source pattern: {lat_val}")
                            if not ship_data['lon']:
                                ship_data['lon'] = lon_val
                                print(f"Found longitude from source pattern: {lon_val}")
                            break
                    except (ValueError, TypeError):
                        continue
                        
        except Exception as e:
            print(f"Error extracting coordinates from source: {e}")
    
    def _interact_with_map(self, ship_data: Dict[str, Any]):
        """Try to interact with map elements to reveal coordinates"""
        try:
            print("Attempting to interact with map elements...")
            
            # Look for map containers
            map_containers = [
                '#map', '.map', '.leaflet-container', '.map-container',
                '.vessel-map', '.ship-map', '[data-map]'
            ]
            
            for container_selector in map_containers:
                try:
                    map_element = self.driver.find_element(By.CSS_SELECTOR, container_selector)
                    if map_element.is_displayed():
                        print(f"Found map container: {container_selector}")
                        
                        # Try to hover over the map center to reveal coordinates
                        from selenium.webdriver.common.action_chains import ActionChains
                        actions = ActionChains(self.driver)
                        actions.move_to_element(map_element).perform()
                        time.sleep(2)
                        
                        # Look for any tooltips or popups that appeared
                        tooltip_selectors = [
                            '.leaflet-tooltip', '.map-tooltip', '.coordinate-tooltip',
                            '.popup', '.leaflet-popup', '.vessel-popup'
                        ]
                        
                        for tooltip_selector in tooltip_selectors:
                            try:
                                tooltips = self.driver.find_elements(By.CSS_SELECTOR, tooltip_selector)
                                for tooltip in tooltips:
                                    if tooltip.is_displayed():
                                        tooltip_text = tooltip.text
                                        print(f"Found tooltip text: {tooltip_text}")
                                        self._parse_coordinate_text(tooltip_text, ship_data)
                            except:
                                continue
                        
                        # Try clicking on vessel markers
                        marker_selectors = [
                            '.leaflet-marker', '.vessel-marker', '.ship-marker',
                            '.marker', '[data-vessel]', '.vessel-icon'
                        ]
                        
                        for marker_selector in marker_selectors:
                            try:
                                markers = self.driver.find_elements(By.CSS_SELECTOR, marker_selector)
                                for marker in markers:
                                    if marker.is_displayed():
                                        marker.click()
                                        time.sleep(1)
                                        print(f"Clicked marker: {marker_selector}")
                                        
                                        # Check if any coordinate info appeared
                                        page_text = self.driver.find_element(By.TAG_NAME, 'body').text
                                        self._parse_coordinate_text(page_text, ship_data)
                                        
                                        if ship_data['lat'] and ship_data['lon']:
                                            return  # Found coordinates, exit
                                        break
                            except:
                                continue
                        break
                        
                except Exception:
                    continue
                    
        except Exception as e:
            print(f"Error interacting with map: {e}")
    
    def _extract_from_network_requests(self, ship_data: Dict[str, Any]):
        """Extract coordinates from network requests (API calls)"""
        try:
            print("Checking network requests for position data...")
            
            # Get performance logs to see network requests
            logs = self.driver.get_log('performance')
            
            for log in logs:
                try:
                    message = json.loads(log['message'])
                    
                    # Look for Network.responseReceived events
                    if message['message']['method'] == 'Network.responseReceived':
                        response = message['message']['params']['response']
                        url = response.get('url', '')
                        
                        # Check if this is a position/vessel API call
                        if any(keyword in url.lower() for keyword in ['position', 'vessel', 'ship', 'coordinates']):
                            print(f"Found potential API call: {url}")
                            
                            # Special handling for position API
                            if '/position' in url:
                                print(f"*** FOUND POSITION API CALL: {url} ***")
                            
                            # Try to get the response body
                            try:
                                request_id = message['message']['params']['requestId']
                                response_body = self.driver.execute_cdp_cmd('Network.getResponseBody', {'requestId': request_id})
                                
                                if response_body and 'body' in response_body:
                                    body_content = response_body['body']
                                    print(f"Response body: {body_content[:500]}...")  # Show first 500 chars
                                    
                                    # Try to parse as JSON
                                    try:
                                        data = json.loads(body_content)
                                        self._extract_coordinates_from_api_response(data, ship_data)
                                        
                                        if ship_data['lat'] and ship_data['lon']:
                                            print("Successfully extracted coordinates from API response!")
                                            # Mark that we found coordinates from API to prevent overwriting
                                            ship_data['_coordinates_from_api'] = True
                                            return
                                            
                                    except json.JSONDecodeError:
                                        # Don't extract coordinates from SVG files
                                        if not url.endswith('.svg'):
                                            # Try to extract coordinates from text response
                                            self._parse_coordinate_text(body_content, ship_data)
                                        
                            except Exception as e:
                                print(f"Could not get response body for {url}: {e}")
                                continue
                                
                except Exception as e:
                    continue
            
            # Also try to make direct API calls based on the MMSI
            self._try_direct_api_calls(ship_data)
                    
        except Exception as e:
            print(f"Error extracting from network requests: {e}")
    
    def _extract_coordinates_from_api_response(self, data: Dict, ship_data: Dict[str, Any]):
        """Extract coordinates from API response data"""
        try:
            # Handle the position API response format you found
            if isinstance(data, dict):
                # Direct coordinate fields - prioritize API data
                if 'lat' in data:
                    try:
                        lat_val = float(data['lat'])
                        ship_data['lat'] = lat_val
                        ship_data['_coordinates_from_api'] = True
                        print(f"Found latitude from API: {lat_val}")
                    except (ValueError, TypeError):
                        pass
                
                if 'lon' in data:
                    try:
                        lon_val = float(data['lon'])
                        ship_data['lon'] = lon_val
                        ship_data['_coordinates_from_api'] = True
                        print(f"Found longitude from API: {lon_val}")
                    except (ValueError, TypeError):
                        pass
                
                # Also extract other available data
                api_field_mapping = {
                    'speed': 'speed',
                    'course': 'course', 
                    'heading': 'heading',
                    'draught': 'draught',
                    'navigationalStatus': 'nav_status',
                    'timestamp': 'timestamp'
                }
                
                for api_field, ship_field in api_field_mapping.items():
                    if api_field in data and not ship_data[ship_field]:
                        value = data[api_field]
                        if value is not None:
                            if ship_field in ['speed', 'course', 'heading', 'draught']:
                                try:
                                    ship_data[ship_field] = float(value)
                                    print(f"Found {ship_field} from API: {value}")
                                except (ValueError, TypeError):
                                    pass
                            else:
                                ship_data[ship_field] = value
                                print(f"Found {ship_field} from API: {value}")
            
            elif isinstance(data, list):
                # Handle array responses
                for item in data:
                    if isinstance(item, dict):
                        self._extract_coordinates_from_api_response(item, ship_data)
                        if ship_data['lat'] and ship_data['lon']:
                            break
                            
        except Exception as e:
            print(f"Error extracting from API response: {e}")
    
    def _try_direct_api_calls(self, ship_data: Dict[str, Any]):
        """Try to make direct API calls to get position data"""
        try:
            print("Attempting direct API calls...")
            
            # Extract ship ID from the current page if possible
            ship_id = None
            
            # Try to get ship ID from JavaScript
            try:
                ship_id = self.driver.execute_script("return window.shipId || window.vesselId || null;")
            except:
                pass
            
            # Try to get ship ID from URL or page content
            if not ship_id:
                current_url = self.driver.current_url
                # Look for ship ID patterns in URL
                id_match = re.search(r'/(\d+)/', current_url)
                if id_match:
                    ship_id = id_match.group(1)
            
            # Try to find ship ID in page source
            if not ship_id:
                page_source = self.driver.page_source
                ship_id_patterns = [
                    r'"shipId"[:\s]*(\d+)',
                    r'"vesselId"[:\s]*(\d+)',
                    r'shipId[:\s]*(\d+)',
                    r'vesselId[:\s]*(\d+)'
                ]
                for pattern in ship_id_patterns:
                    match = re.search(pattern, page_source)
                    if match:
                        ship_id = match.group(1)
                        break
            
            if ship_id:
                print(f"Found ship ID: {ship_id}")
                
                # Try the position API endpoint you discovered
                position_url = f"https://www.marinetraffic.com/en/vessels/{ship_id}/position"
                
                try:
                    # Use JavaScript to make the API call from within the browser context
                    print(f"Trying API call to: {position_url}")
                    
                    # Set up a promise-based fetch that we can wait for
                    api_response = self.driver.execute_async_script(f"""
                        var callback = arguments[arguments.length - 1];
                        
                        fetch('{position_url}')
                            .then(response => {{
                                if (!response.ok) {{
                                    throw new Error('Network response was not ok');
                                }}
                                return response.json();
                            }})
                            .then(data => {{
                                callback(data);
                            }})
                            .catch(error => {{
                                console.error('Fetch error:', error);
                                callback(null);
                            }});
                    """)
                    
                    if api_response:
                        print(f"Direct API response: {api_response}")
                        self._extract_coordinates_from_api_response(api_response, ship_data)
                    else:
                        print("API call returned no data")
                        
                except Exception as e:
                    print(f"Direct API call failed: {e}")
                    
                    # Fallback: try to navigate to the API URL directly
                    try:
                        print("Trying direct navigation to API endpoint...")
                        self.driver.get(position_url)
                        time.sleep(2)
                        
                        # Get the page content (should be JSON)
                        page_text = self.driver.find_element(By.TAG_NAME, 'body').text
                        if page_text.strip().startswith('{'):
                            try:
                                api_data = json.loads(page_text)
                                print(f"API data from direct navigation: {api_data}")
                                self._extract_coordinates_from_api_response(api_data, ship_data)
                            except json.JSONDecodeError:
                                print("Could not parse API response as JSON")
                        
                        # Navigate back to the original page
                        original_url = f"https://www.marinetraffic.com/en/ais/details/ships/mmsi:{ship_data['mmsi']}"
                        self.driver.get(original_url)
                        time.sleep(2)
                        
                    except Exception as e2:
                        print(f"Direct navigation also failed: {e2}")
            else:
                print("Could not find ship ID for direct API call")
                
        except Exception as e:
            print(f"Error in direct API calls: {e}")
    
    def send_to_posthog(self, ship_data: Dict[str, Any], comparison_id: str = None):
        """Send scraped data to PostHog"""
        try:
            if not POSTHOG_AVAILABLE or not self.posthog_api_key:
                logger.warning("PostHog not available - skipping data send")
                return False
            
            # Get current timestamp
            timestamp_dt = datetime.now()
            timestamp_iso = timestamp_dt.isoformat()
            
            logger.info(f"Processing MarineTraffic Selenium data for PostHog: {ship_data}")
            logger.info(f"PostHog comparison_id: {comparison_id}")
            
            # Format data according to your specification
            posthog_properties = {
                "provider": "MarineTraffic",
                "mmsi": str(ship_data.get("mmsi", "")),
                "name": ship_data.get("name"),
                "callsign": ship_data.get("callsign"),
                "type": ship_data.get("type"),
                "lat": float(ship_data.get("lat")) if ship_data.get("lat") is not None else None,
                "lon": float(ship_data.get("lon")) if ship_data.get("lon") is not None else None,
                "speed": ship_data.get("speed") if ship_data.get("speed") is not None else None,
                "course": ship_data.get("course") if ship_data.get("course") is not None else None,
                "heading": ship_data.get("heading") if ship_data.get("heading") is not None else None,
                "draught": ship_data.get("draught") if ship_data.get("draught") is not None else None,
                "nav_status": ship_data.get("nav_status"),
                "destination": ship_data.get("destination", ""),
                "timestamp": timestamp_iso,
                "imo": ship_data.get("imo"),
                "comparison_id": comparison_id,
                "data_source": "selenium_scraper"
            }
            
            logger.info(f"PostHog properties to send: {posthog_properties}")
            
            # Send to PostHog
            posthog.capture(
                distinct_id="selenium_scraper",
                event="marine_traffic_scrape",
                properties=posthog_properties,
                timestamp=timestamp_dt
            )
            
            logger.info(f"Successfully sent data to PostHog for MMSI: {ship_data.get('mmsi')}")
            return True
            
        except Exception as e:
            logger.error(f"Error sending data to PostHog: {e}")
            return False
    
    def _extract_voyage_data(self, ship_data: Dict[str, Any]):
        """Extract voyage related data"""
        try:
            page_text = self.driver.find_element(By.TAG_NAME, 'body').text
            
            # Extract destination with multiple patterns
            if not ship_data['destination']:
                dest_patterns = [
                    r'Destination[:\s]*([^,\n\r]+)',
                    r'Port\s*of\s*Call[:\s]*([^,\n\r]+)',
                    r'Next\s*Port[:\s]*([^,\n\r]+)',
                    r'Bound\s*for[:\s]*([^,\n\r]+)'
                ]
                for pattern in dest_patterns:
                    dest_match = re.search(pattern, page_text, re.I)
                    if dest_match:
                        dest = dest_match.group(1).strip()
                        if dest and dest.lower() not in ['unknown', 'n/a', '-', 'upgrade to unlock']:
                            ship_data['destination'] = dest
                            print(f"Found destination: {dest}")
                            break
            
            # Extract navigation status with multiple patterns
            if not ship_data['nav_status']:
                status_patterns = [
                    r'Status[:\s]*([^,\n\r]+)',
                    r'Navigation\s*Status[:\s]*([^,\n\r]+)',
                    r'Nav\s*Status[:\s]*([^,\n\r]+)',
                    r'Current\s*Status[:\s]*([^,\n\r]+)'
                ]
                for pattern in status_patterns:
                    status_match = re.search(pattern, page_text, re.I)
                    if status_match:
                        status = status_match.group(1).strip()
                        if status and status.lower() not in ['unknown', 'n/a', '-', 'upgrade to unlock']:
                            ship_data['nav_status'] = status
                            print(f"Found nav status: {status}")
                            break
            
            # Extract draught
            if not ship_data['draught']:
                draught_patterns = [
                    r'Draught[:\s]*([0-9.]+)',
                    r'Draft[:\s]*([0-9.]+)',
                    r'Maximum\s*Draught[:\s]*([0-9.]+)',
                    r'Current\s*Draught[:\s]*([0-9.]+)'
                ]
                for pattern in draught_patterns:
                    draught_match = re.search(pattern, page_text, re.I)
                    if draught_match:
                        try:
                            ship_data['draught'] = float(draught_match.group(1))
                            print(f"Found draught: {ship_data['draught']}")
                            break
                        except ValueError:
                            continue
            
            # Try to extract from specific voyage elements
            self._extract_from_voyage_elements(ship_data)
                    
        except Exception as e:
            print(f"Error extracting voyage data: {e}")
    
    def _extract_from_voyage_elements(self, ship_data: Dict[str, Any]):
        """Extract voyage data from specific HTML elements"""
        try:
            # Look for voyage-specific selectors
            voyage_selectors = [
                '.destination', '.port', '.status', '.draught',
                '.voyage-info', '.trip-info', '[data-destination]',
                '[data-status]', '.nav-status'
            ]
            
            for selector in voyage_selectors:
                try:
                    elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    for element in elements:
                        text = element.text.strip()
                        if text and text.lower() not in ['unknown', 'n/a', '-', 'upgrade to unlock', '']:
                            if 'destination' in selector.lower() and not ship_data['destination']:
                                ship_data['destination'] = text
                                print(f"Found destination from element: {text}")
                            elif 'status' in selector.lower() and not ship_data['nav_status']:
                                ship_data['nav_status'] = text
                                print(f"Found nav status from element: {text}")
                            elif 'draught' in selector.lower() and not ship_data['draught']:
                                try:
                                    draught_val = float(re.search(r'([0-9.]+)', text).group(1))
                                    ship_data['draught'] = draught_val
                                    print(f"Found draught from element: {draught_val}")
                                except (ValueError, AttributeError):
                                    continue
                except:
                    continue
                    
        except Exception as e:
            print(f"Error in voyage elements: {e}")
    
    def _extract_from_html(self, html_content: str, ship_data: Dict[str, Any]):
        """Extract data from HTML content as fallback"""
        try:
            # Look for JSON data in script tags
            json_patterns = [
                r'var\s+vessel\s*=\s*({[^}]+})',
                r'window\.vessel\s*=\s*({[^}]+})',
                r'"vessel":\s*({[^}]+})',
            ]
            
            for pattern in json_patterns:
                matches = re.findall(pattern, html_content, re.DOTALL)
                for match in matches:
                    try:
                        data = json.loads(match)
                        self._update_from_json(data, ship_data)
                    except json.JSONDecodeError:
                        continue
                        
        except Exception as e:
            print(f"Error extracting from HTML: {e}")
    
    def _update_from_json(self, json_data: Dict, ship_data: Dict[str, Any]):
        """Update ship data from JSON object"""
        mapping = {
            'mmsi': 'mmsi',
            'shipname': 'name',
            'callsign': 'callsign',
            'shiptype': 'type',
            'lat': 'lat',
            'lon': 'lon',
            'speed': 'speed',
            'course': 'course',
            'heading': 'heading',
            'draught': 'draught',
            'navstat': 'nav_status',
            'destination': 'destination',
            'timestamp': 'timestamp',
            'imo': 'imo'
        }
        
        for json_key, ship_key in mapping.items():
            if json_key in json_data and not ship_data[ship_key]:
                ship_data[ship_key] = json_data[json_key]
                print(f"Updated {ship_key} from JSON: {json_data[json_key]}")
    
    def close(self):
        """Close the browser driver"""
        if self.driver:
            self.driver.quit()
            self.driver = None
    
    def __enter__(self):
        return self
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()


def get_ship_data_selenium(mmsi: str, headless: bool = True, comparison_id: str = None, send_to_posthog: bool = False) -> Dict[str, Any]:
    """
    Get ship data using Selenium scraper
    
    Args:
        mmsi: Ship MMSI number
        headless: Run browser in headless mode
        comparison_id: Optional comparison ID for PostHog
        send_to_posthog: Whether to send data to PostHog
        
    Returns:
        Dictionary containing ship data
    """
    scraper = SeleniumMarineTrafficScraper(headless=headless)
    
    try:
        ship_data = scraper.get_ship_details(mmsi)
        
        # Send to PostHog if requested
        if send_to_posthog:
            scraper.send_to_posthog(ship_data, comparison_id)
        
        return ship_data
        
    except Exception as e:
        logger.error(f"Error scraping ship data: {e}")
        raise
    finally:
        scraper.close()


if __name__ == "__main__":
    # Test ChromeDriver availability
    try:
        options = Options()
        options.add_argument('--headless')
        driver = webdriver.Chrome(options=options)
        driver.quit()
        print("ChromeDriver is available")
    except Exception as e:
        print(f"ChromeDriver not available: {e}")
        print("Please install ChromeDriver:")
        print("1. Download from: https://chromedriver.chromium.org/")
        print("2. Or install via brew: brew install chromedriver")
        print("3. Or install via pip: pip install webdriver-manager")
        import sys
        sys.exit(1)
    
    # Test with provided MMSI
    test_mmsi = "677350000"
    
    try:
        print(f"Testing Selenium scraper with MMSI: {test_mmsi}")
        ship_data = get_ship_data_selenium(test_mmsi, headless=True)
        
        print("\nExtracted ship data:")
        print(json.dumps(ship_data, indent=2, default=str))
        
    except Exception as e:
        print(f"Error: {e}")
        print("\nNote: This approach requires ChromeDriver to be installed.")
        print("If MarineTraffic detects automation, try:")
        print("1. Adding more delays")
        print("2. Using residential proxies")
        print("3. Implementing CAPTCHA solving")
        print("4. Using their official API instead")
