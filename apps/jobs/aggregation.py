import os
import logging
import requests
from django.utils import timezone

logger = logging.getLogger(__name__)


class JobAggregationService:
    """Service to aggregate jobs from external APIs"""
    
    @staticmethod
    def fetch_adzuna_jobs(query='', location='', num_jobs=20):
        """
        Fetch jobs from Adzuna API.
        
        Args:
            query: Job search query
            location: Location to search
            num_jobs: Number of jobs to fetch
        
        Returns:
            List of job dictionaries
        """
        app_id = os.getenv('ADZUNA_APP_ID')
        app_key = os.getenv('ADZUNA_APP_KEY')
        
        if not app_id or not app_key:
            logger.warning('Adzuna credentials not configured')
            return []
        
        try:
            url = 'https://api.adzuna.com/v1/api/jobs/us/search'
            params = {
                'app_id': app_id,
                'app_key': app_key,
                'what': query,
                'where': location,
                'results_per_page': num_jobs,
                'sort_by': 'relevance'
            }
            
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            jobs = []
            for item in data.get('results', []):
                job = {
                    'title': item.get('title', ''),
                    'company': item.get('company', {}).get('display_name', ''),
                    'location': item.get('location', {}).get('display_name', ''),
                    'description': item.get('description', ''),
                    'salary_min': item.get('salary_min'),
                    'salary_max': item.get('salary_max'),
                    'salary_currency': item.get('currency', 'USD'),
                    'job_type': JobAggregationService._map_adzuna_contract(item.get('contract_type', '')),
                    'application_link': item.get('redirect_url', ''),
                    'source': 'Adzuna',
                    'source_url': item.get('id', ''),
                    'posted_at': item.get('created', timezone.now().isoformat()),
                }
                jobs.append(job)
            
            return jobs
            
        except requests.RequestException as e:
            logger.error(f'Adzuna API error: {e}')
            return []
    
    @staticmethod
    def fetch_remotive_jobs(category='dev', num_jobs=20):
        """
        Fetch jobs from Remotive API.
        
        Args:
            category: Job category (dev, it, etc.)
            num_jobs: Number of jobs to fetch
        
        Returns:
            List of job dictionaries
        """
        try:
            url = f'https://remotive.com/api/remote-jobs?category={category}&limit={num_jobs}'
            
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            jobs = []
            for item in data.get('jobs', []):
                job = {
                    'title': item.get('title', ''),
                    'company': item.get('company_name', ''),
                    'location': item.get('candidate_required_location', 'Remote'),
                    'description': item.get('description', ''),
                    'salary_min': None,
                    'salary_max': None,
                    'salary_currency': 'USD',
                    'job_type': 'Remote',
                    'application_link': item.get('url', ''),
                    'source': 'Remotive',
                    'source_url': item.get('id', ''),
                    'posted_at': item.get('published_at', timezone.now().isoformat()),
                }
                
                # Parse salary if available
                if item.get('salary'):
                    # Salary format: "100000-120000 USD/year"
                    salary_parts = item['salary'].split()
                    if salary_parts:
                        try:
                            job['salary_min'] = int(salary_parts[0].replace(',', ''))
                            if len(salary_parts) > 1 and salary_parts[1].replace(',', '').isdigit():
                                job['salary_max'] = int(salary_parts[1].replace(',', ''))
                        except (ValueError, IndexError):
                            pass
                
                jobs.append(job)
            
            return jobs
            
        except requests.RequestException as e:
            logger.error(f'Remotive API error: {e}')
            return []
    
    @staticmethod
    def fetch_jooble_jobs(keywords='', location='', num_jobs=20):
        """
        Fetch jobs from Jooble API.
        
        Args:
            keywords: Job search keywords
            location: Location to search
            num_jobs: Number of jobs to fetch
        
        Returns:
            List of job dictionaries
        """
        api_key = os.getenv('JOOBLE_API_KEY')
        
        if not api_key:
            logger.warning('Jooble API key not configured')
            return []
        
        try:
            url = 'https://jooble.org/api/'
            
            payload = {
                'keywords': keywords,
                'location': location,
                'limit': num_jobs
            }
            
            headers = {
                'Content-Type': 'application/json',
                'Authorization': f'Bearer {api_key}'
            }
            
            response = requests.post(url, json=payload, headers=headers, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            jobs = []
            for item in data.get('jobs', []):
                job = {
                    'title': item.get('title', ''),
                    'company': item.get('company', ''),
                    'location': item.get('location', ''),
                    'description': item.get('snippet', item.get('description', '')),
                    'salary_min': None,
                    'salary_max': None,
                    'salary_currency': 'USD',
                    'job_type': JobAggregationService._map_jooble_type(item.get('type', '')),
                    'application_link': item.get('link', ''),
                    'source': 'Jooble',
                    'source_url': item.get('id', ''),
                    'posted_at': item.get('published', timezone.now().isoformat()),
                }
                
                # Parse salary if available
                salary = item.get('salary', '')
                if salary:
                    # Format: "100000 - 120000"
                    import re
                    numbers = re.findall(r'\\d+', salary.replace(',', ''))
                    if numbers:
                        job['salary_min'] = int(numbers[0]) if len(numbers) > 0 else None
                        job['salary_max'] = int(numbers[1]) if len(numbers) > 1 else None
                
                jobs.append(job)
            
            return jobs
            
        except requests.RequestException as e:
            logger.error(f'Jooble API error: {e}')
            return []
    
    @staticmethod
    def fetch_all_jobs(query='', location='', num_jobs=10):
        """
        Fetch jobs from all available sources.
        
        Args:
            query: Job search query
            location: Location to search
            num_jobs: Number of jobs per source
        
        Returns:
            List of all jobs sorted by date
        """
        all_jobs = []
        
        # Fetch from Remotive (free, remote jobs only)
        remote_jobs = JobAggregationService.fetch_remotive_jobs(num_jobs=num_jobs)
        all_jobs.extend(remote_jobs)
        
        # Fetch from Adzuna
        adzuna_jobs = JobAggregationService.fetch_adzuna_jobs(query, location, num_jobs)
        all_jobs.extend(adzuna_jobs)
        
        # Sort by posted date (newest first)
        all_jobs.sort(key=lambda x: x.get('posted_at', ''), reverse=True)
        
        # Return unique jobs (by title + company)
        seen = set()
        unique_jobs = []
        for job in all_jobs:
            key = (job.get('title', '').lower(), job.get('company', '').lower())
            if key not in seen:
                seen.add(key)
                unique_jobs.append(job)
        
        return unique_jobs[:num_jobs * 3]  # Return up to 3x num_jobs
    
    @staticmethod
    def _map_adzuna_contract(contract_type):
        """Map Adzuna contract types to our job types"""
        mapping = {
            'permanent': 'Full-time',
            'contract': 'Contract',
            'temp': 'Part-time',
            'internship': 'Internship',
        }
        return mapping.get(contract_type.lower() if contract_type else '', 'Full-time')
    
    @staticmethod
    def _map_jooble_type(job_type):
        """Map Jooble job types to our job types"""
        mapping = {
            'full': 'Full-time',
            'part': 'Part-time',
            'contract': 'Contract',
            'internship': 'Internship',
            'remote': 'Remote',
        }
        return mapping.get(job_type.lower() if job_type else '', 'Full-time')
