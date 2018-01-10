from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import User

# Register your models here.

from .models import Profile, State, AmbulancePermission, HospitalPermission

# Define an inline admin descriptor for Profile model
# which acts a bit like a singleton
class ProfileInline(admin.StackedInline):
    model = Profile
    can_delete = False
    verbose_name_plural = 'profile'

class StateInline(admin.StackedInline):
    model = State
    can_delete = False
    verbose_name_plural = 'state'
    
# Define a new User admin
class UserAdmin(BaseUserAdmin):
    inlines = (ProfileInline, StateInline)

# Re-register UserAdmin
admin.site.unregister(User)
admin.site.register(User, UserAdmin)