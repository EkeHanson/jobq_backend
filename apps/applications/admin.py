from django.contrib import admin
from .models import Application, StatusHistory

admin.site.register(Application)
admin.site.register(StatusHistory)
