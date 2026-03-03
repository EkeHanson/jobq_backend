from django.contrib import admin
from .models import Job, Company, ExtractionTask

admin.site.register(Job)
admin.site.register(Company)
admin.site.register(ExtractionTask)
