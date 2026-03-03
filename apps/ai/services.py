import os
import logging

try:
    import openai
except ImportError:
    openai = None

logger = logging.getLogger(__name__)


def extract_job_data(text: str) -> dict:
    """Use OpenAI ChatGPT to parse a job posting text into structured fields.

    Returns a dict containing whatever keys could be found; typical fields include
    ``title``, ``company``, ``location``, ``description`` and ``requirements``.

    If the OpenAI client is not installed or the API key is missing, a simple
    heuristic extraction is performed and an empty result is returned.
    """
    if not openai:
        logger.warning('openai package not installed, skipping AI extraction')
        return {}

    api_key = os.getenv('OPENAI_API_KEY')
    if not api_key:
        logger.warning('OPENAI_API_KEY not set, skipping AI extraction')
        return {}

    openai.api_key = api_key

    # craft a prompt asking for JSON output
    # prompt should request the exact field names the frontend expects so that
    # the returned JSON can be used directly in AIPaste.preview.
    prompt = (
        "You are given the full text of a job posting. "
        "Extract key information and return a JSON object using these keys when possible: "
        "company_name, job_title, location, location_type, employment_type, experience_level, "
        "salary_min, salary_max, salary_currency, contact_email, deadline, skills. "
        "If some fields are not present, simply omit them or set them to null. "
        "Only output the JSON object (no surrounding explanation). "
        f"Here is the text:\n```{text}```"
    )

    try:
        resp = openai.ChatCompletion.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            temperature=0,
            max_tokens=500,
        )
        content = resp.choices[0].message.content
        # attempt to parse JSON
        import json

        try:
            data = json.loads(content)
            return data
        except Exception as exc:
            logger.error('failed to parse JSON from OpenAI response: %s', exc)
            return {'raw': content}
    except Exception as exc:
        logger.error('OpenAI API call failed: %s', exc)
        return {}
