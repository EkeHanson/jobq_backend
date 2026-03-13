import os
import logging
import email
from email import policy
from email.parser import BytesParser
from datetime import datetime
import re

logger = logging.getLogger(__name__)


class EmailImportService:
    """
    Service to scan emails and auto-create job applications.
    
    Note: This is a stub implementation. For production, you would need:
    - Gmail API integration with OAuth2
    - Or IMAP access to the user's email account
    
    This service demonstrates the core logic for parsing job-related emails.
    """
    
    # Email patterns to detect job-related messages
    APPLICATION_RECEIVED_PATTERNS = [
        r'we\s+received\s+your\s+application',
        r'application\s+received',
        r'thank\s+you\s+for\s+applying',
        r'we\s+have\s+received\s+your\s+resume',
        r'confirming\s+receipt',
    ]
    
    INTERVIEW_INVITATION_PATTERNS = [
        r'would\s+you\s+like\s+to\s+schedule',
        r'invite\s+you\s+to\s+an?\s+interview',
        r'we\s+would\s+like\s+to\s+meet',
        r'next\s+steps?\s+.*interview',
        r'follow\s+up\s+.*interview',
        r'phone\s+screen',
        r'video\s+interview',
    ]
    
    OFFER_PATTERNS = [
        r'offer\s+of\s+employment',
        r'pleased\s+to\s+offer',
        r'congratulations.*offer',
        r'we\s+would\s+like\s+to\s+offer',
    ]
    
    REJECTION_PATTERNS = [
        r'unfortunately.*not\s+move\s+forward',
        r'after\s+careful\s+consideration',
        r'unable\s+to\s+proceed',
        r'other\s+candidates',
    ]
    
    @staticmethod
    def parse_job_email(raw_email_content, email_subject=''):
        """
        Parse an email and extract job-related information.
        
        Args:
            raw_email_content: The raw email content
            email_subject: The email subject line
        
        Returns:
            dict with extracted information
        """
        result = {
            'type': None,  # application_received, interview_invitation, offer, rejection
            'company_name': None,
            'job_title': None,
            'next_action': None,
            'raw_content': raw_email_content[:500],  # Store snippet for reference
        }
        
        content_lower = (email_subject + ' ' + raw_email_content).lower()
        
        # Check for interview invitation
        if any(re.search(pattern, content_lower) for pattern in EmailImportService.INTERVIEW_INVITATION_PATTERNS):
            result['type'] = 'interview_invitation'
            result['next_action'] = 'Schedule interview'
        
        # Check for offer
        elif any(re.search(pattern, content_lower) for pattern in EmailImportService.OFFER_PATTERNS):
            result['type'] = 'offer'
            result['next_action'] = 'Review and respond to offer'
        
        # Check for rejection
        elif any(re.search(pattern, content_lower) for pattern in EmailImportService.REJECTION_PATTERNS):
            result['type'] = 'rejection'
            result['next_action'] = None
        
        # Check for application received
        elif any(re.search(pattern, content_lower) for pattern in EmailImportService.APPLICATION_RECEIVED_PATTERNS):
            result['type'] = 'application_received'
            result['next_action'] = 'Follow up in 1-2 weeks'
        
        # Try to extract company name
        result['company_name'] = EmailImportService._extract_company_name(raw_email_content, email_subject)
        
        # Try to extract job title
        result['job_title'] = EmailImportService._extract_job_title(raw_email_content, email_subject)
        
        return result
    
    @staticmethod
    def _extract_company_name(content, subject):
        """Extract company name from email content"""
        # Common patterns for company identification
        patterns = [
            r'from:\s*([^\n]+)',  # "From: Company Name"
            r'at\s+([^,\n]+)',     # "at Company Name"
            r'company:\s*([^\n]+)', # "Company: Name"
        ]
        
        for pattern in patterns:
            match = re.search(pattern, content, re.IGNORECASE)
            if match:
                return match.group(1).strip()
        
        return None
    
    @staticmethod
    def _extract_job_title(content, subject):
        """Extract job title from email content"""
        # Look for job title in subject line
        title_patterns = [
            r'job:\s*([^\n]+)',
            r'position:\s*([^\n]+)',
            r'role:\s*([^\n]+)',
        ]
        
        for pattern in title_patterns:
            match = re.search(pattern, content, re.IGNORECASE)
            if match:
                return match.group(1).strip()
        
        # Look in subject
        if subject:
            # Try to extract from subject patterns like "Job Title at Company"
            match = re.match(r'^(.+?)\s+at\s+', subject)
            if match:
                return match.group(1).strip()
        
        return None
    
    @staticmethod
    def create_application_from_email(user, email_data):
        """
        Create an application from parsed email data.
        
        Args:
            user: The User instance
            email_data: Dict with parsed email data
        
        Returns:
            Application instance or None
        """
        from apps.applications.models import Application
        
        if not email_data.get('company_name') and not email_data.get('job_title'):
            logger.warning('No company or job title found in email')
            return None
        
        # Determine status based on email type
        email_type = email_data.get('type')
        status_map = {
            'application_received': 'applied',
            'interview_invitation': 'interview',
            'offer': 'offer',
            'rejection': 'rejected',
        }
        
        status = status_map.get(email_type, 'applied')
        
        # Build notes string
        raw_content = email_data.get('raw_content', '') or ''
        next_action = email_data.get('next_action', 'N/A') or 'N/A'
        notes = f"Email Import: {raw_content}\n\nNext Action: {next_action}"
        
        # Create the application
        application = Application.objects.create(
            user=user,
            job_title=email_data.get('job_title', 'Unknown Position'),
            company_name=email_data.get('company_name', 'Unknown Company'),
            status=status,
            notes=notes,
            source='email_import'
        )
        
        return application
    
    @staticmethod
    def scan_gmail_emails(service, user_id='me', max_results=50):
        """
        Scan Gmail for job-related emails.
        
        This is a placeholder - requires Google API credentials and OAuth2 setup.
        
        Args:
            service: Gmail API service instance
            user_id: Gmail user ID (typically 'me')
            max_results: Maximum number of emails to scan
        
        Returns:
            List of parsed job email data
        """
        # This would require:
        # 1. Google Cloud Console project with Gmail API enabled
        # 2. OAuth2 credentials with gmail.readonly scope
        # 3. User consent flow
        
        # Search queries for job-related emails
        search_queries = [
            'subject:(application OR interview OR offer OR rejection) from:@',
            'subject:(thank you for applying OR your application)',
            'subject:(interview OR phone screen OR video call)',
        ]
        
        job_emails = []
        
        # This is a stub - actual implementation would call Gmail API
        logger.info('Gmail scanning not implemented - requires OAuth2 setup')
        
        return job_emails


class EmailParserHelper:
    """Helper class for parsing different email formats"""
    
    @staticmethod
    def parse_gmail_message(message):
        """Parse a Gmail API message object"""
        msg_id = message['id']
        subject = ''
        sender = ''
        body = ''
        
        # Get headers
        if 'payload' in message:
            headers = message['payload'].get('headers', [])
            for header in headers:
                if header['name'].lower() == 'subject':
                    subject = header['value']
                if header['name'].lower() == 'from':
                    sender = header['value']
            
            # Get body
            if 'parts' in message['payload']:
                for part in message['payload']['parts']:
                    if part.get('mimeType') == 'text/plain':
                        body = part.get('body', {}).get('data', '')
                        if body:
                            import base64
                            body = base64.urlsafe_b64decode(body).decode('utf-8')
        
        return {
            'id': msg_id,
            'subject': subject,
            'sender': sender,
            'body': body
        }
