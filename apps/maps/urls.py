from django.urls import path
from . import views

app_name = 'maps'

urlpatterns = [
    # Pages
    path('explorer/', views.gis_explorer_view, name='gis_explorer'),
    path('safe-routes/', views.safe_routes_view, name='safe_routes'),
    path('places-safety/', views.place_safety_explorer_view, name='place_safety_explorer'),

    # REST APIs
    path('api/cities/', views.CitiesListAPIView.as_view(), name='api_cities'),
    path('api/places/', views.PlaceSearchAPIView.as_view(), name='api_places'),
    path('api/places/safety-scorecard/', views.PlaceSafetyScorecardAPIView.as_view(), name='api_place_safety_scorecard'),
    path('api/gis-layers/', views.GISLayersAPIView.as_view(), name='api_gis_layers'),
    path('api/nearby-safeguards/', views.NearbySafeguardsAPIView.as_view(), name='api_nearby_safeguards'),
    path('api/calculate-safe-route/', views.CalculateSafeRouteAPIView.as_view(), name='api_calculate_safe_route'),
    path('api/pois/', views.SafetyPOIListAPIView.as_view(), name='api_pois'),
    path('api/saved-routes/', views.SavedSafeRoutesAPIView.as_view(), name='api_saved_routes'),
]
