from django.contrib import admin
from .models import (
    Profile,
    Skill,
    Experience,
    Education,
    Certification,
    Resume,
)

admin.site.register(Profile)
admin.site.register(Skill)
admin.site.register(Experience)
admin.site.register(Education)
admin.site.register(Certification)
admin.site.register(Resume)
