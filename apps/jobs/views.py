from rest_framework import viewsets, status, generics, permissions, pagination
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.filters import SearchFilter, OrderingFilter
from django.shortcuts import get_object_or_404
from django.db.models import Q
from django.utils import timezone

from .models import Job, Company, ExtractionTask, JobBookmark
from .serializers import JobSerializer, CompanySerializer, ExtractionTaskSerializer, JobBookmarkSerializer, BulkJobCreateSerializer

# AI extraction helper
from apps.ai.services import extract_job_data


class JobPagination(pagination.PageNumberPagination):
    page_size = 12
    page_size_query_param = 'page_size'
    max_page_size = 1000


class JobViewSet(viewsets.ModelViewSet):
    queryset = Job.objects.select_related('company').all().order_by('-posted_at')
    serializer_class = JobSerializer
    permission_classes = [permissions.AllowAny]
    pagination_class = JobPagination
    filter_backends = [SearchFilter, OrderingFilter]

    def get_permissions(self):
        if self.action in ['list', 'retrieve']:
            return [permissions.AllowAny()]
        if self.action in ['bookmark', 'unbookmark', 'bookmarks', 'save_application']:
            return [permissions.IsAuthenticated()]
        return [permissions.IsAdminUser()]
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
        
        # Industry filter
        industry = self.request.query_params.get('industry')
        if industry:
            qs = qs.filter(industry=industry)

        # Bookmarked filter
        bookmarked = self.request.query_params.get('bookmarked')
        if bookmarked and bookmarked.lower() == 'true':
            if self.request.user and self.request.user.is_authenticated:
                qs = qs.filter(bookmarks__user=self.request.user)
            else:
                qs = qs.none()

        archived = self.request.query_params.get('archived')
        if archived is None:
            qs = qs.filter(is_archived=False)
        elif archived.lower() == 'true':
            qs = qs.filter(is_archived=True)
        else:
            qs = qs.filter(is_archived=False)
        
        return qs

    @action(detail=True, methods=['post'], permission_classes=[permissions.IsAuthenticated])
    def bookmark(self, request, pk=None):
        """Bookmark a job for the current user"""
        job = self.get_object()
        bookmark, created = JobBookmark.objects.get_or_create(
            user=request.user,
            job=job
        )
        if created:
            return Response({'status': 'bookmarked', 'bookmark_id': bookmark.id}, status=status.HTTP_201_CREATED)
        return Response({'status': 'already bookmarked', 'bookmark_id': bookmark.id})

    @action(detail=True, methods=['delete'], permission_classes=[permissions.IsAuthenticated])
    def unbookmark(self, request, pk=None):
        """Remove bookmark from a job"""
        job = self.get_object()
        deleted, _ = JobBookmark.objects.filter(user=request.user, job=job).delete()
        if deleted:
            return Response({'status': 'unbookmarked'})
        return Response({'status': 'not bookmarked'}, status=status.HTTP_404_NOT_FOUND)

    @action(detail=False, methods=['get'], permission_classes=[permissions.IsAuthenticated])
    def bookmarks(self, request):
        """Get all bookmarked jobs for current user"""
        bookmarks = JobBookmark.objects.filter(user=request.user).order_by('-created_at')
        serializer = JobBookmarkSerializer(bookmarks, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['post'], permission_classes=[permissions.IsAuthenticated])
    def save_application(self, request, pk=None):
        """Save a job as an application for the current user"""
        from apps.applications.models import Application
        
        job = self.get_object()
        user = request.user
        
        # Check if already saved
        existing = Application.objects.filter(
            user=user,
            job_title=job.title,
            company_name=job.company.name,
            deleted_at__isnull=True
        ).first()
        
        if existing:
            return Response(
                {'detail': 'This job is already in your applications', 'application_id': existing.id},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Get the status from request (default to 'saved')
        application_status = request.data.get('status', 'saved')
        
        # Create application from job data
        application = Application.objects.create(
            user=user,
            job_title=job.title,
            company_name=job.company.name,
            status=application_status,
            description=job.description,
            requirements=job.requirements,
            applied_date=timezone.now().date() if application_status == 'applied' else None,
        )
        
        return Response(
            {
                'status': 'application_saved',
                'application_id': application.id,
                'message': f'Application for {job.title} at {job.company.name} has been saved'
            },
            status=status.HTTP_201_CREATED
        )

    @action(detail=True, methods=['post'], permission_classes=[permissions.IsAdminUser])
    def archive(self, request, pk=None):
        """Archive a job so it is hidden from active job listings."""
        job = self.get_object()
        job.is_archived = True
        job.archived_at = timezone.now()
        job.save(update_fields=['is_archived', 'archived_at'])
        return Response({'status': 'archived', 'archived_at': job.archived_at})

    @action(detail=True, methods=['post'], permission_classes=[permissions.IsAdminUser])
    def unarchive(self, request, pk=None):
        """Restore an archived job."""
        job = self.get_object()
        job.is_archived = False
        job.archived_at = None
        job.save(update_fields=['is_archived', 'archived_at'])
        return Response({'status': 'unarchived'})

    @action(detail=False, methods=['post'], permission_classes=[permissions.IsAdminUser])
    def bulk_create(self, request):
        """Bulk create jobs from a list of job data"""
        serializer = BulkJobCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        jobs_data = serializer.validated_data['jobs']
        created_jobs = []
        errors = []
        
        for idx, job_data in enumerate(jobs_data):
            try:
                company_data = job_data.get('company')
                company = None
                
                if company_data:
                    company_name = company_data.get('name') if isinstance(company_data, dict) else company_data
                    company, _ = Company.objects.get_or_create(
                        name=company_name,
                        defaults={
                            'website': company_data.get('website', '') if isinstance(company_data, dict) else '',
                            'description': company_data.get('description', '') if isinstance(company_data, dict) else ''
                        }
                    )
                else:
                    company, _ = Company.objects.get_or_create(name='Unknown Company')
                
                job = Job.objects.create(
                    title=job_data.get('title', 'Untitled'),
                    company=company,
                    location=job_data.get('location', ''),
                    industry=job_data.get('industry', 'Other'),
                    description=job_data.get('description', ''),
                    requirements=job_data.get('requirements', ''),
                    skills=job_data.get('skills', ''),
                    job_type=job_data.get('job_type', 'Full-time'),
                    experience_level=job_data.get('experience_level', 'Mid-Level'),
                    salary_min=job_data.get('salary_min'),
                    salary_max=job_data.get('salary_max'),
                    salary_currency=job_data.get('salary_currency', 'USD'),
                    application_link=job_data.get('application_link'),
                    application_email=job_data.get('application_email'),
                    created_by=request.user if request.user.is_authenticated else None
                )
                created_jobs.append(job)
            except Exception as e:
                errors.append({'index': idx, 'error': str(e), 'data': job_data})
        
        if created_jobs:
            jobs_serializer = JobSerializer(created_jobs, many=True, context={'request': request})
            return Response({
                'created': len(created_jobs),
                'jobs': jobs_serializer.data,
                'errors': errors if errors else None
            }, status=status.HTTP_201_CREATED if not errors else status.HTTP_207_MULTI_STATUS)
        
        return Response(
            {'detail': 'No jobs were created', 'errors': errors},
            status=status.HTTP_400_BAD_REQUEST
        )

    @action(detail=False, methods=['get'], permission_classes=[permissions.IsAdminUser])
    def stats(self, request):
        """Return aggregated job statistics for admin dashboard."""
        total_jobs = Job.objects.count()
        active_qs = Job.objects.filter(is_archived=False)
        active_jobs = active_qs.count()
        archived_jobs = Job.objects.filter(is_archived=True).count()
        remote_jobs = active_qs.filter(
            Q(job_type__icontains='remote') | Q(location__icontains='remote')
        ).count()
        full_time_jobs = active_qs.filter(job_type__icontains='Full-time').count()

        return Response({
            'total_jobs': total_jobs,
            'active_jobs': active_jobs,
            'archived_jobs': archived_jobs,
            'remote_jobs': remote_jobs,
            'full_time_jobs': full_time_jobs,
        })


class CompanyViewSet(viewsets.ModelViewSet):
    queryset = Company.objects.all().order_by('name')
    serializer_class = CompanySerializer

    def get_permissions(self):
        if self.action in ['list', 'retrieve']:
            return [permissions.AllowAny()]
        return [permissions.IsAdminUser()]


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


class JobAggregationView(generics.GenericAPIView):
    """API view for aggregating jobs from external sources"""
    permission_classes = [permissions.AllowAny]
    
    def get(self, request):
        """Get aggregated jobs from external sources"""
        query = request.query_params.get('query', '')
        location = request.query_params.get('location', '')
        num_jobs = int(request.query_params.get('limit', 20))
        source = request.query_params.get('source', 'all')  # all, remotive, adzuna, jooble
        
        from .aggregation import JobAggregationService
        
        if source == 'remotive':
            jobs = JobAggregationService.fetch_remotive_jobs(num_jobs=num_jobs)
        elif source == 'adzuna':
            jobs = JobAggregationService.fetch_adzuna_jobs(query, location, num_jobs)
        elif source == 'jooble':
            jobs = JobAggregationService.fetch_jooble_jobs(query, location, num_jobs)
        else:
            jobs = JobAggregationService.fetch_all_jobs(query, location, num_jobs)
        
        return Response({
            'count': len(jobs),
            'results': jobs
        })
    
    def post(self, request):
        """Save aggregated job to local database"""
        job_data = request.data
        
        if not request.user.is_authenticated:
            return Response(
                {'detail': 'Authentication required to save jobs'},
                status=status.HTTP_401_UNAUTHORIZED
            )
        
        # Get or create company
        company_name = job_data.get('company', 'Unknown Company')
        company, _ = Company.objects.get_or_create(
            name=company_name,
            defaults={'website': ''}
        )
        
        # Create job
        job = Job.objects.create(
            title=job_data.get('title', 'Untitled'),
            company=company,
            location=job_data.get('location', ''),
            description=job_data.get('description', ''),
            requirements=job_data.get('requirements', ''),
            skills=job_data.get('skills', ''),
            job_type=job_data.get('job_type', 'Full-time'),
            salary_min=job_data.get('salary_min'),
            salary_max=job_data.get('salary_max'),
            salary_currency=job_data.get('salary_currency', 'USD'),
            application_link=job_data.get('application_link', ''),
            created_by=request.user
        )
        
        serializer = JobSerializer(job)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
