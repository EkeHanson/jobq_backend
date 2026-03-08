"""
File upload utilities for applications with compression support.
"""
import logging
import time
import uuid
import os
from apps.profiles.storage import get_storage_service

logger = logging.getLogger(__name__)


def upload_resume(file_obj, file_name, content_type="application/pdf", storage_type=None, compress=True):
    """
    Upload resume file to storage with optional compression.
    
    Args:
        file_obj: File object to upload
        file_name: Name of the resume file
        content_type: MIME type of the file
        storage_type: 'supabase', 's3', 'azure', or 'local'. If None, uses settings default
        compress: If True, upload as compressed (zip) archive
    
    Returns:
        Public URL of the uploaded file
    """
    storage_service = get_storage_service(storage_type)
    max_retries = 3
    
    for attempt in range(max_retries):
        try:
            # Reset file pointer before each attempt
            if hasattr(file_obj, 'seek'):
                file_obj.seek(0)
            
            if compress:
                # Upload as compressed file
                url = storage_service.upload_compressed(file_obj, file_name, content_type)
                logger.info(f"Successfully uploaded compressed resume: {file_name}")
                return url
            else:
                # Regular upload without compression
                # Generate unique filename
                ext = os.path.splitext(file_name)[1]
                unique_name = f"resume_{uuid.uuid4()}_{file_name}"
                
                success = storage_service.upload_file(file_obj, unique_name, content_type)
                if success:
                    return storage_service.get_public_url(unique_name)
                else:
                    raise Exception(f"Failed to upload resume {file_name}")
                    
        except Exception as e:
            error_msg = str(e)
            
            # Retry on transient errors
            if "SSL" in error_msg or "EOF" in error_msg or "ConnectError" in error_msg or "Connection" in error_msg:
                if attempt < max_retries - 1:
                    logger.warning(
                        f"Transient error uploading resume {file_name} "
                        f"(attempt {attempt + 1}/{max_retries}): {error_msg}. Retrying..."
                    )
                    time.sleep(1 * (attempt + 1))  # Exponential backoff
                    continue
            
            logger.error(f"Error uploading resume {file_name}: {error_msg}")
            raise


def delete_resume(file_url, storage_type=None):
    """
    Delete a resume file from storage.
    
    Args:
        file_url: URL of the file to delete
        storage_type: Storage backend to use
    
    Returns:
        True if successful, False otherwise
    """
    # Extract filename from URL
    if not file_url:
        return True
    
    # Get just the filename from the URL
    filename = file_url.split('/')[-1]
    if '.zip' in filename:
        filename = filename.replace('.zip', '')
    
    storage_service = get_storage_service(storage_type)
    return storage_service.delete_file(filename)
