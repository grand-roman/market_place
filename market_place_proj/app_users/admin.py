from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from app_users.models import User


@admin.register(User)
class UserAdmin(UserAdmin):
    change_user_password_template = None
    fieldsets = (
        (
            None,
            {'fields': ('email', 'is_email_verified', 'username', 'password')},
        ),
        (
            'Личная информация',
            {'fields': ('full_name', 'phone', 'avatar',)},
        ),
        (
            'Permissions',
            {
                'fields': (
                    'is_active',
                    'is_staff',
                    'is_superuser',
                    'groups',
                    'user_permissions',
                ),
            },
        ),
        ('Important dates', {'fields': ('last_login', 'date_joined')}),
    )
    add_fieldsets = (
        (
            None,
            {
                'classes': ('wide',),
                'fields': (
                    'email',
                    'is_email_verified',
                    'username',
                    'password1',
                    'password2',
                    'phone',
                ),
            },
        ),
    )
    list_display = ('id', 'username', 'email', 'is_staff', 'is_email_verified')
    list_display_links = ('username',)
    list_filter = (
        'is_staff',
        'is_superuser',
        'is_active',
        'is_email_verified',
        'groups'
    )
    search_fields = ('full_name', 'email', 'username')
    ordering = ('pk',)
    filter_horizontal = (
        'groups',
        'user_permissions',
    )
