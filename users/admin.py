from django.contrib import admin
from .models import User
from .models import Passenger

# Register your models here.
admin.site.register(User)
admin.site.register(Passenger)