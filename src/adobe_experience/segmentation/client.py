"""Segmentation Service client for Adobe Experience Platform."""

import asyncio
from typing import Any, Dict, List, Optional
from urllib.parse import quote

from adobe_experience.aep.client import AEPClient
from adobe_experience.segmentation.models import (
    PQLExpression,
    SegmentDefinition,
    SegmentEstimate,
    SegmentExportJob,
    SegmentJob,
    SegmentJobStatus,
    SegmentStatus,
)


class SegmentationServiceClient:
    """Interface to Adobe Experience Platform Segmentation Service API.
    
    The Segmentation Service creates and manages audience segments from
    Real-Time Customer Profile data using PQL (Profile Query Language).
    
    API Reference:
        https://developer.adobe.com/experience-platform-apis/references/segmentation/
    
    Key Concepts:
        - Segment Definition: PQL-based criteria defining a subset of profiles
        - Segment Job: Evaluation process that determines segment membership
        - Profile Segmentation: Membership data attached to customer profiles
    
    Example:
        >>> async with AEPClient(config) as aep_client:
        ...     segment_client = SegmentationServiceClient(aep_client)
        ...     segment_id = await segment_client.create_segment(
        ...         name="High Value Customers",
        ...         pql_expression="person.totalSpent > 1000"
        ...     )
    """

    SEGMENTATION_PATH = "/data/core/ups"

    def __init__(self, client: AEPClient) -> None:
        """Initialize Segmentation Service client.
        
        Args:
            client: Authenticated AEP API client
        """
        self.client = client

    # ==================== Segment Definition Methods ====================

    async def create_segment(
        self,
        name: str,
        pql_expression: str,
        schema_name: str = "_xdm.context.profile",
        description: Optional[str] = None,
        ttl_in_days: Optional[int] = None,
    ) -> str:
        """Create a new segment definition.
        
        Args:
            name: Segment name
            pql_expression: PQL query string defining segment criteria
            schema_name: Schema to evaluate against (default: Profile)
            description: Optional segment description
            ttl_in_days: Time-to-live for segment membership in days
            
        Returns:
            Segment ID
            
        Raises:
            ValueError: If PQL expression is invalid
            httpx.HTTPStatusError: For API errors
            
        Example:
            >>> segment_id = await client.create_segment(
            ...     name="Recent Purchasers",
            ...     pql_expression='person.lastPurchase > now() - duration("P7D")',
            ...     description="Customers who purchased in the last 7 days"
            ... )
        """
        path = f"{self.SEGMENTATION_PATH}/segment/definitions"

        segment_data: Dict[str, Any] = {
            "name": name,
            "expression": {
                "type": "PQL",
                "format": "pql/text",
                "value": pql_expression,
            },
            "schema": {"name": schema_name},
        }

        if description:
            segment_data["description"] = description

        if ttl_in_days is not None:
            segment_data["ttlInDays"] = ttl_in_days

        try:
            response = await self.client.post(path, json=segment_data)
            return response.get("id", "")
        except Exception as e:
            raise ValueError(f"Failed to create segment: {str(e)}") from e

    async def list_segments(
        self,
        limit: int = 50,
        status: Optional[SegmentStatus] = None,
        orderby: Optional[str] = None,
    ) -> List[SegmentDefinition]:
        """List segment definitions.
        
        Args:
            limit: Maximum number of segments to return (1-100)
            status: Filter by segment status (DRAFT, ACTIVE, INACTIVE)
            orderby: Sort field (optional, not supported by all AEP versions)
            
        Returns:
            List of segment definitions
            
        Example:
            >>> segments = await client.list_segments(limit=20, status=SegmentStatus.ACTIVE)
            >>> for segment in segments:
            ...     print(f"{segment.name}: {segment.expression.value}")
        """
        path = f"{self.SEGMENTATION_PATH}/segment/definitions"
        
        params: Dict[str, Any] = {
            "limit": min(limit, 100),
        }
        
        # Only add orderby if explicitly provided (not all AEP versions support it)
        if orderby:
            params["orderby"] = orderby
        
        if status:
            params["property"] = f"status=={status.value}"

        response = await self.client.get(path, params=params)
        
        segments = []
        if "children" in response:
            for segment_data in response["children"]:
                try:
                    segments.append(SegmentDefinition(**segment_data))
                except Exception as e:
                    # Skip malformed segments
                    continue
        
        return segments

    async def get_segment(self, segment_id: str) -> SegmentDefinition:
        """Get segment definition details.
        
        Args:
            segment_id: Segment ID
            
        Returns:
            Segment definition
            
        Raises:
            ValueError: If segment not found
            
        Example:
            >>> segment = await client.get_segment("abc123...")
            >>> print(f"PQL: {segment.expression.value}")
        """
        path = f"{self.SEGMENTATION_PATH}/segment/definitions/{segment_id}"
        
        try:
            response = await self.client.get(path)
            return SegmentDefinition(**response)
        except Exception as e:
            raise ValueError(f"Segment {segment_id} not found: {str(e)}") from e

    async def update_segment(
        self,
        segment_id: str,
        name: Optional[str] = None,
        pql_expression: Optional[str] = None,
        description: Optional[str] = None,
        status: Optional[SegmentStatus] = None,
    ) -> SegmentDefinition:
        """Update an existing segment definition.
        
        Args:
            segment_id: Segment ID
            name: New segment name
            pql_expression: New PQL expression
            description: New description
            status: New status (ACTIVE, INACTIVE)
            
        Returns:
            Updated segment definition
            
        Example:
            >>> updated = await client.update_segment(
            ...     segment_id="abc123",
            ...     status=SegmentStatus.ACTIVE
            ... )
        """
        path = f"{self.SEGMENTATION_PATH}/segment/definitions/{segment_id}"
        
        update_data: Dict[str, Any] = {}
        
        if name is not None:
            update_data["name"] = name
        
        if pql_expression is not None:
            update_data["expression"] = {
                "type": "PQL",
                "format": "pql/text",
                "value": pql_expression,
            }
        
        if description is not None:
            update_data["description"] = description
        
        if status is not None:
            update_data["status"] = status.value

        try:
            response = await self.client.patch(path, json=update_data)
            return SegmentDefinition(**response)
        except Exception as e:
            raise ValueError(f"Failed to update segment: {str(e)}") from e

    async def delete_segment(self, segment_id: str) -> None:
        """Delete a segment definition.
        
        Args:
            segment_id: Segment ID
            
        Raises:
            ValueError: If segment not found or cannot be deleted
            
        Example:
            >>> await client.delete_segment("abc123...")
        """
        path = f"{self.SEGMENTATION_PATH}/segment/definitions/{segment_id}"
        
        try:
            await self.client.delete(path)
        except Exception as e:
            raise ValueError(f"Failed to delete segment: {str(e)}") from e

    # ==================== Segment Evaluation Methods ====================

    async def evaluate_segment(
        self,
        segment_id: str,
        enable_profile_update: bool = True,
    ) -> str:
        """Trigger on-demand segment evaluation.
        
        Creates a segment job that evaluates the segment criteria against
        all eligible profiles and updates segment membership.
        
        Args:
            segment_id: Segment ID to evaluate
            enable_profile_update: Update profile segment membership
            
        Returns:
            Segment job ID
            
        Example:
            >>> job_id = await client.evaluate_segment("abc123...")
            >>> job = await client.get_segment_job(job_id)
            >>> print(f"Status: {job.status}")
        """
        path = f"{self.SEGMENTATION_PATH}/segment/jobs"
        
        job_data = {
            "segmentId": segment_id,
            "type": "BATCH",
            "enableProfileUpdate": enable_profile_update,
        }
        
        try:
            response = await self.client.post(path, json=job_data)
            return response.get("id", "")
        except Exception as e:
            raise ValueError(f"Failed to evaluate segment: {str(e)}") from e

    async def list_segment_jobs(
        self,
        limit: int = 50,
        status: Optional[SegmentJobStatus] = None,
    ) -> List[SegmentJob]:
        """List segment evaluation jobs.
        
        Args:
            limit: Maximum number of jobs to return
            status: Filter by job status
            
        Returns:
            List of segment jobs
        """
        path = f"{self.SEGMENTATION_PATH}/segment/jobs"
        
        params: Dict[str, Any] = {"limit": min(limit, 100)}
        
        if status:
            params["property"] = f"status=={status.value}"

        response = await self.client.get(path, params=params)
        
        jobs = []
        if "children" in response:
            for job_data in response["children"]:
                try:
                    jobs.append(SegmentJob(**job_data))
                except Exception:
                    continue
        
        return jobs

    async def get_segment_job(self, job_id: str) -> SegmentJob:
        """Get segment evaluation job status and metrics.
        
        Args:
            job_id: Segment job ID
            
        Returns:
            Segment job details
            
        Example:
            >>> job = await client.get_segment_job("job123...")
            >>> if job.status == SegmentJobStatus.SUCCEEDED:
            ...     print(f"Evaluated {job.metrics.segmentedProfileCounter}")
        """
        path = f"{self.SEGMENTATION_PATH}/segment/jobs/{job_id}"
        
        try:
            response = await self.client.get(path)
            return SegmentJob(**response)
        except Exception as e:
            raise ValueError(f"Segment job {job_id} not found: {str(e)}") from e

    async def wait_for_job_completion(
        self,
        job_id: str,
        poll_interval: float = 5.0,
        max_wait: float = 300.0,
    ) -> SegmentJob:
        """Wait for segment job to complete.
        
        Polls the job status until it reaches a terminal state
        (SUCCEEDED, FAILED, CANCELLED).
        
        Args:
            job_id: Segment job ID
            poll_interval: Seconds between status checks
            max_wait: Maximum seconds to wait
            
        Returns:
            Final segment job state
            
        Raises:
            TimeoutError: If job doesn't complete within max_wait
            ValueError: If job fails
        """
        start_time = asyncio.get_event_loop().time()
        
        while True:
            job = await self.get_segment_job(job_id)
            
            if job.status in [
                SegmentJobStatus.SUCCEEDED,
                SegmentJobStatus.FAILED,
                SegmentJobStatus.CANCELLED,
            ]:
                if job.status == SegmentJobStatus.FAILED:
                    errors = job.errors or []
                    error_msg = "; ".join([str(e) for e in errors[:3]])
                    raise ValueError(f"Segment job failed: {error_msg}")
                
                return job
            
            elapsed = asyncio.get_event_loop().time() - start_time
            if elapsed > max_wait:
                raise TimeoutError(
                    f"Segment job {job_id} did not complete within {max_wait}s"
                )
            
            await asyncio.sleep(poll_interval)

    # ==================== Preview & Estimation Methods ====================

    async def estimate_segment_size(
        self,
        pql_expression: str,
        schema_name: str = "_xdm.context.profile",
    ) -> SegmentEstimate:
        """Estimate segment size without full evaluation.
        
        Provides a quick estimate of how many profiles match the criteria.
        
        Args:
            pql_expression: PQL query string
            schema_name: Schema to evaluate against
            
        Returns:
            Segment size estimate
            
        Example:
            >>> estimate = await client.estimate_segment_size(
            ...     pql_expression="person.age > 25"
            ... )
            >>> print(f"Estimated {estimate.estimatedSize} profiles")
        """
        path = f"{self.SEGMENTATION_PATH}/estimate"
        
        estimate_data = {
            "predicateExpression": pql_expression,
            "predicateModel": schema_name,
        }
        
        try:
            response = await self.client.post(path, json=estimate_data)
            return SegmentEstimate(**response)
        except Exception as e:
            raise ValueError(f"Failed to estimate segment: {str(e)}") from e

    # ==================== Export Methods ====================

    async def export_segment(
        self,
        segment_id: str,
        dataset_id: str,
    ) -> str:
        """Export segment membership to a dataset.
        
        Creates an export job that writes segment results to a dataset
        for downstream consumption.
        
        Args:
            segment_id: Segment ID
            dataset_id: Target dataset ID
            
        Returns:
            Export job ID
        """
        path = f"{self.SEGMENTATION_PATH}/export/jobs"
        
        export_data = {
            "segments": [{"segmentId": segment_id}],
            "destination": {
                "datasetId": dataset_id,
                "segmentPerBatch": False,
            },
        }
        
        try:
            response = await self.client.post(path, json=export_data)
            return response.get("id", "")
        except Exception as e:
            raise ValueError(f"Failed to export segment: {str(e)}") from e

    async def get_export_job(self, job_id: str) -> SegmentExportJob:
        """Get segment export job status.
        
        Args:
            job_id: Export job ID
            
        Returns:
            Export job details
        """
        path = f"{self.SEGMENTATION_PATH}/export/jobs/{job_id}"
        
        try:
            response = await self.client.get(path)
            return SegmentExportJob(**response)
        except Exception as e:
            raise ValueError(f"Export job {job_id} not found: {str(e)}") from e
