"""
File upload utilities with compression support.
"""
import logging
import time
import uuid
import os
from .storage import get_storage_service

logger = logging.getLogger(__name__)


def upload_file_dynamic(file_obj, file_name, content_type="application/octet-stream", storage_type=None, compress=True):
    """
    Upload files to the selected storage backend, optionally as compressed file.
    
    Args:
        file_obj: File object to upload
        file_name: Name of the file (used for the compressed archive name)
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
                logger.info(f"Successfully uploaded compressed file: {file_name}")
                return url
            else:
                # Regular upload without compression
                # Generate unique filename
                ext = os.path.splitext(file_name)[1]
                unique_name = f"{uuid.uuid4()}_{file_name}"
                
                success = storage_service.upload_file(file_obj, unique_name, content_type)
                if success:
                    return storage_service.get_public_url(unique_name)
                else:
                    raise Exception(f"Failed to upload {file_name}")
                    
        except Exception as e:
            error_msg = str(e)
            
            # Retry on transient errors
            if "SSL" in error_msg or "EOF" in error_msg or "ConnectError" in error_msg or "Connection" in error_msg:
                if attempt < max_retries - 1:
                    logger.warning(
                        f"Transient error uploading {file_name} "
                        f"(attempt {attempt + 1}/{max_retries}): {error_msg}. Retrying..."
                    )
                    time.sleep(1 * (attempt + 1))  # Exponential backoff
                    continue
            
            logger.error(f"Error uploading file {file_name}: {error_msg}")
            raise


def upload_multiple_files(file_list, content_type="application/octet-stream", storage_type=None, compress=True):
    """
    Upload multiple files as a single compressed archive.
    
    Args:
        file_list: List of tuples (file_obj, filename)
        content_type: MIME type for the files
        storage_type: Storage backend to use
        compress: If True, create zip archive
    
    Returns:
        Public URL of the uploaded archive
    """
    import zipfile
    import io
    
    storage_service = get_storage_service(storage_type)
    
    # Create zip in memory
    zip_buffer = io.BytesIO()
    
    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
        for file_obj, filename in file_list:
            # Reset file pointer
            if hasattr(file_obj, 'seek'):
                file_obj.seek(0)
            
            # Read file content
            if hasattr(file_obj, 'read'):
                file_data = file_obj.read()
            else:
                file_data = file_obj
            
            zip_file.writestr(filename, file_data)
    
    zip_buffer.seek(0)
    
    # Generate unique zip filename
    zip_filename = f"upload_{uuid.uuid4()}.zip"
    
    # Upload the zip
    try:
        if hasattr(storage_service, 'upload_compressed'):
            # Use existing compressed upload method with dummy original_filename
            return storage_service.upload_compressed(zip_buffer, "archive", "application/zip")
        else:
            # Fallback: upload as regular file
            success = storage_service.upload_file(zip_buffer, zip_filename, "application/zip")
            if success:
                return storage_service.get_public_url(zip_filename)
            raise Exception("Failed to upload archive")
    except Exception as e:
        logger.error(f"Error uploading multiple files: {str(e)}")
        raise


def delete_file(file_name, storage_type=None):
    """
    Delete a file from storage.
    
    Args:
        file_name: Name/path of the file to delete
        storage_type: Storage backend to use
    
    Returns:
        True if successful, False otherwise
    """
    storage_service = get_storage_service(storage_type)
    return storage_service.delete_file(file_name)
