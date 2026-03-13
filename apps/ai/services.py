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


def calculate_job_match(user_skills, job_skills_text):
    """Calculate match score between user skills and job requirements using AI.
    
    Args:
        user_skills: List of user's skill names
        job_skills_text: Job requirements/skills text
    
    Returns:
        dict with match_score, matched_skills, missing_skills, recommendations
    """
    if not OpenAI:
        return _calculate_match_fallback(user_skills, job_skills_text)
    
    api_key = os.getenv('OPENAI_API_KEY')
    if not api_key:
        return _calculate_match_fallback(user_skills, job_skills_text)
    
    client = OpenAI(api_key=api_key)
    
    # Parse job skills from text
    job_skills_list = [s.strip() for s in job_skills_text.split(',')] if job_skills_text else []
    user_skills_list = [s.strip() for s in user_skills] if user_skills else []
    
    prompt = f"""
You are a job matching expert. Calculate the match score between a candidate's skills and job requirements.

CANDIDATE SKILLS:
{', '.join(user_skills_list) if user_skills_list else 'No skills listed'}

JOB REQUIREMENTS:
{job_skills_text if job_skills_text else 'No requirements provided'}

Return a JSON object with:
{{
    "match_score": 0-100,
    "matched_skills": ["skill1", "skill2"],
    "missing_skills": ["skill3"],
    "recommendations": ["recommendation1", "recommendation2"],
    "analysis": "Brief analysis of the match"
}}

Only output the JSON object (no explanation).
"""
    
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            max_tokens=1000,
        )
        content = response.choices[0].message.content
        
        # Clean up
        content = content.strip()
        if content.startswith('```json'):
            content = content[7:]
        if content.startswith('```'):
            content = content[3:]
        if content.endswith('```'):
            content = content[:-3]
        content = content.strip()
        
        import json
        result = json.loads(content)
        return result
        
    except Exception as e:
        logger.error(f'Job match calculation failed: {e}')
        return _calculate_match_fallback(user_skills, job_skills_text)


def _calculate_match_fallback(user_skills, job_skills_text):
    """Fallback simple matching without AI"""
    user_skills_lower = [s.lower() for s in (user_skills or [])]
    job_skills_list = [s.strip() for s in (job_skills_text or '').split(',')]
    
    matched = []
    missing = []
    
    for skill in job_skills_list:
        skill_lower = skill.lower().strip()
        if any(skill_lower in user_skill or user_skill in skill_lower for user_skill in user_skills_lower):
            matched.append(skill)
        else:
            missing.append(skill)
    
    total = len(job_skills_list) or 1
    score = int((len(matched) / total) * 100)
    
    return {
        'match_score': score,
        'matched_skills': matched,
        'missing_skills': missing,
        'recommendations': [
            'Add missing skills to your profile' if missing else 'Your skills match well!',
            'Tailor your resume to highlight matched skills'
        ],
        'analysis': f'Matched {len(matched)} out of {len(job_skills_list)} skills'
    }


def optimize_resume(job_description, resume_text=''):
    """Analyze and optimize resume for a job using AI.
    
    Args:
        job_description: Job description text
        resume_text: Current resume text (optional)
    
    Returns:
        dict with missing_keywords, improvement_suggestions, resume_score
    """
    if not OpenAI:
        return _optimize_resume_fallback(job_description)
    
    api_key = os.getenv('OPENAI_API_KEY')
    if not api_key:
        return _optimize_resume_fallback(job_description)
    
    client = OpenAI(api_key=api_key)
    
    prompt = f"""
You are a resume optimization expert. Analyze the job description and provide recommendations to improve the resume.

JOB DESCRIPTION:
{job_description[:3000]}

CURRENT RESUME:
{resume_text[:1000] if resume_text else 'No resume provided'}

Return a JSON object with:
{{
    "missing_keywords": ["keyword1", "keyword2"],
    "improvement_suggestions": ["suggestion1", "suggestion2"],
    "resume_score": 0-100,
    "ats_friendly_score": 0-100,
    "action_items": ["action1", "action2"]
}}

Only output the JSON object (no explanation).
"""
    
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.5,
            max_tokens=1500,
        )
        content = response.choices[0].message.content
        
        # Clean up
        content = content.strip()
        if content.startswith('```json'):
            content = content[7:]
        if content.startswith('```'):
            content = content[3:]
        if content.endswith('```'):
            content = content[:-3]
        content = content.strip()
        
        import json
        result = json.loads(content)
        return result
        
    except Exception as e:
        logger.error(f'Resume optimization failed: {e}')
        return _optimize_resume_fallback(job_description)


def _optimize_resume_fallback(job_description):
    """Fallback resume optimization without AI"""
    job_words = set(job_description.lower().split())
    
    # Common keywords to look for
    common_keywords = ['experience', 'skills', 'team', 'project', 'lead', 'manage', 
                       'develop', 'design', 'implement', 'test', 'analysis', 'communication']
    
    found = [kw for kw in common_keywords if kw in job_words]
    missing = [kw for kw in common_keywords if kw not in job_words][:5]
    
    return {
        'missing_keywords': missing,
        'improvement_suggestions': [
            'Quantify your achievements with numbers',
            'Use action verbs to describe your experience',
            'Tailor your summary to the job description'
        ],
        'resume_score': 60,
        'ats_friendly_score': 70,
        'action_items': [
            'Add more relevant keywords from the job description',
            'Ensure proper formatting for ATS systems'
        ]
    }
