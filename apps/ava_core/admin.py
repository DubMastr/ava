from django.contrib import admin
from apps.ava_core.models import Module, UserPreference, User, SystemConfig

admin.site.register(Module)
admin.site.register(UserPreference)
admin.site.register(SystemConfig)
