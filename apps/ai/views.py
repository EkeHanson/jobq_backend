from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView
from django.shortcuts import get_object_or_404

from .models import InterviewPrep
from .serializers import InterviewPrepSerializer, InterviewPrepCreateSerializer
from .services import generate_interview_prep

# AI extraction helper
from apps.ai.services import extract_job_data


class InterviewPrepViewSet(viewsets.ModelViewSet):
    """ViewSet for managing interview preparation content"""
    serializer_class = InterviewPrepSerializer
    permission_classes = [permissions.IsAuthenticated]
    lookup_field = 'prep_id'

    def get_queryset(self):
        return InterviewPrep.objects.filter(user=self.request.user)

    def create(self, request, *args, **kwargs):
        """Create a new interview prep and generate content"""
        serializer = InterviewPrepCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        data = serializer.validated_data
        
        # Create the interview prep record
        interview_prep = InterviewPrep.objects.create(
            user=request.user,
            application_id=data.get('application_id'),
            job_title=data['job_title'],
            company_name=data['company_name'],
            status='processing'
        )
        
        # Get user profile for personalized recommendations
        user_profile = None
        try:
            from apps.profiles.models import Profile
            profile = Profile.objects.filter(user=request.user).first()
            if profile:
                user_profile = {
                    'skills': list(profile.skills.values('id', 'name')),
                    'experiences': list(profile.experiences.values('company', 'position', 'description'))
                }
        except Exception:
            pass
        
        # Generate interview prep content using AI
        try:
            prep_content = generate_interview_prep(
                job_title=data['job_title'],
                company_name=data['company_name'],
                job_description=data.get('job_description', ''),
                job_requirements=data.get('job_requirements', ''),
                job_skills=data.get('job_skills', ''),
                user_profile=user_profile
            )
            
            interview_prep.interview_questions = prep_content.get('interview_questions', [])
            interview_prep.skill_assessments = prep_content.get('skill_assessments', {})
            interview_prep.recommendations = prep_content.get('recommendations', [])
            interview_prep.company_insights = prep_content.get('company_insights', {})
            interview_prep.status = 'completed'
            interview_prep.save()
            
        except Exception as e:
            interview_prep.status = 'failed'
            interview_prep.save()
            return Response(
                {'error': f'Failed to generate interview prep: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        
        output_serializer = InterviewPrepSerializer(interview_prep)
        return Response(output_serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['post'])
    def regenerate(self, request, pk=None):
        """Regenerate interview prep content"""
        interview_prep = self.get_object()
        
        # Update status
        interview_prep.status = 'processing'
        interview_prep.save()
        
        # Get user profile
        user_profile = None
        try:
            from apps.profiles.models import Profile
            profile = Profile.objects.filter(user=request.user).first()
            if profile:
                user_profile = {
                    'skills': list(profile.skills.values('id', 'name')),
                    'experiences': list(profile.experiences.values('company', 'position', 'description'))
                }
        except Exception:
            pass
        
        # Regenerate content
        try:
            prep_content = generate_interview_prep(
                job_title=interview_prep.job_title,
                company_name=interview_prep.company_name,
                user_profile=user_profile
            )
            
            interview_prep.interview_questions = prep_content.get('interview_questions', [])
            interview_prep.skill_assessments = prep_content.get('skill_assessments', {})
            interview_prep.recommendations = prep_content.get('recommendations', [])
            interview_prep.company_insights = prep_content.get('company_insights', {})
            interview_prep.status = 'completed'
            interview_prep.save()
            
        except Exception as e:
            interview_prep.status = 'failed'
            interview_prep.save()
            return Response(
                {'error': f'Failed to regenerate: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        
        output_serializer = InterviewPrepSerializer(interview_prep)
        return Response(output_serializer.data)
