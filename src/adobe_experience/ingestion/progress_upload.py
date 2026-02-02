"""Enhanced bulk file upload with progress tracking and chunked uploads."""

import asyncio
from pathlib import Path
from typing import Callable, Dict, List, Optional, Union

import httpx
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, DownloadColumn, TransferSpeedColumn

from adobe_experience.aep.client import AEPClient


class ProgressTracker:
    """Progress tracker for file uploads with Rich display."""
    
    def __init__(self, show_progress: bool = True) -> None:
        """Initialize progress tracker.
        
        Args:
            show_progress: Whether to show progress UI
        """
        self.show_progress = show_progress
        self.progress: Optional[Progress] = None
        self.task_id: Optional[int] = None
    
    def __enter__(self) -> "ProgressTracker":
        if self.show_progress:
            self.progress = Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                BarColumn(),
                DownloadColumn(),
                TransferSpeedColumn(),
            )
            self.progress.__enter__()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.progress:
            self.progress.__exit__(exc_type, exc_val, exc_tb)
    
    def start_task(self, description: str, total: int) -> None:
        """Start a progress task.
        
        Args:
            description: Task description
            total: Total bytes to upload
        """
        if self.progress:
            self.task_id = self.progress.add_task(description, total=total)
    
    def update(self, advance: int) -> None:
        """Update progress.
        
        Args:
            advance: Bytes uploaded in this chunk
        """
        if self.progress and self.task_id is not None:
            self.progress.update(self.task_id, advance=advance)


class ChunkedUploader:
    """Handles chunked file uploads for large files."""
    
    CHUNK_SIZE = 10 * 1024 * 1024  # 10MB chunks
    
    def __init__(self, client: AEPClient) -> None:
        """Initialize chunked uploader.
        
        Args:
            client: Authenticated AEP API client
        """
        self.client = client
    
    async def upload_file_chunked(
        self,
        batch_id: str,
        dataset_id: str,
        file_path: Path,
        upload_name: str,
        content_type: str,
        progress_callback: Optional[Callable[[int], None]] = None,
    ) -> Dict[str, str]:
        """Upload a file in chunks.
        
        Args:
            batch_id: Batch ID
            dataset_id: Dataset ID
            file_path: Path to file
            upload_name: Name to use for upload
            content_type: MIME type
            progress_callback: Optional callback for progress updates
            
        Returns:
            Upload metadata
        """
        file_size = file_path.stat().st_size
        path = f"/batches/{batch_id}/datasets/{dataset_id}/files/{upload_name}"
        
        # For files smaller than chunk size, use single upload
        if file_size <= self.CHUNK_SIZE:
            with open(file_path, "rb") as f:
                file_content = f.read()
            
            headers = {"Content-Type": content_type}
            await self.client.put(path, content=file_content, headers=headers)
            
            if progress_callback:
                progress_callback(file_size)
            
            return {
                "file_name": upload_name,
                "size_bytes": file_size,
                "status": "uploaded",
                "chunks": 1,
            }
        
        # For large files, upload in chunks
        chunk_count = 0
        bytes_uploaded = 0
        
        with open(file_path, "rb") as f:
            while True:
                chunk = f.read(self.CHUNK_SIZE)
                if not chunk:
                    break
                
                chunk_count += 1
                chunk_size = len(chunk)
                
                # Upload chunk
                headers = {
                    "Content-Type": content_type,
                    "Content-Range": f"bytes {bytes_uploaded}-{bytes_uploaded + chunk_size - 1}/{file_size}",
                }
                
                await self.client.put(path, content=chunk, headers=headers)
                
                bytes_uploaded += chunk_size
                
                if progress_callback:
                    progress_callback(chunk_size)
        
        return {
            "file_name": upload_name,
            "size_bytes": file_size,
            "status": "uploaded",
            "chunks": chunk_count,
        }


class BulkIngestClientWithProgress:
    """Enhanced bulk ingest client with progress tracking and chunked uploads.
    
    This extends the basic bulk upload functionality with:
    - Progress bars for uploads
    - Chunked uploads for large files
    - Concurrent upload management
    - Detailed upload statistics
    """
    
    def __init__(self, client: AEPClient) -> None:
        """Initialize enhanced bulk ingest client.
        
        Args:
            client: Authenticated AEP API client
        """
        self.client = client
        self.chunked_uploader = ChunkedUploader(client)
    
    async def upload_file_with_progress(
        self,
        batch_id: str,
        dataset_id: str,
        file_path: Union[str, Path],
        file_name: Optional[str] = None,
        show_progress: bool = True,
    ) -> Dict[str, str]:
        """Upload a file with progress tracking.
        
        Args:
            batch_id: Batch ID to upload to
            dataset_id: Dataset ID
            file_path: Path to file
            file_name: Optional custom file name
            show_progress: Whether to show progress bar
            
        Returns:
            Upload metadata
        """
        file_path = Path(file_path)
        
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")
        
        file_size = file_path.stat().st_size
        if file_size == 0:
            raise ValueError(f"File is empty: {file_path}")
        
        upload_name = file_name or file_path.name
        
        # Detect content type
        import mimetypes
        content_type = mimetypes.guess_type(file_path)[0] or "application/octet-stream"
        
        with ProgressTracker(show_progress=show_progress) as tracker:
            if show_progress:
                tracker.start_task(f"Uploading {upload_name}", total=file_size)
            
            result = await self.chunked_uploader.upload_file_chunked(
                batch_id=batch_id,
                dataset_id=dataset_id,
                file_path=file_path,
                upload_name=upload_name,
                content_type=content_type,
                progress_callback=tracker.update if show_progress else None,
            )
        
        return result
    
    async def upload_multiple_with_progress(
        self,
        batch_id: str,
        dataset_id: str,
        file_paths: List[Union[str, Path]],
        max_concurrent: int = 3,
        show_progress: bool = True,
    ) -> List[Dict[str, str]]:
        """Upload multiple files with overall progress tracking.
        
        Args:
            batch_id: Batch ID
            dataset_id: Dataset ID
            file_paths: List of file paths
            max_concurrent: Max concurrent uploads
            show_progress: Show progress
            
        Returns:
            List of upload results
        """
        semaphore = asyncio.Semaphore(max_concurrent)
        
        async def upload_with_semaphore(fp: Union[str, Path]) -> Dict[str, str]:
            async with semaphore:
                return await self.upload_file_with_progress(
                    batch_id=batch_id,
                    dataset_id=dataset_id,
                    file_path=fp,
                    show_progress=show_progress,
                )
        
        tasks = [upload_with_semaphore(fp) for fp in file_paths]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
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
