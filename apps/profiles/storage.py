import os
import uuid
import logging
import zipfile
import io
from django.conf import settings
from supabase import create_client
import boto3
from azure.storage.blob import BlobServiceClient
from django.core.files.uploadedfile import InMemoryUploadedFile, TemporaryUploadedFile
import re

logger = logging.getLogger(__name__)


class StorageService:
    """Base storage service interface"""
    
    def upload_file(self, file_obj, file_name, content_type):
        raise NotImplementedError("Subclasses must implement upload_file")

    def get_public_url(self, file_name):
        raise NotImplementedError("Subclasses must implement get_public_url")

    def delete_file(self, file_name):
        raise NotImplementedError("Subclasses must implement delete_file")
    
    def upload_compressed(self, file_obj, original_filename, content_type=None):
        """Upload file as compressed (zip) archive"""
        raise NotImplementedError("Subclasses must implement upload_compressed")


class LocalStorageService(StorageService):
    """Local file system storage"""
    
    def __init__(self):
        self.media_root = getattr(settings, "MEDIA_ROOT", "media")
    
    def upload_file(self, file_obj, file_name, content_type=None):
        file_path = os.path.join(self.media_root, file_name)
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        
        if isinstance(file_obj, (InMemoryUploadedFile, TemporaryUploadedFile)):
            file_data = file_obj.read()
        else:
            file_data = file_obj.read() if hasattr(file_obj, 'read') else file_obj
            
        with open(file_path, "wb") as f:
            f.write(file_data)
        return True

    def get_public_url(self, file_name):
        return f"/media/{file_name}"

    def delete_file(self, file_name):
        file_path = os.path.join(self.media_root, file_name)
        try:
            os.remove(file_path)
            return True
        except FileNotFoundError:
            return False
    
    def upload_compressed(self, file_obj, original_filename, content_type=None):
        """Compress file and save locally"""
        # Generate unique filename with .zip extension
        file_name = f"{uuid.uuid4()}_{original_filename}.zip"
        file_path = os.path.join(self.media_root, file_name)
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        
        # Read file content
        if isinstance(file_obj, (InMemoryUploadedFile, TemporaryUploadedFile)):
            file_data = file_obj.read()
        else:
            file_data = file_obj.read() if hasattr(file_obj, 'read') else file_obj
        
        # Create zip file in memory
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            zip_file.writestr(original_filename, file_data)
        
        # Write zip to disk
        zip_buffer.seek(0)
        with open(file_path, 'wb') as f:
            f.write(zip_buffer.read())
        
        logger.info(f"Compressed file saved locally: {file_name}")
        return True
    
    def get_compressed_url(self, file_name):
        """Get public URL for compressed file"""
        return f"/media/{file_name}"


class SupabaseStorageService(StorageService):
    """Supabase storage service"""
    
    def __init__(self):
        self.client = create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)
        self.bucket = settings.SUPABASE_BUCKET
        if not self.bucket:
            raise ValueError("SUPABASE_BUCKET is not configured properly")
        
        # Get the storage object properly for supabase v1.x
        # The storage might be accessed as a method or property depending on version
        try:
            self.storage = self.client.storage
            if callable(self.storage):
                self.storage = self.storage()
        except Exception as e:
            logger.error(f"Error initializing Supabase storage: {e}")
            raise
    
    def _get_bucket(self):
        """Get the bucket object"""
        try:
            # Try v1.x API first
            return self.storage.from_(self.bucket)
        except AttributeError:
            # Fall back to v2.x API
            return self.storage.bucket(self.bucket)

    def sanitize_filename(self, filename):
        """Sanitize filename for Supabase/S3"""
        if not filename:
            return f"file_{uuid.uuid4()}.dat"
        
        sanitized = re.sub(r'[^\w\.-]', '_', filename)
        sanitized = re.sub(r'_{2,}', '_', sanitized)
        sanitized = re.sub(r'^\_+|_+$', '', sanitized)
        
        name, ext = os.path.splitext(sanitized)
        unique_name = f"{uuid.uuid4()}_{name}{ext}"
        
        return unique_name

    def upload_file(self, file_obj, file_name, content_type):
        try:
            if isinstance(file_obj, (InMemoryUploadedFile, TemporaryUploadedFile)):
                file_data = file_obj.read()
            else:
                file_data = file_obj.read() if hasattr(file_obj, 'read') else file_obj

            bucket = self._get_bucket()
            res = bucket.upload(
                path=file_name,
                file=file_data,
                file_options={"content-type": content_type, "cache-control": "3600", "upsert": "true"}
            )

            if hasattr(res, 'path') and res.path:
                logger.info(f"Successfully uploaded {file_name} to Supabase")
                return True
            else:
                error_msg = getattr(res, 'error', str(res))
                logger.error(f"Failed to upload {file_name} to Supabase: {error_msg}")
                return False
        except Exception as e:
            logger.error(f"Error uploading to Supabase: {str(e)}", exc_info=True)
            raise

    def get_public_url(self, file_name):
        try:
            bucket = self._get_bucket()
            return bucket.get_public_url(file_name)
        except Exception as e:
            logger.error(f"Error generating public URL in Supabase: {str(e)}")
            raise

    def delete_file(self, file_name):
        try:
            bucket = self._get_bucket()
            bucket.remove([file_name])
            logger.info(f"Successfully deleted {file_name} from Supabase")
            return True
        except Exception as e:
            logger.error(f"Error deleting {file_name} from Supabase: {str(e)}")
            return False
    
    def upload_compressed(self, file_obj, original_filename, content_type=None):
        """Compress file and upload to Supabase"""
        # Generate unique zip filename
        zip_filename = f"{uuid.uuid4()}_{original_filename}.zip"
        
        # Read file content
        if isinstance(file_obj, (InMemoryUploadedFile, TemporaryUploadedFile)):
            file_data = file_obj.read()
        else:
            file_data = file_obj.read() if hasattr(file_obj, 'read') else file_obj
        
        # Create zip in memory
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            zip_file.writestr(original_filename, file_data)
        
        zip_buffer.seek(0)
        zip_data = zip_buffer.read()
        
        # Upload to Supabase
        try:
            bucket = self._get_bucket()
            res = bucket.upload(
                path=zip_filename,
                file=zip_data,
                file_options={
                    "content-type": "application/zip",
                    "cache-control": "3600",
                    "upsert": "true"
                }
            )
            
            if hasattr(res, 'path') and res.path:
                logger.info(f"Compressed file uploaded to Supabase: {zip_filename}")
                return self.get_public_url(zip_filename)
            else:
                error_msg = getattr(res, 'error', str(res))
                logger.error(f"Failed to upload compressed file: {error_msg}")
                raise Exception(f"Upload failed: {error_msg}")
        except Exception as e:
            logger.error(f"Error uploading compressed file to Supabase: {str(e)}")
            raise


class S3StorageService(StorageService):
    """AWS S3 storage service"""
    
    def __init__(self):
        self.client = boto3.client(
            's3',
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
            region_name=settings.AWS_REGION
        )
        self.bucket = settings.AWS_S3_BUCKET

    def upload_file(self, file_obj, file_name, content_type):
        try:
            extra_args = {'ContentType': content_type or 'application/octet-stream'}
            acl_value = getattr(settings, 'AWS_S3_OBJECT_ACL', None)
            if acl_value:
                extra_args['ACL'] = acl_value

            self.client.upload_fileobj(
                file_obj,
                self.bucket,
                file_name,
                ExtraArgs=extra_args
            )
            logger.info(f"Successfully uploaded {file_name} to S3")
            return True
        except Exception as e:
            logger.error(f"Error uploading to S3: {str(e)}", exc_info=True)
            raise

    def get_public_url(self, file_name):
        try:
            return f"https://{self.bucket}.s3.{settings.AWS_REGION}.amazonaws.com/{file_name}"
        except Exception as e:
            logger.error(f"Error generating public URL in S3: {str(e)}")
            raise

    def delete_file(self, file_name):
        try:
            self.client.delete_object(Bucket=self.bucket, Key=file_name)
            logger.info(f"Successfully deleted {file_name} from S3")
            return True
        except Exception as e:
            logger.error(f"Error deleting {file_name} from S3: {str(e)}")
            return False
    
    def upload_compressed(self, file_obj, original_filename, content_type=None):
        """Compress file and upload to S3"""
        zip_filename = f"{uuid.uuid4()}_{original_filename}.zip"
        
        # Read file content
        if isinstance(file_obj, (InMemoryUploadedFile, TemporaryUploadedFile)):
            file_data = file_obj.read()
        else:
            file_data = file_obj.read() if hasattr(file_obj, 'read') else file_obj
        
        # Create zip in memory
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            zip_file.writestr(original_filename, file_data)
        
        zip_buffer.seek(0)
        
        # Upload to S3
        try:
            self.client.upload_fileobj(
                zip_buffer,
                self.bucket,
                zip_filename,
                ExtraArgs={
                    'ContentType': 'application/zip',
                    'ACL': getattr(settings, 'AWS_S3_OBJECT_ACL', 'public-read')
                }
            )
            logger.info(f"Compressed file uploaded to S3: {zip_filename}")
            return self.get_public_url(zip_filename)
        except Exception as e:
            logger.error(f"Error uploading compressed file to S3: {str(e)}")
            raise


class AzureStorageService(StorageService):
    """Azure Blob storage service"""
    
    def __init__(self):
        self.client = BlobServiceClient.from_connection_string(settings.AZURE_CONNECTION_STRING)
        self.container = settings.AZURE_CONTAINER

    def upload_file(self, file_obj, file_name, content_type):
        try:
            container_client = self.client.get_container_client(self.container)
            blob_client = container_client.get_blob_client(file_name)
            
            # Read file data
            if isinstance(file_obj, (InMemoryUploadedFile, TemporaryUploadedFile)):
                file_data = file_obj.read()
            else:
                file_data = file_obj.read() if hasattr(file_obj, 'read') else file_obj
            
            blob_client.upload_blob(
                file_data,
                blob_type="BlockBlob",
                content_settings={'content_type': content_type or 'application/octet-stream'}
            )
            logger.info(f"Successfully uploaded {file_name} to Azure")
            return True
        except Exception as e:
            logger.error(f"Error uploading to Azure: {str(e)}")
            raise

    def get_public_url(self, file_name):
        try:
            return f"https://{settings.AZURE_ACCOUNT_NAME}.blob.core.windows.net/{self.container}/{file_name}"
        except Exception as e:
            logger.error(f"Error generating public URL in Azure: {str(e)}")
            raise

    def delete_file(self, file_name):
        try:
            container_client = self.client.get_container_client(self.container)
            blob_client = container_client.get_blob_client(file_name)
            blob_client.delete_blob()
            logger.info(f"Successfully deleted {file_name} from Azure")
            return True
        except Exception as e:
            logger.error(f"Error deleting {file_name} from Azure: {str(e)}")
            return False
    
    def upload_compressed(self, file_obj, original_filename, content_type=None):
        """Compress file and upload to Azure"""
        zip_filename = f"{uuid.uuid4()}_{original_filename}.zip"
        
        # Read file content
        if isinstance(file_obj, (InMemoryUploadedFile, TemporaryUploadedFile)):
            file_data = file_obj.read()
        else:
            file_data = file_obj.read() if hasattr(file_obj, 'read') else file_obj
        
        # Create zip in memory
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            zip_file.writestr(original_filename, file_data)
        
        zip_buffer.seek(0)
        
        # Upload to Azure
        try:
            container_client = self.client.get_container_client(self.container)
            blob_client = container_client.get_blob_client(zip_filename)
            blob_client.upload_blob(
                zip_buffer.read(),
                blob_type="BlockBlob",
                content_settings={'content_type': 'application/zip'}
            )
            logger.info(f"Compressed file uploaded to Azure: {zip_filename}")
            return self.get_public_url(zip_filename)
        except Exception as e:
            logger.error(f"Error uploading compressed file to Azure: {str(e)}")
            raise


def get_storage_service(storage_type=None):
    """
    Factory function to get the appropriate storage service.
    
    Args:
        storage_type: One of 'supabase', 's3', 'azure', or 'local'
                     If None, uses STORAGE_TYPE from settings
    
    Returns:
        StorageService instance
    """
    storage_type = (storage_type or getattr(settings, 'STORAGE_TYPE', 'supabase')).lower()

    if storage_type == 'supabase':
        return SupabaseStorageService()
    elif storage_type == 's3':
        return S3StorageService()
    elif storage_type == 'azure':
        return AzureStorageService()
    else:
        return LocalStorageService()
