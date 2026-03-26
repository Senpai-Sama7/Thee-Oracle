#!/usr/bin/env python3
"""
Oracle Agent GCS Storage Integration
Handles Google Cloud Storage operations for file persistence and media management
"""

import os
import time
import mimetypes
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

try:
    from google.cloud import storage as gcs_storage  # type: ignore
    from google.api_core import exceptions as gcs_exceptions

    GCS_AVAILABLE = True
except ImportError:
    GCS_AVAILABLE = False
    gcs_storage = None
    gcs_exceptions = None  # type: ignore


class GCSStorageManager:
    """
    Google Cloud Storage integration for Oracle Agent
    Handles file uploads, downloads, and bucket management
    """

    def __init__(self, bucket_name: str, project_id: str, project_root: Optional[Union[str, Path]] = None) -> None:
        self.bucket_name = bucket_name
        self.project_id = project_id
        self.project_root = Path(project_root).resolve() if project_root else None
        self.client: Optional[Any] = None
        self.bucket: Optional[Any] = None
        self._initialize_client()

    def _initialize_client(self) -> None:
        """Initialize GCS client and bucket reference"""
        if not GCS_AVAILABLE or gcs_storage is None:
            return

        try:
            self.client = gcs_storage.Client(project=self.project_id)
            if not self.client:
                return
            self.bucket = self.client.bucket(self.bucket_name)

            # Test bucket access
            if self.bucket:
                self.bucket.reload()
                print(f"✅ GCS Storage initialized: {self.bucket_name}")

        except Exception as e:
            if gcs_exceptions and isinstance(e, gcs_exceptions.NotFound):
                print(f"⚠️  Bucket {self.bucket_name} not found.")
            else:
                print(f"⚠️  GCS initialization failed: {e}")
            try:
                self._create_bucket()
            except Exception as create_error:
                print(f"❌ Failed to initialize GCS Storage: {create_error}")
                raise

    def _create_bucket(self) -> None:
        """Create GCS bucket if it doesn't exist"""
        if not GCS_AVAILABLE:
            print("❌ GCS Storage is not available, cannot create bucket.")
            return
        try:
            if not self.client:
                raise RuntimeError("GCS Client not initialized")

            # Create bucket with appropriate location
            bucket = self.client.create_bucket(self.bucket_name, location=os.environ.get("GCP_LOCATION", "us-central1"))
            self.bucket = bucket
            print(f"✅ Created GCS bucket: {self.bucket_name}")

            # Set lifecycle rules for automatic cleanup
            self._configure_bucket_lifecycle()

        except Exception as e:
            print(f"❌ Failed to create bucket: {e}")
            raise

    def _configure_bucket_lifecycle(self) -> None:
        """Configure bucket lifecycle rules for cost optimization"""
        if not self.bucket:
            return
        lifecycle_rules = [
            {
                "action": {"type": "Delete"},
                "condition": {"age": 30},  # Delete objects after 30 days
            },
            {
                "action": {"type": "SetStorageClass", "storage_class": "COLDLINE"},
                "condition": {"age": 7},  # Move to Coldline after 7 days
            },
        ]

        lifecycle = self.bucket.lifecycle()
        lifecycle.rules = lifecycle_rules
        lifecycle.patch()
        print("✅ Configured bucket lifecycle rules")

    def upload_file(
        self, local_path: str, gcs_path: Optional[str] = None, metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Upload file to GCS bucket

        Args:
            local_path: Local file path
            gcs_path: GCS object path (defaults to filename)
            metadata: Optional metadata to attach

        Returns:
            Upload result with GCS URI and metadata
        """
        try:
            local_file = Path(local_path)
            if not local_file.exists():
                return {"success": False, "error": "Local file not found"}

            # Default GCS path to filename if not provided
            if not gcs_path:
                gcs_path = local_file.name

            # Determine content type
            content_type, _ = mimetypes.guess_type(str(local_file))
            if not content_type:
                content_type = "application/octet-stream"

            if not self.bucket:
                return {"success": False, "error": "GCS bucket not initialized"}
            blob = self.bucket.blob(gcs_path)
            blob.content_type = content_type

            # Add metadata
            if metadata:
                blob.metadata = metadata

            # Add standard metadata
            blob.metadata = blob.metadata or {}
            blob.metadata.update(
                {
                    "uploaded_by": "oracle-agent",
                    "upload_time": time.strftime("%Y-%m-%d %H:%M:%S"),
                    "original_filename": local_file.name,
                    "file_size": local_file.stat().st_size,
                }
            )

            # Perform upload
            blob.upload_from_filename(str(local_file))

            result = {
                "success": True,
                "gcs_uri": f"gs://{self.bucket_name}/{gcs_path}",
                "public_url": blob.public_url,
                "size": local_file.stat().st_size,
                "content_type": content_type,
                "metadata": blob.metadata,
            }

            print(f"✅ Uploaded {local_file.name} to GCS")
            return result

        except Exception as e:
            return {"success": False, "error": str(e)}

    def download_file(self, gcs_path: str, local_path: Optional[str] = None) -> Dict[str, Any]:
        """
        Download file from GCS bucket

        Args:
            gcs_path: GCS object path
            local_path: Local destination path (defaults to current directory)

        Returns:
            Download result with file information
        """
        try:
            if not self.bucket:
                return {"success": False, "error": "GCS bucket not initialized"}
            blob = self.bucket.blob(gcs_path)

            if not blob.exists():
                return {"success": False, "error": "GCS object not found"}

            # Default local path
            if not local_path:
                local_path_obj = Path.cwd() / Path(gcs_path).name
            else:
                local_path_obj = Path(local_path)

            local_path_obj = local_path_obj.resolve()

            # Enforce path containment if project_root is set
            if self.project_root and not local_path_obj.is_relative_to(self.project_root):
                return {"success": False, "error": f"Path traversal denied: {local_path_obj} is outside project root"}

            # Create directory if needed
            local_path_obj.parent.mkdir(parents=True, exist_ok=True)

            # Download file
            blob.download_to_filename(str(local_path_obj))

            result = {
                "success": True,
                "local_path": str(local_path_obj),
                "size": local_path_obj.stat().st_size,
                "content_type": blob.content_type,
                "metadata": blob.metadata,
            }

            return result

        except Exception as e:
            return {"success": False, "error": str(e)}

    def list_files(self, prefix: str = "", max_results: int = 100) -> List[Dict[str, Any]]:
        """
        List files in GCS bucket

        Args:
            prefix: Prefix filter (e.g., "screenshots/")
            max_results: Maximum number of results

        Returns:
            List of file information
        """
        try:
            if not self.client:
                return []
            blobs = self.client.list_blobs(self.bucket_name, prefix=prefix, max_results=max_results)

            files = []
            for blob in blobs:
                files.append(
                    {
                        "name": blob.name,
                        "size": blob.size,
                        "content_type": blob.content_type,
                        "updated": blob.updated.isoformat() if blob.updated else None,
                        "public_url": blob.public_url,
                        "metadata": blob.metadata,
                    }
                )

            return files

        except Exception as e:
            print(f"❌ Failed to list files: {e}")
            return []

    def delete_file(self, gcs_path: str) -> Dict[str, Any]:
        """Delete file from GCS bucket"""
        try:
            if not self.bucket:
                return {"success": False, "error": "GCS bucket not initialized"}
            blob = self.bucket.blob(gcs_path)

            if not blob.exists():
                return {"success": False, "error": "GCS object not found"}

            blob.delete()

            return {"success": True, "message": f"Deleted {gcs_path} from GCS"}

        except Exception as e:
            return {"success": False, "error": str(e)}

    def get_file_info(self, gcs_path: str) -> Dict[str, Any]:
        """Get file information from GCS"""
        try:
            if not self.bucket:
                return {"success": False, "error": "GCS bucket not initialized"}
            blob = self.bucket.blob(gcs_path)

            if not blob.exists():
                return {"success": False, "error": "GCS object not found"}

            blob.reload()

            return {
                "success": True,
                "name": blob.name,
                "size": blob.size,
                "content_type": blob.content_type,
                "updated": blob.updated.isoformat() if blob.updated else None,
                "public_url": blob.public_url,
                "metadata": blob.metadata,
                "gcs_uri": f"gs://{self.bucket_name}/{gcs_path}",
            }

        except Exception as e:
            return {"success": False, "error": str(e)}

    def upload_screenshot(self, screenshot_path: str, session_id: str = "default") -> Dict[str, Any]:
        """
        Specialized method for uploading screenshots with organized naming

        Args:
            screenshot_path: Path to screenshot file
            session_id: Session identifier for organization

        Returns:
            Upload result with organized GCS path
        """
        try:
            screenshot_file = Path(screenshot_path)
            timestamp = time.strftime("%Y%m%d_%H%M%S")

            # Organized path: screenshots/session_id/timestamp_filename.png
            gcs_path = f"screenshots/{session_id}/{timestamp}_{screenshot_file.name}"

            metadata = {
                "type": "screenshot",
                "session_id": session_id,
                "capture_time": timestamp,
                "tool": "vision_capture",
            }

            return self.upload_file(screenshot_path, gcs_path, metadata)

        except Exception as e:
            return {"success": False, "error": str(e)}

    def backup_database(self, db_path: str) -> Dict[str, Any]:
        """
        Backup database file to GCS

        Args:
            db_path: Path to database file

        Returns:
            Backup result with timestamped GCS path
        """
        try:
            db_file = Path(db_path)
            if not db_file.exists():
                return {"success": False, "error": "Database file not found"}

            timestamp = time.strftime("%Y%m%d_%H%M%S")
            gcs_path = f"backups/database/oracle_core_{timestamp}.db"

            metadata = {
                "type": "database_backup",
                "backup_time": timestamp,
                "original_size": db_file.stat().st_size,
                "version": "oracle_agent_v1",
            }

            return self.upload_file(db_path, gcs_path, metadata)

        except Exception as e:
            return {"success": False, "error": str(e)}

    def get_bucket_stats(self) -> Dict[str, Any]:
        """Get bucket statistics and usage information"""
        try:
            # Get bucket info
            if not self.bucket or not self.client:
                return {"success": False, "error": "GCS bucket not initialized"}
            self.bucket.reload()

            # Count objects and calculate total size
            total_size = 0
            object_count = 0

            for blob in self.client.list_blobs(self.bucket_name):
                total_size += blob.size
                object_count += 1

            return {
                "success": True,
                "bucket_name": self.bucket_name,
                "location": self.bucket.location,
                "storage_class": self.bucket.storage_class,
                "object_count": object_count,
                "total_size_bytes": total_size,
                "total_size_mb": round(total_size / (1024 * 1024), 2),
                "time_created": self.bucket.time_created.isoformat() if self.bucket.time_created else None,
            }

        except Exception as e:
            return {"success": False, "error": str(e)}
