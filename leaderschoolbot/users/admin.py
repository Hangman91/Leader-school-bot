from django.contrib import admin
from .forms import UserForm
from .models import User, Message, Call


@admin.register(User)
class ProfileAdmin(admin.ModelAdmin):
    list_display = (
        'first_last_name',
        'external_id',
        'name',
        'access_level',
        'count'
    )
    form = UserForm
    fields = (
        'name',
        'first_last_name',
        'access_level'
    )
    list_filter = (
        'first_last_name',
        'access_level'
    )
    search_fields = (
        'first_last_name',
    )

    def count(self, obj):
        result = Message.objects.filter(user=obj).count()
        return result

    count.short_description = "Количество сообщений"


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'user',
        'first_last_name',
        'text',
        'created_at'
    )
    search_fields = (
        'user__first_last_name',
    )

    def first_last_name(self, obj):
        author = User.objects.get(id=obj.user_id)
        return author.first_last_name


@admin.register(Call)
class CallAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'user',
        'message',
        'created_at'
    )
