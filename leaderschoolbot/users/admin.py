from django.contrib import admin
from .forms import UserForm
from .models import User


@admin.register(User)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ('id', 'external_id', 'name')
    form = UserForm