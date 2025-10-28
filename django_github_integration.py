"""
Django integration for triggering GitHub Actions MarineTraffic scraper
Add this to your Django views or services
"""

import requests
import logging
from django.conf import settings
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.views import View
import json

logger = logging.getLogger(__name__)


class MarineTrafficScraperTrigger:
    """Service class for triggering GitHub Actions scraper"""
    
    def __init__(self):
        self.github_token = getattr(settings, 'GITHUB_TOKEN', None)
        self.repo_owner = getattr(settings, 'GITHUB_REPO_OWNER', None)
        self.repo_name = getattr(settings, 'GITHUB_REPO_NAME', 'marine-traffic-scrapping')
        
        if not self.github_token or not self.repo_owner:
            logger.error("GitHub configuration missing. Set GITHUB_TOKEN and GITHUB_REPO_OWNER in settings.")
    
    def trigger_scraper(self, mmsi: str, comparison_id: str = None) -> dict:
        """
        Trigger the GitHub Actions scraper
        
        Args:
            mmsi: Ship MMSI number
            comparison_id: Comparison ID for PostHog tracking
            
        Returns:
            Dict with success status and message
        """
        if not self.github_token or not self.repo_owner:
            return {
                'success': False,
                'message': 'GitHub configuration missing'
            }
        
        url = f"https://api.github.com/repos/{self.repo_owner}/{self.repo_name}/dispatches"
        
        headers = {
            "Authorization": f"token {self.github_token}",
            "Accept": "application/vnd.github.v3+json",
            "Content-Type": "application/json"
        }
        
        payload = {
            "event_type": "scrape-marine-traffic",
            "client_payload": {
                "mmsi": mmsi,
                "comparison_id": comparison_id,
                "headless": True,
                "send_to_posthog": True
            }
        }
        
        try:
            logger.info(f"Triggering GitHub Actions scraper for MMSI: {mmsi}")
            response = requests.post(url, headers=headers, json=payload, timeout=30)
            
            if response.status_code == 204:
                logger.info(f"Successfully triggered scraper for MMSI: {mmsi}")
                return {
                    'success': True,
                    'message': f'Scraper triggered successfully for MMSI: {mmsi}',
                    'mmsi': mmsi,
                    'comparison_id': comparison_id
                }
            else:
                logger.error(f"Failed to trigger scraper. Status: {response.status_code}, Response: {response.text}")
                return {
                    'success': False,
                    'message': f'GitHub API error: {response.status_code}',
                    'details': response.text
                }
                
        except requests.exceptions.Timeout:
            logger.error("Timeout while triggering GitHub Actions")
            return {
                'success': False,
                'message': 'Request timeout'
            }
        except Exception as e:
            logger.error(f"Error triggering scraper: {e}")
            return {
                'success': False,
                'message': f'Error: {str(e)}'
            }


@method_decorator(csrf_exempt, name='dispatch')
class TriggerScraperView(View):
    """Django view for triggering the scraper"""
    
    def __init__(self):
        super().__init__()
        self.scraper_trigger = MarineTrafficScraperTrigger()
    
    def post(self, request):
        """Handle POST request to trigger scraper"""
        try:
            data = json.loads(request.body)
            mmsi = data.get('mmsi')
            comparison_id = data.get('comparison_id')
            
            if not mmsi:
                return JsonResponse({
                    'success': False,
                    'message': 'MMSI is required'
                }, status=400)
            
            # Trigger the scraper
            result = self.scraper_trigger.trigger_scraper(mmsi, comparison_id)
            
            status_code = 200 if result['success'] else 500
            return JsonResponse(result, status=status_code)
            
        except json.JSONDecodeError:
            return JsonResponse({
                'success': False,
                'message': 'Invalid JSON in request body'
            }, status=400)
        except Exception as e:
            logger.error(f"Error in TriggerScraperView: {e}")
            return JsonResponse({
                'success': False,
                'message': f'Server error: {str(e)}'
            }, status=500)


# Function-based view alternative
@require_http_methods(["POST"])
@csrf_exempt
def trigger_marine_traffic_scraper(request):
    """Function-based view for triggering the scraper"""
    try:
        data = json.loads(request.body)
        mmsi = data.get('mmsi')
        comparison_id = data.get('comparison_id')
        
        if not mmsi:
            return JsonResponse({
                'success': False,
                'message': 'MMSI is required'
            }, status=400)
        
        scraper_trigger = MarineTrafficScraperTrigger()
        result = scraper_trigger.trigger_scraper(mmsi, comparison_id)
        
        status_code = 200 if result['success'] else 500
        return JsonResponse(result, status=status_code)
        
    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'message': 'Invalid JSON in request body'
        }, status=400)
    except Exception as e:
        logger.error(f"Error in trigger_marine_traffic_scraper: {e}")
        return JsonResponse({
            'success': False,
            'message': f'Server error: {str(e)}'
        }, status=500)


# Add to your urls.py:
"""
from django.urls import path
from . import views

urlpatterns = [
    path('api/scrape/marine-traffic/', views.trigger_marine_traffic_scraper, name='trigger_marine_traffic_scraper'),
    # or using class-based view:
    # path('api/scrape/marine-traffic/', views.TriggerScraperView.as_view(), name='trigger_marine_traffic_scraper'),
]
"""

# Add to your settings.py:
"""
# GitHub Actions configuration
GITHUB_TOKEN = os.getenv('GITHUB_TOKEN')
GITHUB_REPO_OWNER = os.getenv('GITHUB_REPO_OWNER', 'your-username')
GITHUB_REPO_NAME = os.getenv('GITHUB_REPO_NAME', 'marine-traffic-scrapping')
"""
