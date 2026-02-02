"""Catalog Service client for Adobe Experience Platform."""

import asyncio
from typing import Any, Dict, List, Optional
from urllib.parse import quote

from adobe_experience.aep.client import AEPClient
from adobe_experience.catalog.models import (
    Batch,
    BatchInputFormat,
    BatchStatus,
    Dataset,
    DatasetSchemaRef,
    DatasetTags,
    DataSetFile,
)


class CatalogServiceClient:
    """Interface to Adobe Experience Platform Catalog Service API.
    
    The Catalog Service manages datasets, batches, and data files within AEP.
    This client provides methods for dataset lifecycle management and batch
    ingestion operations.
    
    Reference: https://developer.adobe.com/experience-platform-apis/references/catalog/
    """

    CATALOG_PATH = "/data/foundation/catalog"
    IMPORT_PATH = "/data/foundation/import"

    def __init__(self, client: AEPClient) -> None:
        """Initialize Catalog Service client.
        
        Args:
            client: Authenticated AEP API client
        """
        self.client = client

    # ==================== Dataset Methods ====================

    async def create_dataset(
        self,
        name: str,
        schema_id: str,
        description: Optional[str] = None,
        enable_profile: bool = False,
        enable_identity: bool = False,
    ) -> str:
        """Create a new dataset in Adobe Experience Platform.
        
        Args:
            name: Dataset name
            schema_id: Full XDM schema ID (e.g., https://ns.adobe.com/{tenant}/schemas/{id})
            description: Optional dataset description
            enable_profile: Enable for Real-Time Customer Profile
            enable_identity: Enable for Identity Service
            
        Returns:
            Dataset ID
            
        Raises:
            ValueError: If schema_id is invalid or dataset name already exists
            httpx.HTTPStatusError: For API errors
            
        Example:
            >>> async with AEPClient(config) as aep_client:
            ...     catalog = CatalogServiceClient(aep_client)
            ...     dataset_id = await catalog.create_dataset(
            ...         name="Customer Events",
            ...         schema_id="https://ns.adobe.com/tenant/schemas/abc123",
            ...         enable_profile=True
            ...     )
        """
        path = f"{self.CATALOG_PATH}/dataSets"

        dataset_data: Dict[str, Any] = {
            "name": name,
            "schemaRef": {
                "id": schema_id,
                "contentType": "application/vnd.adobe.xed+json;version=1",
            },
        }

        if description:
            dataset_data["description"] = description

        if enable_profile or enable_identity:
            tags: Dict[str, List[str]] = {}
            if enable_profile:
                tags["unifiedProfile"] = ["enabled:true"]
            if enable_identity:
                tags["unifiedIdentity"] = ["enabled:true"]
            dataset_data["tags"] = tags

        try:
            response = await self.client.post(path, json=dataset_data)
            # Response format: ["@/dataSets/5c8c3c555033b814b69f947f"]
            if isinstance(response, list) and len(response) > 0:
                return response[0].split("/")[-1]
            else:
                raise ValueError(f"Unexpected response format: {response}")
        except Exception as e:
            if "409" in str(e) or "already exists" in str(e).lower():
                raise ValueError(f"Dataset with name '{name}' already exists") from e
            elif "400" in str(e):
                raise ValueError(f"Invalid schema reference or dataset configuration: {e}") from e
            raise

    async def list_datasets(
        self,
        limit: int = 50,
        properties: Optional[List[str]] = None,
        schema_id: Optional[str] = None,
        state: Optional[str] = None,
    ) -> List[Dataset]:
        """List datasets in Adobe Experience Platform.
        
        Args:
            limit: Maximum number of datasets to return (default: 50, max: 100)
            properties: Specific properties to include in response
            schema_id: Filter by schema ID
            state: Filter by state (DRAFT or ENABLED)
            
        Returns:
            List of Dataset objects
            
        Example:
            >>> datasets = await catalog.list_datasets(
            ...     limit=10,
            ...     properties=["name", "schemaRef", "state"]
            ... )
        """
        path = f"{self.CATALOG_PATH}/dataSets"

        params: Dict[str, Any] = {"limit": min(limit, 100)}
        if properties:
            params["properties"] = ",".join(properties)
        if schema_id:
            params["schemaRef.id"] = schema_id
        if state:
            params["state"] = state

        response = await self.client.get(path, params=params)

        # Response format: {"dataset_id1": {...}, "dataset_id2": {...}}
        datasets = []
        for dataset_id, dataset_data in response.items():
            try:
                dataset_data["@id"] = dataset_id
                datasets.append(Dataset(**dataset_data))
            except Exception:
                # Skip datasets with parsing errors
                continue

        return datasets

    async def get_dataset(self, dataset_id: str) -> Dataset:
        """Get dataset details by ID.
        
        Args:
            dataset_id: Dataset ID
            
        Returns:
            Dataset object with full details
            
        Raises:
            ValueError: If dataset not found
            
        Example:
            >>> dataset = await catalog.get_dataset("5c8c3c555033b814b69f947f")
        """
        encoded_id = quote(dataset_id, safe="")
        path = f"{self.CATALOG_PATH}/dataSets/{encoded_id}"

        try:
            response = await self.client.get(path)
            response["@id"] = dataset_id
            return Dataset(**response)
        except Exception as e:
            if "404" in str(e):
                raise ValueError(f"Dataset not found: {dataset_id}") from e
            raise

    async def update_dataset(
        self,
        dataset_id: str,
        name: Optional[str] = None,
        description: Optional[str] = None,
        tags: Optional[DatasetTags] = None,
    ) -> Dataset:
        """Update dataset properties (PATCH operation).
        
        Args:
            dataset_id: Dataset ID
            name: New dataset name
            description: New description
            tags: New tags configuration
            
        Returns:
            Updated Dataset object
            
        Example:
            >>> dataset = await catalog.update_dataset(
            ...     dataset_id="5c8c3c555033b814b69f947f",
            ...     description="Updated customer events dataset"
            ... )
        """
        encoded_id = quote(dataset_id, safe="")
        path = f"{self.CATALOG_PATH}/dataSets/{encoded_id}"

        updates: Dict[str, Any] = {}
        if name is not None:
            updates["name"] = name
        if description is not None:
            updates["description"] = description
        if tags is not None:
            updates["tags"] = tags.model_dump(by_alias=True, exclude_none=True)

        response = await self.client.patch(path, json=updates)
        response["@id"] = dataset_id
        return Dataset(**response)

    async def delete_dataset(self, dataset_id: str) -> None:
        """Delete a dataset.
        
        Args:
            dataset_id: Dataset ID to delete
            
        Raises:
            ValueError: If dataset not found or cannot be deleted
            
        Example:
            >>> await catalog.delete_dataset("5c8c3c555033b814b69f947f")
        """
        encoded_id = quote(dataset_id, safe="")
        path = f"{self.CATALOG_PATH}/dataSets/{encoded_id}"

        try:
            await self.client.delete(path)
        except Exception as e:
            if "404" in str(e):
                raise ValueError(f"Dataset not found: {dataset_id}") from e
            raise

    async def enable_dataset_for_profile(self, dataset_id: str) -> Dataset:
        """Enable dataset for Real-Time Customer Profile.
        
        Args:
            dataset_id: Dataset ID
            
        Returns:
            Updated Dataset object with Profile enabled
            
        Example:
            >>> dataset = await catalog.enable_dataset_for_profile("5c8c3c555033b814b69f947f")
        """
        return await self.update_dataset(
            dataset_id=dataset_id,
            tags=DatasetTags(unified_profile=["enabled:true"]),
        )

    async def enable_dataset_for_identity(self, dataset_id: str) -> Dataset:
        """Enable dataset for Identity Service.
        
        Args:
            dataset_id: Dataset ID
            
        Returns:
            Updated Dataset object with Identity enabled
            
        Example:
            >>> dataset = await catalog.enable_dataset_for_identity("5c8c3c555033b814b69f947f")
        """
        return await self.update_dataset(
            dataset_id=dataset_id,
            tags=DatasetTags(unified_identity=["enabled:true"]),
        )

    # ==================== Batch Methods ====================

    async def create_batch(
        self,
        dataset_id: str,
        format: str = "parquet",
    ) -> str:
        """Create a new batch for data ingestion.
        
        Args:
            dataset_id: Target dataset ID
            format: Input format (parquet, json, csv, avro)
            
        Returns:
            Batch ID
            
        Example:
            >>> batch_id = await catalog.create_batch(
            ...     dataset_id="5c8c3c555033b814b69f947f",
            ...     format="json"
            ... )
        """
        path = f"{self.IMPORT_PATH}/batches"

        batch_data = {
            "datasetId": dataset_id,
            "inputFormat": {"format": format},
        }

        response = await self.client.post(path, json=batch_data)
        return response["id"]

    async def get_batch(self, batch_id: str) -> Batch:
        """Get batch status and details.
        
        Args:
            batch_id: Batch ID
            
        Returns:
            Batch object with current status
            
        Raises:
            ValueError: If batch not found
            
        Example:
            >>> batch = await catalog.get_batch("5d01230fc78a4e4f8c0c6b387b4b8d1c")
            >>> print(batch.status)
        """
        path = f"{self.CATALOG_PATH}/batches/{batch_id}"

        try:
            response = await self.client.get(path)
            # Response format: {batch_id: {...}}
            batch_data = list(response.values())[0]
            return Batch(**batch_data)
        except Exception as e:
            if "404" in str(e):
                raise ValueError(f"Batch not found: {batch_id}") from e
            raise

    async def list_batches(
        self,
        limit: int = 50,
        dataset_id: Optional[str] = None,
        status: Optional[BatchStatus] = None,
    ) -> List[Batch]:
        """List batches with optional filters.
        
        Args:
            limit: Maximum number of batches to return
            dataset_id: Filter by dataset ID
            status: Filter by batch status
            
        Returns:
            List of Batch objects
            
        Example:
            >>> batches = await catalog.list_batches(
            ...     dataset_id="5c8c3c555033b814b69f947f",
            ...     status=BatchStatus.SUCCESS
            ... )
        """
        path = f"{self.CATALOG_PATH}/batches"

        params: Dict[str, Any] = {"limit": min(limit, 100)}
        if dataset_id:
            params["dataSet"] = dataset_id
        if status:
            params["status"] = status.value

        response = await self.client.get(path, params=params)

        # Response format: {batch_id: {...}, ...}
        batches = []
        for batch_id, batch_data in response.items():
            try:
                batches.append(Batch(**batch_data))
            except Exception:
                continue

        return batches

    async def complete_batch(self, batch_id: str) -> None:
        """Signal batch completion (all files uploaded).
        
        Args:
            batch_id: Batch ID to complete
            
        Example:
            >>> await catalog.complete_batch("5d01230fc78a4e4f8c0c6b387b4b8d1c")
        """
        path = f"{self.IMPORT_PATH}/batches/{batch_id}"
        await self.client.post(path, params={"action": "COMPLETE"})

    async def abort_batch(self, batch_id: str) -> None:
        """Abort a batch ingestion.
        
        Args:
            batch_id: Batch ID to abort
            
        Example:
            >>> await catalog.abort_batch("5d01230fc78a4e4f8c0c6b387b4b8d1c")
        """
        path = f"{self.IMPORT_PATH}/batches/{batch_id}"
        await self.client.post(path, params={"action": "ABORT"})

    async def wait_for_batch_completion(
        self,
        batch_id: str,
        timeout: int = 300,
        poll_interval: int = 5,
    ) -> Batch:
        """Poll batch status until completion (success or failure).
        
        Args:
            batch_id: Batch ID to monitor
            timeout: Maximum wait time in seconds (default: 300 = 5 minutes)
            poll_interval: Seconds between status checks (default: 5)
            
        Returns:
            Final Batch object
            
        Raises:
            TimeoutError: If batch doesn't complete within timeout
            ValueError: If batch fails or is aborted
            
        Example:
            >>> batch_id = await catalog.create_batch(dataset_id, "json")
            >>> # ... upload files ...
            >>> await catalog.complete_batch(batch_id)
            >>> final_batch = await catalog.wait_for_batch_completion(batch_id)
            >>> print(f"Ingested {final_batch.metrics.records_written} records")
        """
        start_time = asyncio.get_event_loop().time()

        while True:
            batch = await self.get_batch(batch_id)

            if batch.status == BatchStatus.SUCCESS:
                return batch
            elif batch.status == BatchStatus.FAILED:
                errors = "\n".join(f"  - {e.code}: {e.description}" for e in batch.errors)
                failure_msg = f"Batch {batch_id} failed"
                if batch.metrics and batch.metrics.failure_reason:
                    failure_msg += f": {batch.metrics.failure_reason}"
                if errors:
                    failure_msg += f"\nErrors:\n{errors}"
                raise ValueError(failure_msg)
            elif batch.status == BatchStatus.ABORTED:
                raise ValueError(f"Batch {batch_id} was aborted")

            elapsed = asyncio.get_event_loop().time() - start_time
            if elapsed > timeout:
                raise TimeoutError(
                    f"Batch {batch_id} did not complete within {timeout}s (current status: {batch.status.value})"
                )

            await asyncio.sleep(poll_interval)

    # ==================== DataSetFile Methods ====================

    async def list_dataset_files(
        self,
        dataset_id: Optional[str] = None,
        batch_id: Optional[str] = None,
        limit: int = 50,
    ) -> List[DataSetFile]:
        """List files in a dataset or batch.
        
        Args:
            dataset_id: Filter by dataset ID
            batch_id: Filter by batch ID
            limit: Maximum number of files to return
            
        Returns:
            List of DataSetFile objects
            
        Example:
            >>> files = await catalog.list_dataset_files(
            ...     batch_id="5d01230fc78a4e4f8c0c6b387b4b8d1c"
            ... )
        """
        path = f"{self.CATALOG_PATH}/dataSetFiles"

        params: Dict[str, Any] = {"limit": min(limit, 100)}
        if dataset_id:
            params["dataSetId"] = dataset_id
        if batch_id:
            params["batchId"] = batch_id

        response = await self.client.get(path, params=params)

        # Response format: {file_id: {...}, ...}
        files = []
        for file_id, file_data in response.items():
            try:
                file_data["@id"] = file_id
                files.append(DataSetFile(**file_data))
            except Exception:
                continue

        return files
