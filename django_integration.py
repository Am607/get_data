# models.py
from django.db import models
from django.utils import timezone


class Ship(models.Model):
    """Django model for storing ship data"""
    
    # Required fields
    provider = models.CharField(max_length=100, default='MarineTraffic')
    mmsi = models.CharField(max_length=20, unique=True, db_index=True)
    name = models.CharField(max_length=200, null=True, blank=True)
    callsign = models.CharField(max_length=20, null=True, blank=True)
    ship_type = models.CharField(max_length=100, null=True, blank=True)
    
    # Position data
    lat = models.FloatField(null=True, blank=True)
    lon = models.FloatField(null=True, blank=True)
    speed = models.FloatField(null=True, blank=True)
    course = models.FloatField(null=True, blank=True)
    heading = models.FloatField(null=True, blank=True)
    
    # Technical data
    draught = models.FloatField(null=True, blank=True)
    nav_status = models.CharField(max_length=100, null=True, blank=True)
    destination = models.CharField(max_length=200, null=True, blank=True)
    
    # Metadata
    timestamp = models.DateTimeField(null=True, blank=True)
    imo = models.CharField(max_length=20, null=True, blank=True)
    comparison_id = models.CharField(max_length=100, null=True, blank=True)
    data_source = models.CharField(max_length=100, default='MarineTraffic')
    
    # Django metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'ships'
        ordering = ['-updated_at']
        
    def __str__(self):
        return f"{self.name or 'Unknown'} (MMSI: {self.mmsi})"


# views.py
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.utils.decorators import method_decorator
from django.views import View
from django.core.exceptions import ValidationError
import json
import logging
from .marine_traffic_scraper import get_ship_data

logger = logging.getLogger(__name__)


@method_decorator(csrf_exempt, name='dispatch')
class ShipDataView(View):
    """API view for fetching and storing ship data"""
    
    def get(self, request, mmsi=None):
        """Get ship data by MMSI"""
        if not mmsi:
            mmsi = request.GET.get('mmsi')
        
        if not mmsi:
            return JsonResponse({
                'error': 'MMSI parameter is required'
            }, status=400)
        
        try:
            # Try to get from database first
            ship = Ship.objects.filter(mmsi=mmsi).first()
            
            if ship:
                return JsonResponse({
                    'success': True,
                    'data': self._ship_to_dict(ship),
                    'source': 'database'
                })
            else:
                return JsonResponse({
                    'error': 'Ship not found in database. Use POST to fetch from MarineTraffic.'
                }, status=404)
                
        except Exception as e:
            logger.error(f"Error fetching ship data: {str(e)}")
            return JsonResponse({
                'error': 'Internal server error'
            }, status=500)
    
    def post(self, request, mmsi=None):
        """Fetch ship data from MarineTraffic and store in database"""
        try:
            if not mmsi:
                data = json.loads(request.body)
                mmsi = data.get('mmsi')
            
            if not mmsi:
                return JsonResponse({
                    'error': 'MMSI is required'
                }, status=400)
            
            # Fetch data from MarineTraffic
            logger.info(f"Fetching ship data for MMSI: {mmsi}")
            ship_data = get_ship_data(mmsi)
            
            # Create or update ship record
            ship, created = Ship.objects.update_or_create(
                mmsi=mmsi,
                defaults={
                    'provider': ship_data.get('provider'),
                    'name': ship_data.get('name'),
                    'callsign': ship_data.get('callsign'),
                    'ship_type': ship_data.get('type'),
                    'lat': ship_data.get('lat'),
                    'lon': ship_data.get('lon'),
                    'speed': ship_data.get('speed'),
                    'course': ship_data.get('course'),
                    'heading': ship_data.get('heading'),
                    'draught': ship_data.get('draught'),
                    'nav_status': ship_data.get('nav_status'),
                    'destination': ship_data.get('destination'),
                    'timestamp': ship_data.get('timestamp'),
                    'imo': ship_data.get('imo'),
                    'comparison_id': ship_data.get('comparison_id'),
                    'data_source': ship_data.get('data_source'),
                }
            )
            
            return JsonResponse({
                'success': True,
                'data': self._ship_to_dict(ship),
                'created': created,
                'source': 'marinetraffic'
            })
            
        except json.JSONDecodeError:
            return JsonResponse({
                'error': 'Invalid JSON data'
            }, status=400)
        except Exception as e:
            logger.error(f"Error scraping ship data: {str(e)}")
            return JsonResponse({
                'error': f'Failed to fetch ship data: {str(e)}'
            }, status=500)
    
    def _ship_to_dict(self, ship):
        """Convert ship model to dictionary"""
        return {
            'provider': ship.provider,
            'mmsi': ship.mmsi,
            'name': ship.name,
            'callsign': ship.callsign,
            'type': ship.ship_type,
            'lat': ship.lat,
            'lon': ship.lon,
            'speed': ship.speed,
            'course': ship.course,
            'heading': ship.heading,
            'draught': ship.draught,
            'nav_status': ship.nav_status,
            'destination': ship.destination,
            'timestamp': ship.timestamp.isoformat() if ship.timestamp else None,
            'imo': ship.imo,
            'comparison_id': ship.comparison_id,
            'data_source': ship.data_source,
            'created_at': ship.created_at.isoformat(),
            'updated_at': ship.updated_at.isoformat(),
        }


# urls.py
from django.urls import path
from . import views

urlpatterns = [
    path('api/ships/', views.ShipDataView.as_view(), name='ship_list'),
    path('api/ships/<str:mmsi>/', views.ShipDataView.as_view(), name='ship_detail'),
]


# management/commands/scrape_ship.py
from django.core.management.base import BaseCommand
from django.core.exceptions import ValidationError
from ...models import Ship
from ...marine_traffic_scraper import get_ship_data


class Command(BaseCommand):
    help = 'Scrape ship data from MarineTraffic by MMSI'
    
    def add_arguments(self, parser):
        parser.add_argument('mmsi', type=str, help='MMSI of the ship to scrape')
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force update even if ship exists in database',
        )
    
    def handle(self, *args, **options):
        mmsi = options['mmsi']
        force = options['force']
        
        try:
            # Check if ship already exists
            existing_ship = Ship.objects.filter(mmsi=mmsi).first()
            if existing_ship and not force:
                self.stdout.write(
                    self.style.WARNING(
                        f'Ship with MMSI {mmsi} already exists. Use --force to update.'
                    )
                )
                return
            
            # Fetch ship data
            self.stdout.write(f'Fetching ship data for MMSI: {mmsi}')
            ship_data = get_ship_data(mmsi)
            
            # Create or update ship
            ship, created = Ship.objects.update_or_create(
                mmsi=mmsi,
                defaults={
                    'provider': ship_data.get('provider'),
                    'name': ship_data.get('name'),
                    'callsign': ship_data.get('callsign'),
                    'ship_type': ship_data.get('type'),
                    'lat': ship_data.get('lat'),
                    'lon': ship_data.get('lon'),
                    'speed': ship_data.get('speed'),
                    'course': ship_data.get('course'),
                    'heading': ship_data.get('heading'),
                    'draught': ship_data.get('draught'),
                    'nav_status': ship_data.get('nav_status'),
                    'destination': ship_data.get('destination'),
                    'timestamp': ship_data.get('timestamp'),
                    'imo': ship_data.get('imo'),
                    'comparison_id': ship_data.get('comparison_id'),
                    'data_source': ship_data.get('data_source'),
                }
            )
            
            action = 'Created' if created else 'Updated'
            self.stdout.write(
                self.style.SUCCESS(
                    f'{action} ship: {ship.name or "Unknown"} (MMSI: {mmsi})'
                )
            )
            
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Error scraping ship data: {str(e)}')
            )
