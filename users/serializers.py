from rest_framework import serializers
from typing import Dict, Any, Optional, TYPE_CHECKING
from decimal import Decimal
from django.contrib.auth import get_user_model
from .models import Passenger

# Fix for PyLance type checking error
if TYPE_CHECKING:
    from django.contrib.auth.models import AbstractUser
else:
    User = get_user_model()

class UserSerializer(serializers.ModelSerializer):
    """
    Nested serializer for User data within Passenger serializer.
    """
    class Meta:
        model = User
        fields: tuple[str, ...] = (
            'email', 
            'first_name', 
            'last_name', 
            'phone_number',
            'is_active',
            'date_joined',
        )
        read_only_fields: tuple[str, ...] = (
            'is_active', 
            'date_joined',
        )
        
        
class PassengerSerializer(serializers.ModelSerializer):
    """
    Serializer for Passenger model, including nested User data.
    Handles both read and write operations for passenger profiles.
    """
    
    # Nested user data - read-only for display
    user = UserSerializer(read_only=True)

    # Computed fields
    full_name = serializers.SerializerMethodField()
    profile_completion_percentage = serializers.SerializerMethodField()
    
    class Meta:
        model = Passenger
        fields: tuple[str, ...] = (
            # Primary key
            'user',
            
            # Personal information
            'full_name',
            'home_address',
            'work_address',
            'emergency_contact_name',
            'emergency_contact_phone',
            
            # Preferences
            'preferred_payment_method',
            'preferred_car_type',
            
            # Statistics
            'average_rating',
            'total_rides',
            
            # Status fields
            'is_phone_verified',
            'profile_completion_percentage',
            'is_profile_complete',
            
            # Timestamps
            'created_at',
            'updated_at',
        )
        read_only_fields: tuple[str, ...] = (
            'user',
            'full_name',
            'profile_completion_percentage',
            'average_rating',
            'total_rides',
            'created_at',
            'updated_at',
        )
        
    def get_full_name(self, obj: Passenger) -> str:
        """
        Return the Passenger's full name from the related User model.
        """
        if obj.user.first_name and obj.user.last_name:
            return f"{obj.user.first_name} {obj.user.last_name}".strip()
        return obj.user.email.split('@')[0]  # Fallback to email username (if names are not set)
    
    def get_profile_completion_percentage(self, obj: Passenger) -> int:
        """
        Calculate profile completion percentage based on filled fields.
        """
        total_fields: int = 6  # Total fields considered for completion
        completed_fields: int = 0
        
        # Check user fields
        if obj.user.first_name:
            completed_fields += 1
        if obj.user.last_name:
            completed_fields += 1
        if obj.user.phone_number and obj.is_phone_verified:
            completed_fields += 1
        
        # Check passenger-specific fields
        if obj.home_address:
            completed_fields += 1
        if obj.emergency_contact_name:
            completed_fields += 1
        if obj.emergency_contact_phone:
            completed_fields += 1

        # Calculate and return the completion percentage (fixed return type)
        return int((completed_fields / total_fields * 100)) if total_fields > 0 else 0
    
    def validate_emergency_contact_phone(self, value: str) -> str:
        """
        Validate the emergency contact phone number format.
        """
        if value and not value.startswith('+'):
            raise serializers.ValidationError("Emergency contact phone must start with '+'.")
        return value
    
    def validate(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate the entire Passenger data.
        """
        
        # If emergency contact name is provided, phone must also be provided
        emergency_name: Optional[str] = data.get('emergency_contact_name')
        emergency_phone: Optional[str] = data.get('emergency_contact_phone')
        
        if emergency_name and not emergency_phone:
            raise serializers.ValidationError({
                'emergency_contact_phone': "Phone number is required when emergency contact name is provided."
            })
            
        return data


class PassengerCreateSerializer(serializers.ModelSerializer):
    """
    Serializer for creating new passenger profiles.
    Separate from the main serializer to handle creation logic.
    """
    
    class Meta:
        model = Passenger
        fields: tuple[str, ...] = (
            'home_address',
            'work_address',
            'emergency_contact_name',
            'emergency_contact_phone',
            'preferred_payment_method',
            'preferred_car_type',
        )
    
    def create(self, validated_data: Dict[str, Any]) -> Passenger:
        """
        Create a new Passenger profile linked to the authenticated user.
        """
        
        # Get the user from the context (passed during serializer initialization)
        user = self.context['request'].user
        
        # Ensure the user is of type 'passenger'
        if user.user_type != 'passenger':
            raise serializers.ValidationError("Only users with type 'passenger' can create passenger profiles.")
        
        # Create the passenger profile
        passenger: Passenger = Passenger.objects.create(user=user, **validated_data)
        
        # Update user's profile completion status
        passenger.is_profile_complete = self._calculate_profile_completion(passenger)
        passenger.save()
        
        return passenger
    
    def _calculate_profile_completion(self, passenger: Passenger) -> bool:
        """
        Helper method to determine if the profile is complete.
        A profile is considered complete if all key fields are filled.
        """
        required_fields: list[bool] = [
            bool(passenger.user.first_name),
            bool(passenger.user.last_name),
            bool(passenger.home_address),
            bool(passenger.emergency_contact_name),
            bool(passenger.emergency_contact_phone),
            passenger.is_phone_verified,
        ]
        
        return all(required_fields)