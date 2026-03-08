from rest_framework import viewsets, status, generics, permissions, pagination
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.filters import SearchFilter, OrderingFilter
from django.shortcuts import get_object_or_404
from django.db.models import Q

from .models import Job, Company, ExtractionTask
from .serializers import JobSerializer, CompanySerializer, ExtractionTaskSerializer

# AI extraction helper
from apps.ai.services import extract_job_data


class JobPagination(pagination.PageNumberPagination):
    page_size = 12
    page_size_query_param = 'page_size'
    max_page_size = 100


class JobViewSet(viewsets.ModelViewSet):
    queryset = Job.objects.select_related('company').all().order_by('-posted_at')
    serializer_class = JobSerializer
    permission_classes = [permissions.AllowAny]
    pagination_class = JobPagination
    filter_backends = [SearchFilter, OrderingFilter]
    search_fields = ['title', 'description', 'company__name', 'location']
    ordering_fields = ['posted_at', 'title']
    ordering = ['-posted_at']  # LIFO - newest first

    def get_queryset(self):
        qs = super().get_queryset()
        
        # Search query
        search = self.request.query_params.get('search')
        if search:
            qs = qs.filter(
                Q(title__icontains=search) |
                Q(description__icontains=search) |
                Q(company__name__icontains=search) |
                Q(location__icontains=search)
            )
        
        # Job type filter
        job_type = self.request.query_params.get('job_type')
        if job_type:
            qs = qs.filter(job_type=job_type)
        
        # Experience level filter
        experience_level = self.request.query_params.get('experience_level')
        if experience_level:
            qs = qs.filter(experience_level=experience_level)
        
        # Location filter
        location = self.request.query_params.get('location')
        if location:
            qs = qs.filter(location__icontains=location)
        
        return qs


class CompanyViewSet(viewsets.ModelViewSet):
    queryset = Company.objects.all().order_by('name')
    serializer_class = CompanySerializer
    permission_classes = [permissions.AllowAny]


class JobExtractView(generics.CreateAPIView):
    queryset = ExtractionTask.objects.all()
    serializer_class = ExtractionTaskSerializer
    permission_classes = [permissions.IsAuthenticated]

    def create(self, request, *args, **kwargs):
        text = request.data.get('job_text', '')
        task = ExtractionTask.objects.create(input_text=text)

        # attempt AI extraction; falls back to simple parsing on failure
        try:
            ai_result = extract_job_data(text)
            # Check if result is not empty (even empty dict is falsy, so check explicitly)
            if ai_result and isinstance(ai_result, dict) and len(ai_result) > 0:
                task.result = ai_result
                task.status = 'completed'
                task.save()
                return Response({'task_id': task.task_id, 'extracted': ai_result}, status=status.HTTP_201_CREATED)
            else:
                # Log why it fell back
                import logging
                logging.warning(f"AI extraction returned empty result, falling back to simple parsing. Result: {ai_result}")
        except Exception as e:
            import logging
            logging.error(f"AI extraction failed: {e}")
            pass

        # if the AI didn't return anything, fall back to naive split
        if task.status != 'completed':
            lines = [l.strip() for l in text.splitlines() if l.strip()]
            result = {}
            if lines:
                result['title'] = lines[0]
                if len(lines) > 1:
                    result['company'] = lines[1]
            task.status = 'completed'
            task.result = result
            task.save()

        return Response({'task_id': task.task_id}, status=status.HTTP_201_CREATED)


class JobExtractStatusView(generics.RetrieveAPIView):
    queryset = ExtractionTask.objects.all()
    serializer_class = ExtractionTaskSerializer
    lookup_field = 'task_id'
    permission_classes = [permissions.IsAuthenticated]


class JobExtractResultView(generics.RetrieveAPIView):
    queryset = ExtractionTask.objects.all()
    serializer_class = ExtractionTaskSerializer
    lookup_field = 'task_id'
    permission_classes = [permissions.IsAuthenticated]
