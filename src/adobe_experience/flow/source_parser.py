"""Utilities for parsing dataflow source connection parameters into readable entity names."""

from typing import Optional, Dict, Any

from adobe_experience.flow.models import SourceConnection


def extract_source_entity(source_connection: SourceConnection) -> Optional[str]:
    """Extract human-readable source entity from connection params.
    
    Parses the connection params dict to extract meaningful data source information
    like bucket names, table names, object names, etc. based on the connector type.
    
    Args:
        source_connection: Source connection with params dict
        
    Returns:
        Formatted source entity string, or None if params cannot be parsed
        
    Examples:
        S3: "s3://customer-data/daily-exports"
        Salesforce: "Object: Account"
        Database: "schema.table_name"
        Azure Blob: "azure://container/path"
        ADLS Gen2: "adls://filesystem/directory"
    """
    if not source_connection.params:
        return None
    
    params = source_connection.params
    spec_id = source_connection.connection_spec.id if source_connection.connection_spec else ""
    
    # Google Cloud Storage (check before S3 since both use bucketName)
    if spec_id == "32e8f412-cdf7-464c-9885-8a96ce6e7b1e" and "bucketName" in params:
        bucket = params["bucketName"]
        path = params.get("path", "") or params.get("folderPath", "")
        return f"gs://{bucket}{path}"
    
    # Amazon S3
    if "s3" in params:
        s3 = params["s3"]
        bucket = s3.get("bucketName", "")
        path = s3.get("folderPath", "") or s3.get("path", "")
        if bucket:
            return f"s3://{bucket}{path}"
    
    # S3 bucket directly in params (alternative format)
    if "bucketName" in params:
        bucket = params["bucketName"]
        path = params.get("folderPath", "") or params.get("path", "")
        return f"s3://{bucket}{path}"
    
    # Salesforce
    if "objectName" in params:
        obj_name = params["objectName"]
        return f"Salesforce Object: {obj_name}"
    
    # Database connectors (MySQL, PostgreSQL, SQL Server, etc.)
    if "tableName" in params:
        schema = params.get("schemaName", "") or params.get("schema", "")
        table = params["tableName"]
        if schema:
            return f"{schema}.{table}"
        return table
    
    # Azure Blob Storage
    if "container" in params or "containerName" in params:
        container = params.get("containerName") or params.get("container", "")
        path = params.get("blobPath", "") or params.get("path", "") or params.get("folderPath", "")
        if container:
            return f"azure://{container}{path}"
    
    # Azure Data Lake Storage Gen2
    if "fileSystem" in params or "filesystem" in params:
        fs = params.get("filesystem") or params.get("fileSystem", "")
        path = params.get("directoryPath", "") or params.get("path", "") or params.get("folderPath", "")
        if fs:
            return f"adls://{fs}{path}"
    
    # FTP/SFTP
    if "host" in params and ("path" in params or "remotePath" in params):
        host = params["host"]
        path = params.get("remotePath") or params.get("path", "")
        protocol = "sftp" if params.get("port") == 22 else "ftp"
        return f"{protocol}://{host}{path}"
    
    # HTTP/REST API
    if "url" in params or "endpoint" in params:
        url = params.get("url") or params.get("endpoint", "")
        return f"API: {url}"
    
    # Generic file path
    if "path" in params and len(params) == 1:
        return params["path"]
    
    # Fallback: Try to find most descriptive param
    descriptive_keys = ["name", "entityName", "resource", "source", "location"]
    for key in descriptive_keys:
        if key in params and isinstance(params[key], str):
            return params[key]
    
    return None


def format_source_params(params: Dict[str, Any], max_depth: int = 2) -> str:
    """Format source params dict for display with controlled nesting.
    
    Args:
        params: Parameters dictionary
        max_depth: Maximum nesting depth to display
        
    Returns:
        Formatted string representation
    """
    if not params:
        return "{}"
    
    def _format_value(value: Any, depth: int = 0) -> str:
        if depth >= max_depth:
            return str(value)
        
        if isinstance(value, dict):
            if not value:
                return "{}"
            items = []
            for k, v in value.items():
                formatted_v = _format_value(v, depth + 1)
                items.append(f"{k}: {formatted_v}")
            return "{ " + ", ".join(items) + " }"
        elif isinstance(value, list):
            if not value:
                return "[]"
            if len(value) > 3:
                return f"[{len(value)} items]"
            items = [_format_value(v, depth + 1) for v in value]
            return "[" + ", ".join(items) + "]"
        elif isinstance(value, str):
            if len(value) > 50:
                return f'"{value[:47]}..."'
            return f'"{value}"'
        else:
            return str(value)
    
    return _format_value(params)


def get_source_type_from_spec(connection_spec_id: str) -> Optional[str]:
    """Get human-readable source type from connection spec ID.
    
    Args:
        connection_spec_id: Connection spec UUID
        
    Returns:
        Source type name or None
    """
    # Common AEP connector spec IDs
    spec_map = {
        "ecadc60c-7455-4d65-9f77-8f1b1e6e1a1a": "Amazon S3",
        "b7bf2577-4520-42c9-bae9-cad01560f7bc": "Azure Blob Storage",
        "0ed90a81-07f4-4586-8190-b40eccef1c5a": "Azure Data Lake Storage Gen2",
        "26d738e0-8963-47ea-aadf-c60de735468a": "Google Cloud Storage",
        "cfc0fee1-7dc0-40ef-b73e-d8b134c436f5": "Salesforce",
        "3417a6f7-6f2f-4db8-9b5a-5f4c9e1a6e1a": "MySQL",
        "26d738e0-8963-47ea-aadf-c60de735468a": "PostgreSQL",
        "dd51f8c2-36bd-4be9-8da9-8c7f7e9e1a1a": "Microsoft SQL Server",
        "9b6a-8be9-47ea-5f4c-26d738e012345": "Oracle",
        "5d6c00ce-5dbd-4b24-9b2e-8a4b2c3d4e5f": "SFTP",
    }
    return spec_map.get(connection_spec_id)


def extract_source_summary(source_connection: SourceConnection) -> str:
    """Extract a concise summary of the source connection for display.
    
    Combines connection type and entity name into a single readable string.
    
    Args:
        source_connection: Source connection object
        
    Returns:
        Summary string like "Amazon S3: s3://bucket/path" or connection name as fallback
        
    Examples:
        "Amazon S3: s3://customer-data/exports"
        "Salesforce Object: Account"
        "MySQL: analytics.user_events"
    """
    # Get entity name
    entity = extract_source_entity(source_connection)
    
    # Get source type
    source_type = None
    if source_connection.connection_spec:
        source_type = source_connection.connection_spec.name
        if not source_type and source_connection.connection_spec.id:
            source_type = get_source_type_from_spec(source_connection.connection_spec.id)
    
    # Build summary
    if entity and source_type:
        return f"{source_type}: {entity}"
    elif entity:
        return entity
    elif source_type:
        return source_type
    
    # Fallback to connection name
    return source_connection.name or "Unknown source"
