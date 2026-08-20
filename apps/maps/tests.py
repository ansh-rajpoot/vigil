import json
from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone
from maps.models import SafetyPOI, SafeRoute
from risk.models import Blackspot
from geofencing.models import GeoZone
from tourists.models import TouristProfile, TouristLocationHistory

User = get_user_model()


class GISModuleTestCase(TestCase):
    def setUp(self):
        self.client = Client()

        # Create Tourist
        self.tourist_user = User.objects.create_user(
            username='gis_tester',
            password='Password123!',
            first_name='Ananya',
            last_name='Sen'
        )
        self.profile = TouristProfile.objects.create(
            user=self.tourist_user,
            current_latitude=15.4989,
            current_longitude=73.8278,
            battery_level=90
        )

        # Create POIs in Panaji & Calangute
        self.police_poi = SafetyPOI.objects.create(
            name='Panaji Police Station',
            poi_type='POLICE',
            latitude=15.4980,
            longitude=73.8260,
            contact_number='+91 832 242 0808',
            is_24_hours=True,
            address='Church Square, Panaji'
        )
        self.hospital_poi = SafetyPOI.objects.create(
            name='Goa Medical College (GMC)',
            poi_type='HOSPITAL',
            latitude=15.4620,
            longitude=73.8550,
            contact_number='108',
            is_24_hours=True,
            address='Bambolim'
        )

        # Create Blackspot
        self.blackspot = Blackspot.objects.create(
            name='Panaji Dark Alley Blackspot',
            category='THEFT_PRONE',
            risk_weight=75,
            latitude=15.5010,
            longitude=73.8290,
            radius_meters=300,
            safety_advice='Stay on main lit promenade.'
        )

        # Create GeoZone
        self.geozone = GeoZone.objects.create(
            name='Panaji Safe Haven',
            code='ZONE-PANAJI-SAFE',
            zone_type='SAFE_HAVEN',
            center_latitude=15.4989,
            center_longitude=73.8278,
            polygon_geojson={
                "type": "Polygon",
                "coordinates": [[[73.820, 15.492], [73.835, 15.492], [73.835, 15.505], [73.820, 15.505], [73.820, 15.492]]]
            }
        )

    def test_gis_layers_api(self):
        """Verify GET /maps/api/gis-layers/ returns categorized layers."""
        response = self.client.get(reverse('maps:api_gis_layers'))
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['success'])
        self.assertIn('police_stations', data['data'])
        self.assertIn('hospitals', data['data'])
        self.assertIn('blackspots', data['data'])
        self.assertIn('geozones', data['data'])
        self.assertGreaterEqual(len(data['data']['police_stations']), 1)

    def test_nearby_safeguards_spatial_query(self):
        """Verify spatial proximity search calculates accurate distances to nearest police and hospital."""
        url = reverse('maps:api_nearby_safeguards') + '?lat=15.4989&lng=73.8278&radius_km=10.0'
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['success'])

        nearest_police = data['data']['nearest_police']
        self.assertIsNotNone(nearest_police)
        self.assertEqual(nearest_police['name'], 'Panaji Police Station')
        self.assertLess(nearest_police['distance_km'], 1.0)  # Close proximity (< 1 km)

        nearest_hospital = data['data']['nearest_hospital']
        self.assertIsNotNone(nearest_hospital)
        self.assertEqual(nearest_hospital['name'], 'Goa Medical College (GMC)')

        nearby_hazards = data['data']['nearby_hazards']
        self.assertGreaterEqual(len(nearby_hazards), 1)
        self.assertEqual(nearby_hazards[0]['name'], 'Panaji Dark Alley Blackspot')

    def test_nearby_safeguards_missing_params(self):
        """Verify API handles missing query parameters gracefully."""
        response = self.client.get(reverse('maps:api_nearby_safeguards'))
        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertFalse(data['success'])

    def test_safe_route_calculation_api(self):
        """Verify safe route calculation returns waypoints and evasion detour."""
        payload = {
            'orig_lat': 15.4989,
            'orig_lng': 73.8278,
            'dest_lat': 15.5439,
            'dest_lng': 73.7554
        }
        response = self.client.post(
            reverse('maps:api_calculate_safe_route'),
            data=json.dumps(payload),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['success'])
        self.assertIn('waypoints', data['data'])
        self.assertGreater(len(data['data']['waypoints']), 3)
        self.assertGreater(data['data']['safety_score'], 0)

    def test_place_search_api(self):
        """Verify GET /maps/api/places/ returns filtered landmark matches."""
        # 1. Search for Baga
        res = self.client.get(reverse('maps:api_places') + '?q=baga')
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertTrue(data['success'])
        self.assertGreaterEqual(len(data['data']), 1)
        self.assertTrue(any('Baga' in p['name'] for p in data['data']))

        # 2. Search for Police
        res_pol = self.client.get(reverse('maps:api_places') + '?q=police')
        self.assertEqual(res_pol.status_code, 200)
        data_pol = res_pol.json()
        self.assertTrue(data_pol['success'])
        self.assertGreaterEqual(len(data_pol['data']), 1)

    def test_place_to_place_safe_routing(self):
        """Verify safe routing resolves named places without manual raw coordinates."""
        payload = {
            'orig_place': 'Baga Beach Main Promenade',
            'dest_place': 'Calangute Tourist Police Station',
            'mode': 'walking'
        }
        response = self.client.post(
            reverse('maps:api_calculate_safe_route'),
            data=json.dumps(payload),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['success'])
        self.assertIn('waypoints', data['data'])
        self.assertIn('Baga Beach Main Promenade', data['data']['origin_name'])
        self.assertIn('Calangute Tourist Police Station', data['data']['destination_name'])
        self.assertIn('directions', data['data'])
        self.assertGreater(len(data['data']['directions']), 2)

    def test_safe_routes_view_renders(self):
        """Verify Safe Routes page renders with place selector and interactive map."""
        self.client.force_login(self.tourist_user)
        response = self.client.get(reverse('maps:safe_routes'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'safe-route-map')
        self.assertContains(response, 'orig_place_input')
        self.assertContains(response, 'dest_place_input')
        self.assertContains(response, 'places-catalog-list')

    def test_location_update_throttling(self):
        """Verify location updates throttle history insertion to avoid storing every second."""
        self.client.force_login(self.tourist_user)

        url = reverse('tourists:api_update_location')

        # First location update -> records log
        res1 = self.client.post(url, {
            'latitude': 15.4989,
            'longitude': 73.8278,
            'battery_level': 88
        }, content_type='application/json')
        self.assertEqual(res1.status_code, 200)
        self.assertEqual(TouristLocationHistory.objects.filter(tourist=self.profile).count(), 1)

        # Immediate second update with tiny movement (<15 meters) -> updates profile but throttles history log
        res2 = self.client.post(url, {
            'latitude': 15.49891,
            'longitude': 73.82781,
            'battery_level': 87
        }, content_type='application/json')
        self.assertEqual(res2.status_code, 200)
        # History count remains 1 due to sensible interval throttling
        self.assertEqual(TouristLocationHistory.objects.filter(tourist=self.profile).count(), 1)

    def test_gis_explorer_view_renders(self):
        """Verify GIS Explorer template renders properly with modern map canvas and search."""
        response = self.client.get(reverse('maps:gis_explorer'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "gis-explorer-map")
        self.assertContains(response, "gis-basemap-switcher")
        self.assertContains(response, "gis-place-search")

    def test_cities_list_api(self):
        """Verify GET /maps/api/cities/ returns all 6 major cities with safety metrics."""
        response = self.client.get(reverse('maps:api_cities'))
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['success'])
        cities = data['data']
        self.assertGreaterEqual(len(cities), 6)
        city_codes = [c['city_code'] for c in cities]
        self.assertIn('MUMBAI', city_codes)
        self.assertIn('DELHI', city_codes)
        self.assertIn('NOIDA', city_codes)
        self.assertIn('JAIPUR', city_codes)
        self.assertIn('AGRA', city_codes)
        self.assertIn('GOA', city_codes)

    def test_multi_city_place_search(self):
        """Verify searching places filtered by city returns accurate landmark safety data."""
        # 1. Search Mumbai Gateway
        res_mum = self.client.get(reverse('maps:api_places') + '?city=MUMBAI&q=gateway')
        self.assertEqual(res_mum.status_code, 200)
        data_mum = res_mum.json()
        self.assertTrue(data_mum['success'])
        self.assertTrue(any('Gateway' in p['name'] for p in data_mum['data']))

        # 2. Search Agra Taj Mahal
        res_agr = self.client.get(reverse('maps:api_places') + '?city=AGRA&q=taj')
        self.assertEqual(res_agr.status_code, 200)
        data_agr = res_agr.json()
        self.assertTrue(data_agr['success'])
        self.assertTrue(any('Taj Mahal' in p['name'] for p in data_agr['data']))

        # 3. Search Jaipur Hawa Mahal
        res_jai = self.client.get(reverse('maps:api_places') + '?city=JAIPUR&q=hawa')
        self.assertEqual(res_jai.status_code, 200)
        data_jai = res_jai.json()
        self.assertTrue(data_jai['success'])
        self.assertTrue(any('Hawa Mahal' in p['name'] for p in data_jai['data']))

        # 4. Search Delhi India Gate
        res_del = self.client.get(reverse('maps:api_places') + '?city=DELHI&q=india')
        self.assertEqual(res_del.status_code, 200)
        data_del = res_del.json()
        self.assertTrue(data_del['success'])
        self.assertTrue(any('India Gate' in p['name'] for p in data_del['data']))

        # 5. Search Noida Sector 18
        res_noi = self.client.get(reverse('maps:api_places') + '?city=NOIDA&q=sector')
        self.assertEqual(res_noi.status_code, 200)
        data_noi = res_noi.json()
        self.assertTrue(data_noi['success'])
        self.assertTrue(any('Sector 18' in p['name'] for p in data_noi['data']))

    def test_place_safety_scorecard_api(self):
        """Verify GET /maps/api/places/safety-scorecard/ returns full safety intelligence breakdown."""
        response = self.client.get(reverse('maps:api_place_safety_scorecard') + '?place=Gateway of India & Taj Mahal Palace&city=MUMBAI')
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['success'])
        scorecard = data['data']
        self.assertIn('safety_score', scorecard)
        self.assertIn('safety_level', scorecard)
        self.assertIn('lighting', scorecard)
        self.assertIn('police_coverage', scorecard)
        self.assertIn('active_pcr_vans', scorecard)
        self.assertIn('restricted_zones', scorecard)
        self.assertIn('safety_tips', scorecard)

    def test_place_safety_explorer_view(self):
        """Verify Place Safety Explorer HTML page renders properly."""
        response = self.client.get(reverse('maps:place_safety_explorer'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Tourist Places & City Safety Intelligence')
        self.assertContains(response, 'place-safety-map')
        self.assertContains(response, 'modal-place-scorecard')
