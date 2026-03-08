from rest_framework import viewsets, status, generics, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from django.shortcuts import get_object_or_404

from .models import Job, Company, ExtractionTask
from .serializers import JobSerializer, CompanySerializer, ExtractionTaskSerializer

# AI extraction helper
from apps.ai.services import extract_job_data


class JobViewSet(viewsets.ModelViewSet):
    queryset = Job.objects.all().order_by('-posted_at')
    serializer_class = JobSerializer
    permission_classes = [permissions.AllowAny]

    def get_queryset(self):
        qs = super().get_queryset()
        search = self.request.query_params.get('search')
        if search:
            qs = qs.filter(title__icontains=search)
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
