from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    ProfileViewSet,
    SkillViewSet,
    ExperienceViewSet,
    EducationViewSet,
    CertificationViewSet,
    ResumeViewSet,
    ResumeUploadView,
)

router = DefaultRouter()
router.register(r'profiles', ProfileViewSet, basename='profile')

# nested routers manual
profile_detail = DefaultRouter()
# not needed inside since frontend uses explicit paths

urlpatterns = [
    path('', include(router.urls)),
    path('profiles/<int:profile_pk>/skills/', SkillViewSet.as_view({'get': 'list', 'post': 'create'}), name='profile-skills'),
    path('profiles/<int:profile_pk>/skills/<int:pk>/', SkillViewSet.as_view({'put': 'update', 'delete': 'destroy'}), name='profile-skill-detail'),
    path('profiles/<int:profile_pk>/experiences/', ExperienceViewSet.as_view({'get': 'list', 'post': 'create'}), name='profile-experiences'),
    path('profiles/<int:profile_pk>/experiences/<int:pk>/', ExperienceViewSet.as_view({'put': 'update', 'delete': 'destroy'}), name='profile-experience-detail'),
    path('profiles/<int:profile_pk>/education/', EducationViewSet.as_view({'get': 'list', 'post': 'create'}), name='profile-education'),
    path('profiles/<int:profile_pk>/education/<int:pk>/', EducationViewSet.as_view({'put': 'update', 'delete': 'destroy'}), name='profile-education-detail'),
    path('profiles/<int:profile_pk>/certifications/', CertificationViewSet.as_view({'get': 'list', 'post': 'create'}), name='profile-certifications'),
    path('profiles/<int:profile_pk>/certifications/<int:pk>/', CertificationViewSet.as_view({'delete': 'destroy'}), name='profile-certification-detail'),
    path('profiles/<int:profile_pk>/resumes/upload/', ResumeUploadView.as_view({'post': 'create'}), name='profile-resume-upload'),
    path('profiles/<int:profile_pk>/resumes/', ResumeViewSet.as_view({'get': 'list'}), name='profile-resumes'),
    path('profiles/<int:profile_pk>/resumes/<int:pk>/', ResumeViewSet.as_view({'delete': 'destroy'}), name='profile-resume-detail'),
]
