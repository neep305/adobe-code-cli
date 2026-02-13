"""Flow Service client for Adobe Experience Platform."""

import asyncio
from datetime import datetime
from typing import Any, Dict, List, Optional
from urllib.parse import quote

from adobe_experience.aep.client import AEPClient
from adobe_experience.flow.models import (
    Connection,
    Dataflow,
    DataflowRun,
    RunStatus,
    SourceConnection,
    TargetConnection,
)


class FlowServiceClient:
    """Interface to Adobe Experience Platform Flow Service API.
    
    The Flow Service manages dataflows (data ingestion pipelines) that automate
    data collection from various sources into AEP. This client provides methods
    for querying dataflows, monitoring runs, and inspecting connections.
    
    Reference: https://developer.adobe.com/experience-platform-apis/references/flow-service/
    """

    FLOW_SERVICE_PATH = "/data/foundation/flowservice"

    def __init__(self, client: AEPClient) -> None:
        """Initialize Flow Service client.
        
        Args:
            client: Authenticated AEP API client
        """
        self.client = client

    # ==================== Dataflow Methods ====================

    async def list_dataflows(
        self,
        limit: int = 50,
        property_filter: Optional[str] = None,
        orderby: Optional[str] = None,
    ) -> List[Dataflow]:
        """List dataflows in the organization.
        
        Args:
            limit: Maximum number of dataflows to return (max: 100)
            property_filter: Filter expression (e.g., "state==enabled")
            orderby: Sort field (e.g., "createdAt", "updatedAt"). Note: Do not use :desc/:asc suffix.
            
        Returns:
            List of dataflows
            
        Example:
            ```python
            # List enabled dataflows
            flows = await client.list_dataflows(
                limit=20,
                property_filter="state==enabled"
            )
            
            for flow in flows:
                print(f"{flow.name}: {flow.state}")
            ```
        """
        params: Dict[str, Any] = {
            "limit": min(limit, 100),
        }
        
        if orderby:
            params["orderby"] = orderby
        
        if property_filter:
            params["property"] = property_filter

        path = f"{self.FLOW_SERVICE_PATH}/flows"
        response = await self.client.get(path, params=params)
        
        items = response.get("items", [])
        return [Dataflow(**item) for item in items]

    async def get_dataflow(self, flow_id: str) -> Dataflow:
        """Get detailed information about a specific dataflow.
        
        Args:
            flow_id: Dataflow ID
            
        Returns:
            Dataflow object with full details including inherited attributes
            
        Raises:
            httpx.HTTPStatusError: If dataflow not found or access denied
            
        Example:
            ```python
            flow = await client.get_dataflow("d8a68c9e-1d5f-4b6c-8a4e-9f8c7d6e5f4a")
            print(f"Flow: {flow.name}")
            print(f"State: {flow.state}")
            print(f"Source IDs: {flow.source_connection_ids}")
            ```
        """
        path = f"{self.FLOW_SERVICE_PATH}/flows/{flow_id}"
        response = await self.client.get(path)
        
        # Handle both direct object and items array response formats
        if "items" in response:
            items = response["items"]
            if not items:
                raise ValueError(f"Flow with ID {flow_id} not found")
            return Dataflow(**items[0])
        else:
            return Dataflow(**response)

    async def list_dataflows_paginated(
        self,
        limit: int = 50,
        property_filter: Optional[str] = None,
        orderby: Optional[str] = None,
        max_pages: Optional[int] = None,
    ) -> List[Dataflow]:
        """List dataflows with automatic pagination.
        
        Args:
            limit: Results per page (max: 100)
            property_filter: Filter expression
            orderby: Sort field (e.g., "createdAt", "updatedAt")
            max_pages: Maximum number of pages to fetch (None = all pages)
            
        Returns:
            List of all dataflows across pages
            
        Example:
            ```python
            # Get all enabled dataflows (up to 500)
            flows = await client.list_dataflows_paginated(
                limit=100,
                property_filter="state==enabled",
                max_pages=5
            )
            ```
        """
        all_flows: List[Dataflow] = []
        page_count = 0
        start_token: Optional[str] = None

        while True:
            params: Dict[str, Any] = {
                "limit": min(limit, 100),
            }
            
            if orderby:
                params["orderby"] = orderby
            
            if property_filter:
                params["property"] = property_filter
            
            if start_token:
                params["start"] = start_token

            path = f"{self.FLOW_SERVICE_PATH}/flows"
            response = await self.client.get(path, params=params)
            
            items = response.get("items", [])
            all_flows.extend([Dataflow(**item) for item in items])
            
            page_count += 1
            
            # Check if we should continue pagination
            page_info = response.get("_page", {})
            start_token = page_info.get("next")
            
            if not start_token:
                break  # No more pages
            
            if max_pages and page_count >= max_pages:
                break  # Reached max pages limit

        return all_flows

    # ==================== Run Methods ====================

    async def list_runs(
        self,
        flow_id: str,
        limit: int = 50,
        orderby: Optional[str] = "createdAt",
    ) -> List[DataflowRun]:
        """List runs for a specific dataflow.
        
        Args:
            flow_id: Dataflow ID
            limit: Maximum number of runs to return
            orderby: Sort field (e.g., "createdAt", "updatedAt")
            
        Returns:
            List of dataflow runs
            
        Example:
            ```python
            runs = await client.list_runs(
                "d8a68c9e-1d5f-4b6c-8a4e-9f8c7d6e5f4a",
                limit=10
            )
            
            for run in runs:
                print(f"{run.id}: {run.status.value}")
            ```
        """
        params = {
            "property": f"flowId=={flow_id}",
            "limit": min(limit, 100),
        }
        
        if orderby:
            params["orderby"] = orderby

        path = f"{self.FLOW_SERVICE_PATH}/runs"
        response = await self.client.get(path, params=params)
        
        items = response.get("items", [])
        return [DataflowRun(**item) for item in items]

    async def get_run(self, run_id: str) -> DataflowRun:
        """Get detailed information about a specific run.
        
        Args:
            run_id: Run ID
            
        Returns:
            DataflowRun object with metrics and error details
            
        Example:
            ```python
            run = await client.get_run("run-12345678-abcd-ef01")
            
            if run.status.value == RunStatus.FAILED:
                for error in run.status.errors:
                    print(f"Error: {error.code} - {error.message}")
            ```
        """
        path = f"{self.FLOW_SERVICE_PATH}/runs/{run_id}"
        response = await self.client.get(path)
        return DataflowRun(**response)

    async def list_failed_runs(
        self,
        flow_id: str,
        limit: int = 50,
    ) -> List[DataflowRun]:
        """List only failed runs for a dataflow.
        
        Args:
            flow_id: Dataflow ID
            limit: Maximum number of runs to return
            
        Returns:
            List of failed dataflow runs with error details
            
        Example:
            ```python
            failed = await client.list_failed_runs(
                "d8a68c9e-1d5f-4b6c-8a4e-9f8c7d6e5f4a"
            )
            
            print(f"Found {len(failed)} failed runs")
            ```
        """
        # Get all runs and filter for failed status
        all_runs = await self.list_runs(flow_id, limit=limit)
        return [run for run in all_runs if run.status == "failed"]

    async def list_runs_by_date_range(
        self,
        flow_id: str,
        start_date: datetime,
        end_date: Optional[datetime] = None,
        limit: int = 50,
    ) -> List[DataflowRun]:
        """List runs within a date range.
        
        Args:
            flow_id: Dataflow ID
            start_date: Start date (inclusive)
            end_date: End date (inclusive), defaults to now
            limit: Maximum number of runs to return
            
        Returns:
            List of dataflow runs in date range
            
        Example:
            ```python
            from datetime import datetime, timedelta
            
            # Get runs from last 7 days
            start = datetime.now() - timedelta(days=7)
            runs = await client.list_runs_by_date_range(
                "d8a68c9e-1d5f-4b6c-8a4e-9f8c7d6e5f4a",
                start_date=start
            )
            ```
        """
        if end_date is None:
            end_date = datetime.now()
        
        # Convert to Unix milliseconds
        start_ms = int(start_date.timestamp() * 1000)
        end_ms = int(end_date.timestamp() * 1000)
        
        # Build complex filter
        property_filter = (
            f"flowId=={flow_id}&property=createdAt>={start_ms}&property=createdAt<={end_ms}"
        )
        
        params = {
            "property": property_filter,
            "limit": min(limit, 100),
        }

        path = f"{self.FLOW_SERVICE_PATH}/runs"
        response = await self.client.get(path, params=params)
        
        items = response.get("items", [])
        return [DataflowRun(**item) for item in items]

    # ==================== Connection Methods ====================

    async def get_source_connection(self, connection_id: str) -> SourceConnection:
        """Get source connection details.
        
        Args:
            connection_id: Source connection ID
            
        Returns:
            SourceConnection object
            
        Example:
            ```python
            source = await client.get_source_connection(
                "a1b2c3d4-e5f6-7890-abcd-ef1234567890"
            )
            print(f"Source: {source.name}")
            print(f"Spec: {source.connection_spec.name}")
            ```
        """
        path = f"{self.FLOW_SERVICE_PATH}/sourceConnections/{connection_id}"
        response = await self.client.get(path)
        return SourceConnection(**response)

    async def get_target_connection(self, connection_id: str) -> TargetConnection:
        """Get target connection details.
        
        Args:
            connection_id: Target connection ID
            
        Returns:
            TargetConnection object
            
        Example:
            ```python
            target = await client.get_target_connection(
                "b2c3d4e5-f6a7-8901-bcde-f12345678901"
            )
            
            # Get dataset ID from params
            dataset_id = target.params.get("dataSetId")
            print(f"Target dataset: {dataset_id}")
            ```
        """
        path = f"{self.FLOW_SERVICE_PATH}/targetConnections/{connection_id}"
        response = await self.client.get(path)
        return TargetConnection(**response)

    async def get_connection(self, connection_id: str) -> Connection:
        """Get base connection details.
        
        Args:
            connection_id: Connection ID
            
        Returns:
            Connection object with auth details (credentials masked)
            
        Example:
            ```python
            conn = await client.get_connection("base-conn-123")
            print(f"Connection: {conn.name}")
            print(f"Type: {conn.connection_spec.name}")
            print(f"State: {conn.state}")
            ```
        """
        path = f"{self.FLOW_SERVICE_PATH}/connections/{connection_id}"
        response = await self.client.get(path)
        return Connection(**response)

    async def get_dataflow_connections(
        self,
        flow_id: str,
    ) -> Dict[str, Any]:
        """Get all connection details for a dataflow.
        
        Convenience method that fetches dataflow and all its connections
        in parallel for efficient inspection.
        
        Args:
            flow_id: Dataflow ID
            
        Returns:
            Dictionary with dataflow, source_connections, and target_connections
            
        Example:
            ```python
            details = await client.get_dataflow_connections(
                "d8a68c9e-1d5f-4b6c-8a4e-9f8c7d6e5f4a"
            )
            
            print(f"Dataflow: {details['dataflow'].name}")
            for src in details['source_connections']:
                print(f"Source: {src.name}")
            for tgt in details['target_connections']:
                print(f"Target: {tgt.name}")
            ```
        """
        # First get dataflow
        dataflow = await self.get_dataflow(flow_id)
        
        # Fetch all connections in parallel
        source_tasks = [
            self.get_source_connection(conn_id)
            for conn_id in dataflow.source_connection_ids
        ]
        target_tasks = [
            self.get_target_connection(conn_id)
            for conn_id in dataflow.target_connection_ids
        ]
        
        source_connections = await asyncio.gather(*source_tasks, return_exceptions=True)
        target_connections = await asyncio.gather(*target_tasks, return_exceptions=True)
        
        # Filter out exceptions (e.g., if connection was deleted)
        source_connections = [
            conn for conn in source_connections if isinstance(conn, SourceConnection)
        ]
        target_connections = [
            conn for conn in target_connections if isinstance(conn, TargetConnection)
        ]
        
        return {
            "dataflow": dataflow,
            "source_connections": source_connections,
            "target_connections": target_connections,
        }

    # ==================== Analysis Methods ====================

    async def analyze_dataflow_health(
        self,
        flow_id: str,
        lookback_days: int = 7,
    ) -> Dict[str, Any]:
        """Analyze dataflow health based on recent runs.
        
        Args:
            flow_id: Dataflow ID
            lookback_days: Number of days to analyze
            
        Returns:
            Dictionary with health metrics and statistics
            
        Example:
            ```python
            health = await client.analyze_dataflow_health(
                "d8a68c9e-1d5f-4b6c-8a4e-9f8c7d6e5f4a",
                lookback_days=7
            )
            
            print(f"Success rate: {health['success_rate']:.1f}%")
            print(f"Total runs: {health['total_runs']}")
            print(f"Failed runs: {health['failed_runs']}")
            ```
        """
        # Get runs from last N days
        start_date = datetime.now()
        from datetime import timedelta
        start_date = start_date - timedelta(days=lookback_days)
        
        runs = await self.list_runs_by_date_range(
            flow_id,
            start_date=start_date,
            limit=100,
        )
        
        if not runs:
            return {
                "total_runs": 0,
                "success_rate": 0.0,
                "failed_runs": 0,
                "success_runs": 0,
                "pending_runs": 0,
                "average_duration_seconds": 0,
                "errors": [],
            }
        
        # Calculate statistics
        total_runs = len(runs)
        success_runs = sum(1 for r in runs if r.status.value == RunStatus.SUCCESS)
        failed_runs = sum(1 for r in runs if r.status.value == RunStatus.FAILED)
        pending_runs = sum(
            1 for r in runs
            if r.status.value in [RunStatus.PENDING, RunStatus.IN_PROGRESS]
        )
        
        success_rate = (success_runs / total_runs * 100) if total_runs > 0 else 0.0
        
        # Calculate average duration for completed runs
        durations = []
        for run in runs:
            if run.metrics and run.metrics.duration_summary:
                ds = run.metrics.duration_summary
                if ds.started_at_utc and ds.completed_at_utc:
                    duration = (ds.completed_at_utc - ds.started_at_utc) / 1000.0
                    durations.append(duration)
        
        avg_duration = sum(durations) / len(durations) if durations else 0
        
        # Collect unique errors
        errors = []
        for run in runs:
            if run.status.value == RunStatus.FAILED:
                for error in run.status.errors:
                    errors.append({
                        "code": error.code,
                        "message": error.message,
                        "run_id": run.id,
                    })
        
        return {
            "dataflow_id": flow_id,
            "lookback_days": lookback_days,
            "total_runs": total_runs,
            "success_runs": success_runs,
            "failed_runs": failed_runs,
            "pending_runs": pending_runs,
            "success_rate": success_rate,
            "average_duration_seconds": avg_duration,
            "errors": errors,
        }
