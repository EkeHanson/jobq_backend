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
