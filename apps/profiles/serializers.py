from rest_framework import serializers
from .models import (
    Profile,
    Skill,
    Experience,
    Education,
    Certification,
    Resume,
)


class SkillSerializer(serializers.ModelSerializer):
    class Meta:
        model = Skill
        fields = ['id', 'name']


class ExperienceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Experience
        fields = ['id', 'company', 'position', 'start_date', 'end_date', 'description']


class EducationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Education
        fields = ['id', 'school', 'degree', 'field_of_study', 'start_date', 'end_date']


class CertificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Certification
        fields = ['id', 'title', 'institution', 'date_obtained']


class ResumeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Resume
        fields = ['id', 'file', 'uploaded_at']


class ProfileSerializer(serializers.ModelSerializer):
    skills = SkillSerializer(many=True, read_only=True)
    experiences = ExperienceSerializer(many=True, read_only=True)
    education = EducationSerializer(many=True, read_only=True)
    certifications = CertificationSerializer(many=True, read_only=True)
    resumes = ResumeSerializer(many=True, read_only=True)

    class Meta:
        model = Profile
        fields = [
            'id',
            'user',
            'bio',
            'location',
            'website',
            'skills',
            'experiences',
            'education',
            'certifications',
            'resumes',
        ]
        read_only_fields = ['user']
