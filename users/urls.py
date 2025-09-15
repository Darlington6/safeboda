from django.urls import path
from typing import List
from django.urls.resolvers import URLPattern
from . import views

app_name: str = 'passengers'

urlpatterns: List[URLPattern] = [
    # Passenger CRUD operations
    path(
        '',
        views.PassengerListCreateView.as_view(),
        name='passenger-list-create'
    ),
    path(
        '<int:user_id>/',
        views.PassengerDetailView.as_view(),
        name='passenger-detail'
    ),
    
    # Passenger statistics
    path(
        '<int:user_id>/stats/',
        views.PassengerStatsView.as_view(),
        name='passenger-stats'
    ),
    
    # Alternative simple endpoint
    path(
        'simple/',
        views.passenger_list_simple,
        name='passenger-list-simple'
    ),
]