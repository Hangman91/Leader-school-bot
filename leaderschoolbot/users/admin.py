from django.contrib import admin
from .forms import UserForm
from .models import User, Message


@admin.register(User)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ('id', 'external_id', 'name', 'first_last_name')
    form = UserForm


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'text', 'created_at')
