from django.db import models
from django.contrib.auth.models import User

from xmmcg.settings import DEFAULT_USER_TOKENS


class UserProfile(models.Model):
    """用户扩展信息模型"""
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    token = models.IntegerField(default=DEFAULT_USER_TOKENS, help_text='用户虚拟货币余额')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = '用户资料'
        verbose_name_plural = '用户资料'

    def __str__(self):
        return f"{self.user.username}'s profile"
