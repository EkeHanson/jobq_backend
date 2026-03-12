import os
import logging
import json

try:
    from openai import OpenAI
except ImportError:
    OpenAI = None

logger = logging.getLogger(__name__)


def extract_job_data(text: str) -> dict:
    """Use OpenAI ChatGPT to parse a job posting text into structured fields.

    Returns a dict containing whatever keys could be found; typical fields include
    ``title``, ``company``, ``location``, ``description`` and ``requirements``.

    If the OpenAI client is not installed or the API key is missing, a simple
    heuristic extraction is performed and an empty result is returned.
    """
    if not OpenAI:
        logger.warning('openai package not installed, skipping AI extraction')
        return {}

    api_key = os.getenv('OPENAI_API_KEY')
    if not api_key:
        logger.warning('OPENAI_API_KEY not set, skipping AI extraction')
        return {}

    client = OpenAI(api_key=api_key)

    # craft a prompt asking for JSON output with comprehensive fields
    prompt = (
        "You are given the full text of a job posting. Extract ALL relevant information and return a JSON object. "
        "Include these fields when available: "
        "title, company, location, location_type (remote/hybrid/onsite), employment_type (full-time/part-time/contract), "
        "experience_level, salary_min, salary_max, salary_currency, salary_period (yearly/monthly/hourly), "
        "description, responsibilities, requirements, skills (as an array), benefits, company_description, "
        "contact_email, application_url, job_url, posted_date, deadline, is_remote, "
        "number_of_openings, department, reporting_to, travel_required." 
        "If some fields are not present, use null. "
        "Only output the JSON object (no surrounding explanation). "
        f"Here is the job posting text:\n{text}"
    )

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            temperature=0,
            max_tokens=2000,
        )
        content = response.choices[0].message.content
        
        # Clean up the response - sometimes AI adds markdown code blocks
        content = content.strip()
        if content.startswith('```json'):
            content = content[7:]
        if content.startswith('```'):
            content = content[3:]
        if content.endswith('```'):
            content = content[:-3]
        content = content.strip()
        
        # Attempt to parse JSON
        data = json.loads(content)
        
        # Normalize field names to match expected format
        normalized = {}
        
        # Title
        if 'title' in data:
            normalized['title'] = data['title']
        elif 'job_title' in data:
            normalized['title'] = data['job_title']
        
        # Company
        if 'company' in data:
            normalized['company'] = data['company']
        elif 'company_name' in data:
            normalized['company'] = data['company_name']
        
        # Copy other fields
        for key in ['location', 'location_type', 'employment_type', 'experience_level',
                    'salary_min', 'salary_max', 'salary_currency', 'salary_period',
                    'description', 'responsibilities', 'requirements', 'skills',
                    'benefits', 'company_description', 'contact_email', 'application_url',
                    'job_url', 'posted_date', 'deadline', 'is_remote',
                    'number_of_openings', 'department', 'reporting_to', 'travel_required']:
            if key in data:
                normalized[key] = data[key]
        
        return normalized
        
    except json.JSONDecodeError as exc:
        logger.error('failed to parse JSON from OpenAI response: %s', exc)
        return {'raw': content}
    except Exception as exc:
        logger.error('OpenAI API call failed: %s', exc)
        return {}


def generate_interview_prep(job_title, company_name, job_description='', job_requirements='', job_skills='', user_profile=None):
    """Generate interview preparation content using OpenAI.
    
    Args:
        job_title: Title of the job position
        company_name: Name of the company
        job_description: Job description text
        job_requirements: Job requirements text
        job_skills: Required skills (comma-separated or text)
        user_profile: User's profile data (skills, experiences, etc.)
    
    Returns:
        dict containing:
        - interview_questions: List of categorized interview questions
        - skill_assessments: Skills gap analysis
        - recommendations: Personalized recommendations
        - company_insights: Information about the company
    """
    if not OpenAI:
        logger.warning('openai package not installed, skipping AI interview prep')
        return _generate_fallback_interview_prep(job_title, company_name)

    api_key = os.getenv('OPENAI_API_KEY')
    if not api_key:
        logger.warning('OPENAI_API_KEY not set, skipping AI interview prep')
        return _generate_fallback_interview_prep(job_title, company_name)

    client = OpenAI(api_key=api_key)
    
    # Build the prompt
    profile_context = ""
    if user_profile:
        skills = user_profile.get('skills', [])
        experiences = user_profile.get('experiences', [])
        if skills:
            profile_context += f"User's skills: {', '.join([s.get('name', str(s)) for s in skills])}"
        if experiences:
            exp_summary = [f"{e.get('position', '')} at {e.get('company', '')}" for e in experiences[:3]]
            profile_context += f"\nUser's experience: {', '.join(exp_summary)}"
    
    prompt = f"""
You are an expert career coach and interview preparation specialist. Generate comprehensive interview preparation content for a job seeker.

JOB DETAILS:
- Position: {job_title}
- Company: {company_name}
- Description: {job_description[:2000] if job_description else 'Not provided'}
- Requirements: {job_requirements[:1000] if job_requirements else 'Not provided'}
- Required Skills: {job_skills if job_skills else 'Not provided'}

USER PROFILE:
{profile_context}

Generate a JSON object with the following structure:
{{
    "interview_questions": [
        {{
            "category": "Technical",
            "question": "Question text here",
            "tips": ["Tip 1", "Tip 2"]
        }}
    ],
    "skill_assessments": {{
        "matched_skills": ["skill1", "skill2"],
        "gap_skills": ["skill3"],
        "assessment_notes": "Notes about skill match"
    }},
    "recommendations": [
        {{"title": "Recommendation title", "description": "Description", "priority": "high/medium/low"}}
    ],
    "company_insights": {{
        "industry": "Industry name",
        "key_values": ["Value 1", "Value 2"],
        "tips": ["Tip for this company"]
    }}
}}

Only output the JSON object (no surrounding explanation). Make the questions realistic and specific to the job description provided.
"""

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
            max_tokens=3000,
        )
        content = response.choices[0].message.content
        
        # Clean up the response
        content = content.strip()
        if content.startswith('```json'):
            content = content[7:]
        if content.startswith('```'):
            content = content[3:]
        if content.endswith('```'):
            content = content[:-3]
        content = content.strip()
        
        # Parse JSON
        data = json.loads(content)
        
        return {
            'interview_questions': data.get('interview_questions', []),
            'skill_assessments': data.get('skill_assessments', {}),
            'recommendations': data.get('recommendations', []),
            'company_insights': data.get('company_insights', {})
        }
        
    except json.JSONDecodeError as exc:
        logger.error('failed to parse JSON from OpenAI response: %s', exc)
        return _generate_fallback_interview_prep(job_title, company_name)
    except Exception as exc:
        logger.error('OpenAI API call failed: %s', exc)
        return _generate_fallback_interview_prep(job_title, company_name)


def _generate_fallback_interview_prep(job_title, company_name):
    """Generate basic interview prep content without AI"""
    return {
        'interview_questions': [
            {
                'category': 'General',
                'question': f'Tell me about yourself and why you are interested in the {job_title} position at {company_name}.',
                'tips': ['Keep it concise (2-3 minutes)', 'Focus on relevant experience', 'Show enthusiasm']
            },
            {
                'category': 'Technical',
                'question': f'What are your technical strengths relevant to this {job_title} role?',
                'tips': ['Highlight key skills', 'Provide specific examples', 'Be honest about your level']
            },
            {
                'category': 'Behavioral',
                'question': 'Describe a challenging project you worked on and how you overcame obstacles.',
                'tips': ['Use the STAR method', 'Focus on your specific contribution', 'Learn from the experience']
            }
        ],
        'skill_assessments': {
            'matched_skills': [],
            'gap_skills': [],
            'assessment_notes': 'Add your skills to your profile to get personalized assessment.'
        },
        'recommendations': [
            {'title': 'Research the Company', 'description': 'Learn about their products, culture, and recent news', 'priority': 'high'},
            {'title': 'Practice Common Questions', 'description': 'Prepare answers for typical interview questions', 'priority': 'high'},
            {'title': 'Prepare Your Questions', 'description': 'Have thoughtful questions ready for the interviewer', 'priority': 'medium'}
        ],
        'company_insights': {
            'industry': 'Research this company',
            'key_values': ['Research company values'],
            'tips': ['Check their website and social media']
        }
    }
