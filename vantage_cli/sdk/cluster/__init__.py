"""Cluster CRUD operations."""

from typing import Any, Dict, List, Optional
import typer
from loguru import logger

from vantage_cli.exceptions import Abort
from vantage_cli.gql_client import create_async_graphql_client


async def list(ctx: typer.Context) -> List[Dict[str, Any]]:
    """List all Vantage clusters.
    
    Returns:
        List of cluster dictionaries
    """
    logger.debug(f"list() called with ctx: {ctx}")
    logger.debug(f"ctx.obj: {ctx.obj}")
    logger.debug(f"ctx.obj type: {type(ctx.obj)}")
    
    if hasattr(ctx.obj, 'settings'):
        logger.debug(f"ctx.obj.settings: {ctx.obj.settings}")
    else:
        logger.error("ctx.obj.settings not found!")
        
    if hasattr(ctx.obj, 'profile'):
        logger.debug(f"ctx.obj.profile: {ctx.obj.profile}")
    else:
        logger.error("ctx.obj.profile not found!")
    
    # GraphQL query to fetch clusters
    query = """
    query getClusters($first: Int!) {
        clusters(first: $first) {
            edges {
                node {
                    name
                    status
                    clientId
                    description
                    ownerEmail
                    provider
                    cloudAccountId
                    creationParameters
                }
            }
        }
    }
    """

    variables = {"first": 100}  # Fetch up to 100 clusters

    try:
        # Create async GraphQL client
        profile = getattr(ctx.obj, "profile", "default")
        logger.debug(f"Using profile: {profile}")
        
        graphql_client = create_async_graphql_client(ctx.obj.settings, profile)
        logger.debug(f"GraphQL client created: {graphql_client}")

        # Execute the query
        logger.debug("Executing clusters query")
        response_data = await graphql_client.execute_async(query, variables)
        logger.debug(f"GraphQL response: {response_data}")

        # Extract cluster data
        clusters_data = response_data.get("clusters", {})
        clusters = [edge["node"] for edge in clusters_data.get("edges", [])]
        
        logger.debug(f"Returning {len(clusters)} clusters")
        return clusters

    except Exception as e:
        logger.error(f"Error listing clusters: {e}")
        logger.exception("Full traceback:")
        raise Abort(
            "Failed to fetch clusters from Vantage API.",
            subject="API Error",
            log_message=f"Clusters list error: {e}",
        )


async def get(ctx: typer.Context, cluster_name: str) -> Optional[Dict[str, Any]]:
    """Get details of a specific cluster by name.
    
    Args:
        ctx: Typer context
        cluster_name: Name of the cluster to retrieve
        
    Returns:
        Cluster dictionary if found, None if not found
    """
    try:
        # Get all clusters using the list function and filter
        logger.debug(f"Getting cluster '{cluster_name}' using list and filter approach")
        clusters = await list(ctx)
        
        # Filter clusters by name (case-insensitive)
        matching_clusters = [
            cluster
            for cluster in clusters
            if cluster.get("name", "").lower() == cluster_name.lower()
        ]

        if not matching_clusters:
            logger.debug(f"No cluster found with name '{cluster_name}'")
            return None

        # Return the first (and should be only) cluster
        cluster = matching_clusters[0]
        logger.debug(f"Found cluster: {cluster}")
        return cluster

    except Exception as e:
        logger.error(f"Error fetching cluster {cluster_name}: {e}")
        raise Abort(
            f"Failed to fetch cluster '{cluster_name}' from Vantage API.",
            subject="API Error", 
            log_message=f"Cluster get error: {e}",
        )