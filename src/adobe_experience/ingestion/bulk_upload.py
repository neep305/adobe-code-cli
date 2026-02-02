"""Bulk file upload client for Adobe Experience Platform batch ingestion."""

import asyncio
import mimetypes
from pathlib import Path
from typing import Dict, List, Optional, Union

import httpx

from adobe_experience.aep.client import AEPClient


class BulkIngestClient:
    """Client for uploading files to Adobe Experience Platform batches.
    
    This client handles binary file uploads to batches created via the Catalog Service.
    It supports single file uploads, multiple file uploads, and tracks upload progress.
    
    Reference: https://experienceleague.adobe.com/en/docs/experience-platform/ingestion/batch/api
    """

    def __init__(self, client: AEPClient) -> None:
        """Initialize bulk ingest client.
        
        Args:
            client: Authenticated AEP API client
        """
        self.client = client

    async def upload_file(
        self,
        batch_id: str,
        dataset_id: str,
        file_path: Union[str, Path],
        file_name: Optional[str] = None,
    ) -> Dict[str, str]:
        """Upload a single file to a batch.
        
        Args:
            batch_id: Batch ID to upload to
            dataset_id: Dataset ID associated with the batch
            file_path: Path to file to upload
            file_name: Optional custom file name (defaults to original filename)
            
        Returns:
            Dict with upload metadata (file_name, size_bytes, status)
            
        Raises:
            FileNotFoundError: If file doesn't exist
            ValueError: If file is empty or too large
            httpx.HTTPStatusError: For API errors
            
        Example:
            >>> async with AEPClient(config) as aep_client:
            ...     bulk = BulkIngestClient(aep_client)
            ...     result = await bulk.upload_file(
            ...         batch_id="5d01230fc78a4e4f8c0c6b387b4b8d1c",
            ...         dataset_id="5c8c3c555033b814b69f947f",
            ...         file_path="data.parquet"
            ...     )
            ...     print(f"Uploaded {result['size_bytes']} bytes")
        """
        file_path = Path(file_path)
        
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")
        
        file_size = file_path.stat().st_size
        if file_size == 0:
            raise ValueError(f"File is empty: {file_path}")
        
        # Use custom name or original filename
        upload_name = file_name or file_path.name
        
        # Detect content type
        content_type = mimetypes.guess_type(file_path)[0] or "application/octet-stream"
        
        # Build upload URL
        path = f"/batches/{batch_id}/datasets/{dataset_id}/files/{upload_name}"
        
        # Read file content
        with open(file_path, "rb") as f:
            file_content = f.read()
        
        # Upload file
        headers = {
            "Content-Type": content_type,
        }
        
        try:
            await self.client.put(path, content=file_content, headers=headers)
            
            return {
                "file_name": upload_name,
                "size_bytes": file_size,
                "status": "uploaded",
                "content_type": content_type,
            }
            
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 413:
                raise ValueError(f"File too large: {file_size} bytes (max may be 512MB)") from e
            raise

    async def upload_multiple_files(
        self,
        batch_id: str,
        dataset_id: str,
        file_paths: List[Union[str, Path]],
        max_concurrent: int = 3,
    ) -> List[Dict[str, str]]:
        """Upload multiple files to a batch concurrently.
        
        Args:
            batch_id: Batch ID to upload to
            dataset_id: Dataset ID associated with the batch
            file_paths: List of file paths to upload
            max_concurrent: Maximum concurrent uploads (default: 3)
            
        Returns:
            List of upload results (one per file)
            
        Example:
            >>> files = ["data1.parquet", "data2.parquet", "data3.parquet"]
            >>> results = await bulk.upload_multiple_files(
            ...     batch_id=batch_id,
            ...     dataset_id=dataset_id,
            ...     file_paths=files
            ... )
            >>> total_bytes = sum(r['size_bytes'] for r in results)
        """
        semaphore = asyncio.Semaphore(max_concurrent)
        
        async def upload_with_semaphore(file_path: Union[str, Path]) -> Dict[str, str]:
            async with semaphore:
                return await self.upload_file(batch_id, dataset_id, file_path)
        
        tasks = [upload_with_semaphore(fp) for fp in file_paths]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Convert exceptions to error dicts
        processed_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                processed_results.append({
                    "file_name": str(file_paths[i]),
                    "size_bytes": 0,
                    "status": "failed",
                    "error": str(result),
                })
            else:
                processed_results.append(result)
        
        return processed_results

    async def upload_directory(
        self,
        batch_id: str,
        dataset_id: str,
        directory_path: Union[str, Path],
        pattern: str = "*",
        recursive: bool = False,
        max_concurrent: int = 3,
    ) -> List[Dict[str, str]]:
        """Upload all files from a directory to a batch.
        
        Args:
            batch_id: Batch ID to upload to
            dataset_id: Dataset ID associated with the batch
            directory_path: Path to directory containing files
            pattern: Glob pattern for file matching (default: "*" = all files)
            recursive: Search subdirectories recursively (default: False)
            max_concurrent: Maximum concurrent uploads
            
        Returns:
            List of upload results
            
        Example:
            >>> # Upload all parquet files
            >>> results = await bulk.upload_directory(
            ...     batch_id=batch_id,
            ...     dataset_id=dataset_id,
            ...     directory_path="./data",
            ...     pattern="*.parquet"
            ... )
        """
        dir_path = Path(directory_path)
        
        if not dir_path.is_dir():
            raise NotADirectoryError(f"Not a directory: {dir_path}")
        
        # Find matching files
        if recursive:
            file_paths = list(dir_path.rglob(pattern))
        else:
            file_paths = list(dir_path.glob(pattern))
        
        # Filter out directories
        file_paths = [fp for fp in file_paths if fp.is_file()]
        
        if not file_paths:
            raise ValueError(f"No files found matching pattern '{pattern}' in {dir_path}")
        
        return await self.upload_multiple_files(
            batch_id=batch_id,
            dataset_id=dataset_id,
            file_paths=file_paths,
            max_concurrent=max_concurrent,
        )

    async def get_upload_status(
        self,
        batch_id: str,
        file_name: str,
    ) -> Dict[str, str]:
        """Check if a file has been uploaded to a batch.
        
        Args:
            batch_id: Batch ID
            file_name: Name of file to check
            
        Returns:
            Dict with status information
            
        Example:
            >>> status = await bulk.get_upload_status(batch_id, "data.parquet")
            >>> if status['exists']:
            ...     print(f"File uploaded: {status['size_bytes']} bytes")
        """
        # Use Catalog Service to list files in batch
        from adobe_experience.catalog.client import CatalogServiceClient
        
        catalog = CatalogServiceClient(self.client)
        files = await catalog.list_dataset_files(batch_id=batch_id)
        
        # Find matching file
        for file in files:
            if file.file_name == file_name:
                return {
                    "exists": True,
                    "file_name": file.file_name,
                    "size_bytes": file.size_bytes,
                    "records": file.records or 0,
                    "is_valid": file.is_valid or False,
                }
        
        return {
            "exists": False,
            "file_name": file_name,
        }
