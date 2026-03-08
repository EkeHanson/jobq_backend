from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.shortcuts import get_object_or_404

from .models import (
    Profile,
    Skill,
    Experience,
    Education,
    Certification,
    Resume,
)
from .serializers import (
    ProfileSerializer,
    SkillSerializer,
    ExperienceSerializer,
    EducationSerializer,
    CertificationSerializer,
    ResumeSerializer,
)
from .upload_utils import upload_file_dynamic


class ProfileViewSet(viewsets.ModelViewSet):
    queryset = Profile.objects.select_related('user').all()
    serializer_class = ProfileSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if not user.is_staff:
            return self.queryset.filter(user=user)
        return self.queryset

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class SkillViewSet(viewsets.ModelViewSet):
    serializer_class = SkillSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        profile_id = self.kwargs.get('profile_pk')
        return Skill.objects.filter(profile_id=profile_id)

    def perform_create(self, serializer):
        profile = get_object_or_404(Profile, pk=self.kwargs.get('profile_pk'), user=self.request.user)
        serializer.save(profile=profile)


class ExperienceViewSet(viewsets.ModelViewSet):
    serializer_class = ExperienceSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        profile_id = self.kwargs.get('profile_pk')
        return Experience.objects.filter(profile_id=profile_id)

    def perform_create(self, serializer):
        profile = get_object_or_404(Profile, pk=self.kwargs.get('profile_pk'), user=self.request.user)
        serializer.save(profile=profile)


class EducationViewSet(viewsets.ModelViewSet):
    serializer_class = EducationSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        profile_id = self.kwargs.get('profile_pk')
        return Education.objects.filter(profile_id=profile_id)

    def perform_create(self, serializer):
        profile = get_object_or_404(Profile, pk=self.kwargs.get('profile_pk'), user=self.request.user)
        serializer.save(profile=profile)


class CertificationViewSet(viewsets.ModelViewSet):
    serializer_class = CertificationSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        profile_id = self.kwargs.get('profile_pk')
        return Certification.objects.filter(profile_id=profile_id)

    def perform_create(self, serializer):
        profile = get_object_or_404(Profile, pk=self.kwargs.get('profile_pk'), user=self.request.user)
        serializer.save(profile=profile)


class ResumeUploadView(viewsets.ViewSet):
    permission_classes = [permissions.IsAuthenticated]

    def create(self, request, profile_pk=None):
        profile = get_object_or_404(Profile, pk=profile_pk, user=request.user)
        file_obj = request.FILES.get('file')
        
        if not file_obj:
            return Response({'error': 'No file provided'}, status=status.HTTP_400_BAD_REQUEST)
        
        # Get content type
        content_type = file_obj.content_type
        original_filename = file_obj.name
        file_size = file_obj.size
        
        try:
            # Upload to dynamic storage (compress by default)
            file_url = upload_file_dynamic(
                file_obj,
                original_filename,
                content_type,
                compress=True  # Compress as zip
            )
            
            # Create resume record with the URL
            resume = Resume.objects.create(
                profile=profile,
                file=file_url,  # Store the URL instead of file object
                original_filename=original_filename,
                file_size=file_size
            )
            
            serializer = ResumeSerializer(resume)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
            
        except Exception as e:
            return Response(
                {'error': f'Upload failed: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class ResumeViewSet(viewsets.ModelViewSet):
    serializer_class = ResumeSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        profile_id = self.kwargs.get('profile_pk')
        return Resume.objects.filter(profile_id=profile_id)
