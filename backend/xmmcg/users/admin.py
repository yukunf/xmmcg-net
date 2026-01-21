from django.contrib import admin
from .models import UserProfile


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ('user','qqid', 'token', 'created_at', 'updated_at')
    list_filter = ('created_at', 'updated_at')
    search_fields = ('user__username', 'user__email')
    readonly_fields = ('created_at', 'updated_at')
    actions = ['reset_tokens']
    fieldsets = (
        ('用户信息', {
            'fields': ('user',)
        }),
        ('QQ号', {
            'fields': ('qqid',)
        }),
        ('虚拟货币', {
            'fields': ('token',)
        }),
        ('时间戳', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    @admin.action(description='重置token数量至默认')
    def reset_tokens(self, request, queryset):
        from django.conf import settings
        default_tokens = getattr(settings, 'DEFAULT_USER_TOKENS', 1000)
        updated_count = queryset.update(token=default_tokens)
        self.message_user(request, f'已将 {updated_count} 个用户的token数量重置为默认值 {default_tokens}。')

