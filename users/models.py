from django.contrib.auth.base_user import BaseUserManager, AbstractBaseUser
from django.contrib.auth.models import PermissionsMixin
from django.core.validators import RegexValidator
from django.db import models
from django.utils import timezone


class CustomUserManager(BaseUserManager):
    """
    Custom user model manager where email is the unique identifier
    for authentication instead of usernames.
    """
    def create_user(self, email, password, **extra_fields):
        """
        Create and save a User with the given email and password.
        """
        if not email:
            raise ValueError('The Email must be set')
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password, **extra_fields):
        """
        Create and save a SuperUser with the given email and password.
        """
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_active', True)

        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')
        return self.create_user(email, password, **extra_fields)



class User(AbstractBaseUser, PermissionsMixin):
    """
    Custom User model that uses email for authentication instead of usernames.
    """
    USER_TYPES = (
        ('passenger', 'Passenger'),
        ('rider', 'Rider'),
    )

    # Required fields for authentication
    email = models.EmailField(unique=True)

    # Custom fields
    user_type = models.CharField(max_length=20, choices=USER_TYPES)
    phone_number = models.CharField(
        max_length=15,
        unique=True,
        validators=[RegexValidator(r'^\+?1?\d{9,15}$')]
    )

    # Fields required by Django
    first_name = models.CharField(max_length=150, blank=True)
    last_name = models.CharField(max_length=150, blank=True)
    is_staff = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    date_joined = models.DateTimeField(default=timezone.now)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # Set the custom manager and the username field
    objects = CustomUserManager()
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []

    def __str__(self):
        return self.email
    
class Passenger(models.Model):
    """
    Passenger profile model that extends the User model functionality
    for passengers in the ride-sharing application.
    """
    # One-to-one relationship with the User model
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        primary_key=True,
        limit_choices_to={'user_type': 'passenger'}
        )
    
    # Passenger specific fields
    home_address = models.CharField(max_length=255, blank=True)
    work_address = models.CharField(max_length=255, blank=True)
    emergency_contact_name = models.CharField(max_length=150, blank=True)
    emergency_contact_phone = models.CharField(
        max_length=15,
        validators=[RegexValidator(r'^\+?1?\d{9,15}$')],
        blank=True
    )
    
    # Payment preferences
    preferred_payment_method = models.CharField(
        max_length=50, 
        choices=[
            ('cash', 'Cash'), 
            ('card', 'Credit/Debit Card'), 
            ('mobile_money', 'Mobile Money'), 
            ('wallet', 'Digital Wallet')
        ], 
        default='card'
        )
    
    # Ride preferences
    preferred_car_type = models.CharField(
        max_length=50,
        choices=[
            ('economy', 'Economy'),
            ('comfort', 'Comfort'),
            ('premium', 'Premium'),
            ('any', 'Any')
        ],
        default='economy'
        )
    
    # Rating and ride stats
    average_rating = models.DecimalField(
        max_digits=3, 
        decimal_places=2, 
        default=5.0
        )
    total_rides = models.PositiveIntegerField(default=0)
    
    # Profile completion and verification
    is_phone_verified = models.BooleanField(default=False)
    is_profile_complete = models.BooleanField(default=False)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'passengers'
        verbose_name = 'Passenger'
        verbose_name_plural = 'Passengers'
        
    def __str__(self) -> str:
        return f"Passenger: {self.user.email}"