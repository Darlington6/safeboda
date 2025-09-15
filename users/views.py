from rest_framework import generics, status, permissions, filters
from rest_framework.decorators import api_view, permission_classes
from rest_framework.request import Request
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend  # This line is valid and should remain
from django.db.models import QuerySet
from typing import Any, Optional, TYPE_CHECKING

from .models import Passenger
from .serializers import PassengerSerializer, PassengerCreateSerializer

if TYPE_CHECKING:
    from django.contrib.auth.models import AbstractUser


class PassengerListCreateView(generics.ListCreateAPIView):
    """
    API view for listing and creating passenger profiles.
    
    GET /passengers/ - List all passengers (admin only)
    POST /passengers/ - Create new passenger profile (authenticated users only)
    """
    
    queryset: QuerySet[Passenger] = Passenger.objects.select_related('user').all()
    permission_classes: tuple[type[permissions.BasePermission], ...] = (permissions.IsAuthenticated,)
    filter_backends: tuple[type[filters.BaseFilterBackend], ...] = (
        DjangoFilterBackend,
        filters.SearchFilter,
        filters.OrderingFilter,
    )
    
    # Filtering options
    filterset_fields: tuple[str, ...] = (
        'preferred_payment_method',
        'preferred_car_type',
        'is_phone_verified',
        'is_profile_complete',
    )
    
    # Search functionality
    search_fields: tuple[str, ...] = (
        'user__email',
        'user__first_name',
        'user__last_name',
        'home_address',
        'work_address',
    )
    
    # Ordering options
    ordering_fields: tuple[str, ...] = (
        'created_at',
        'updated_at',
        'average_rating',
        'total_rides',
    )
    ordering: tuple[str, ...] = ('-created_at',)  # Default ordering
    
    def get_serializer_class(self) -> type[PassengerSerializer] | type[PassengerCreateSerializer]:
        """
        Return the appropriate serializer class based on the request method.
        """
        if self.request.method == 'POST':
            return PassengerCreateSerializer
        return PassengerSerializer
    
    def get_queryset(self) -> QuerySet[Passenger]:
        """
        Override queryset based on user permissions.
        Regular users can only see their own profile, staff can see all.
        """
        queryset: QuerySet[Passenger] = super().get_queryset()
        
        if not self.request.user.is_staff:
            # Non-staff users can only see their own passenger profile
            queryset = queryset.filter(user=self.request.user)
        
        return queryset
    
    def perform_create(self, serializer: PassengerCreateSerializer) -> None:
        """
        Save the passenger profile with additional context.
        """
        serializer.save()


class PassengerDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    API view for retrieving, updating, and deleting individual passenger profiles.
    
    GET /passengers/{id}/ - Retrieve passenger profile
    PUT/PATCH /passengers/{id}/ - Update passenger profile
    DELETE /passengers/{id}/ - Delete passenger profile
    """
    
    queryset: QuerySet[Passenger] = Passenger.objects.select_related('user').all()
    serializer_class: type[PassengerSerializer] = PassengerSerializer
    permission_classes: tuple[type[permissions.BasePermission], ...] = (permissions.IsAuthenticated,)
    lookup_field: str = 'user_id'  # user_id used instead of pk
    
    def get_queryset(self) -> QuerySet[Passenger]:
        """
        Users can only access their own passenger profile unless they are staff.
        """
        queryset: QuerySet[Passenger] = super().get_queryset()
        
        if not self.request.user.is_staff:
            queryset = queryset.filter(user=self.request.user)
            
        return queryset
    
    def perform_update(self, serializer: PassengerSerializer) -> None:
        """
        Update passenger profile and recalculate completion status.
        """
        passenger: Passenger = serializer.save()
        
        # Recalculate profile completion
        completion_fields: list[bool] = [
            bool(passenger.user.first_name),
            bool(passenger.user.last_name),
            bool(passenger.home_address),
            bool(passenger.emergency_contact_name),
            bool(passenger.emergency_contact_phone),
            passenger.is_phone_verified,
        ]
        
        passenger.is_profile_complete = all(completion_fields)
        passenger.save(update_fields=['is_profile_complete'])


class PassengerStatsView(generics.RetrieveAPIView):
    """
    API view for retrieving passenger statistics.
    
    GET /passengers/{id}/stats/ - Get passenger ride statistics
    """
    
    queryset: QuerySet[Passenger] = Passenger.objects.select_related('user').all()
    serializer_class: type[PassengerSerializer] = PassengerSerializer
    permission_classes: tuple[type[permissions.BasePermission], ...] = (permissions.IsAuthenticated,)
    lookup_field: str = 'user_id'
    
    def get_queryset(self) -> QuerySet[Passenger]:
        """
        Users can only access their own stats unless they are staff.
        """
        queryset: QuerySet[Passenger] = super().get_queryset()
        
        if not self.request.user.is_staff:
            queryset = queryset.filter(user=self.request.user)
            
        return queryset
    
    def retrieve(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        """
        Return detailed statistics for the passenger.
        """
        passenger: Passenger = self.get_object()
        
        stats_data: dict[str, Any] = {
            'passenger_id': passenger.user_id,
            'email': passenger.user.email,
            'total_rides': passenger.total_rides,
            'average_rating': float(passenger.average_rating),
            'profile_completion': self._calculate_completion_percentage(passenger),
            'is_verified': passenger.is_phone_verified,
            'member_since': passenger.created_at,
            'last_updated': passenger.updated_at,
        }
        
        return Response(stats_data, status=status.HTTP_200_OK)
    
    def _calculate_completion_percentage(self, passenger: Passenger) -> int:
        """
        Calculate profile completion percentage.
        """
        total_fields: int = 6
        completed_fields: int = 0
        
        if passenger.user.first_name:
            completed_fields += 1
        if passenger.user.last_name:
            completed_fields += 1
        if passenger.user.phone_number and passenger.is_phone_verified:
            completed_fields += 1
        if passenger.home_address:
            completed_fields += 1
        if passenger.emergency_contact_name:
            completed_fields += 1
        if passenger.emergency_contact_phone:
            completed_fields += 1
            
        return int((completed_fields / total_fields) * 100)


# Function-based view alternative for passenger list
@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def passenger_list_simple(request: Request) -> Response:
    """
    Simple function-based view for listing passengers.
    Alternative to the class-based view above.
    
    GET /passengers/simple/ - List passengers (simplified)
    """
    if request.user.is_staff:
        passengers: QuerySet[Passenger] = Passenger.objects.select_related('user').all()
    else:
        passengers = Passenger.objects.select_related('user').filter(user=request.user)
    
    serializer: PassengerSerializer = PassengerSerializer(passengers, many=True)
    
    response_data: dict[str, Any] = {
        'count': passengers.count(),
        'results': serializer.data,
    }
    
    return Response(response_data, status=status.HTTP_200_OK)