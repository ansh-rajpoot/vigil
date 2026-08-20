from django.test import TestCase
from common.utils import (
    haversine_distance, point_in_polygon,
    generate_dynamic_totp_token, verify_dynamic_totp_token,
    generate_secure_crypto_hash
)

class CommonUtilsTestCase(TestCase):
    def test_haversine_distance(self):
        # Distance between Panaji (15.4989, 73.8278) and Calangute (15.5439, 73.7554) is ~9.2 km
        dist = haversine_distance(15.4989, 73.8278, 15.5439, 73.7554)
        self.assertAlmostEqual(dist, 9.2, delta=1.5)

    def test_point_in_polygon(self):
        # Square polygon covering [0,0] to [10,10]
        polygon_geojson = {
            "type": "Polygon",
            "coordinates": [[[0, 0], [10, 0], [10, 10], [0, 10], [0, 0]]]
        }
        # Point inside
        self.assertTrue(point_in_polygon(5.0, 5.0, polygon_geojson))
        # Point outside
        self.assertFalse(point_in_polygon(15.0, 15.0, polygon_geojson))

    def test_totp_generation_and_verification(self):
        secret = "sih_test_secret_key_123"
        token = generate_dynamic_totp_token(secret, step=30)
        self.assertEqual(len(token), 6)
        self.assertTrue(token.isdigit())
        self.assertTrue(verify_dynamic_totp_token(secret, token, step=30, window=1))
        self.assertFalse(verify_dynamic_totp_token(secret, "999999", step=30, window=0))
