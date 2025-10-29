# Copyright (C) 2025 Vantage Compute Corporation
# This program is free software: you can redistribute it and/or modify it under
# the terms of the GNU General Public License as published by the Free Software
# Foundation, version 3.
#
# This program is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along with
# this program. If not, see <https://www.gnu.org/licenses/>.
"""JupyterHub REST API Client for notebook server management."""

import logging
from typing import Any, Dict, Optional

import httpx

from vantage_cli.exceptions import Abort

logger = logging.getLogger(__name__)


class JupyterHubClient:
    """Client for interacting with JupyterHub REST API."""

    def __init__(self, hub_url: str, api_token: str):
        """Initialize JupyterHub client.

        Args:
            hub_url: Base URL of the JupyterHub instance (e.g., https://client-id.vantagecompute.ai)
            api_token: JupyterHub API token for authentication
        """
        self.hub_url = hub_url.rstrip("/")
        self.api_token = api_token
        self.api_base = f"{self.hub_url}/hub/api"
        self.client = httpx.AsyncClient(timeout=30.0)

    def _headers(self) -> Dict[str, str]:
        """Get request headers with authentication."""
        return {
            "Authorization": f"token {self.api_token}",
            "Content-Type": "application/json",
        }

    async def create_user_server(
        self,
        username: str,
        server_name: Optional[str] = None,
        options: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Create a new notebook server for a user.

        Args:
            username: JupyterHub username
            server_name: Optional named server (default creates default server)
            options: Optional server configuration options

        Returns:
            Response data from JupyterHub API

        Raises:
            Abort: If server creation fails
        """
        # Construct the endpoint
        if server_name:
            endpoint = f"{self.api_base}/users/{username}/servers/{server_name}"
        else:
            endpoint = f"{self.api_base}/users/{username}/server"

        payload = options or {}

        logger.debug(f"Creating JupyterHub server for user '{username}' at {endpoint}")

        try:
            response = await self.client.post(
                endpoint,
                headers=self._headers(),
                json=payload,
            )

            if response.status_code == 201:
                logger.info(f"Successfully created server for user '{username}'")
                return response.json() if response.text else {"status": "created"}

            if response.status_code == 202:
                # Server is being spawned
                logger.info(f"Server spawn initiated for user '{username}'")
                return {"status": "pending", "message": "Server is being spawned"}

            if response.status_code == 404:
                hint_message = (
                    "JupyterHub returned 404 for the requested server."
                    "\n• Confirm the cluster's JupyterHub endpoint is reachable."
                    "\n• Ensure the named server '"
                    f"{server_name or 'default'}"
                    "' exists or can be created for user '"
                    f"{username}'"
                    "'."
                    "\n• If this is a fresh deployment, verify the JupyterHub chart finished installing."
                )
                error_msg = f"Failed to create server: {response.status_code} - {response.text}\n{hint_message}"
                logger.error(error_msg)
                raise Abort(
                    error_msg,
                    subject="JupyterHub Server Creation Failed",
                    log_message=f"JupyterHub API error: {response.status_code}",
                )

            error_msg = f"Failed to create server: {response.status_code} - {response.text}"
            logger.error(error_msg)
            raise Abort(
                error_msg,
                subject="JupyterHub Server Creation Failed",
                log_message=f"JupyterHub API error: {response.status_code}",
            )

        except httpx.HTTPError as e:
            logger.error(f"HTTP error while creating server: {e}")
            raise Abort(
                f"Failed to connect to JupyterHub: {str(e)}",
                subject="JupyterHub Connection Error",
                log_message=f"HTTPError: {str(e)}",
            )

    async def get_user_server(
        self, username: str, server_name: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """Get information about a user's notebook server.

        Args:
            username: JupyterHub username
            server_name: Optional named server

        Returns:
            Server information or None if not found
        """
        endpoint = f"{self.api_base}/users/{username}"

        try:
            response = await self.client.get(endpoint, headers=self._headers())

            if response.status_code == 200:
                user_data = response.json()
                servers = user_data.get("servers", {})

                if server_name:
                    return servers.get(server_name)
                else:
                    # Return default server (empty string key)
                    return servers.get("")

            return None

        except httpx.HTTPError as e:
            logger.error(f"HTTP error while getting server info: {e}")
            return None

    async def stop_user_server(self, username: str, server_name: Optional[str] = None) -> bool:
        """Stop a user's notebook server.

        Args:
            username: JupyterHub username
            server_name: Optional named server

        Returns:
            True if successful, False otherwise
        """
        if server_name:
            endpoint = f"{self.api_base}/users/{username}/servers/{server_name}"
        else:
            endpoint = f"{self.api_base}/users/{username}/server"

        try:
            response = await self.client.delete(endpoint, headers=self._headers())

            if response.status_code in [202, 204]:
                logger.info(f"Successfully stopped server for user '{username}'")
                return True
            else:
                logger.error(f"Failed to stop server: {response.status_code}")
                return False

        except httpx.HTTPError as e:
            logger.error(f"HTTP error while stopping server: {e}")
            return False

    async def list_users(self) -> list[Dict[str, Any]]:
        """List all users in JupyterHub.

        Returns:
            List of user data dictionaries
        """
        endpoint = f"{self.api_base}/users"

        try:
            response = await self.client.get(endpoint, headers=self._headers())

            if response.status_code == 200:
                return response.json()
            else:
                logger.error(f"Failed to list users: {response.status_code}")
                return []

        except httpx.HTTPError as e:
            logger.error(f"HTTP error while listing users: {e}")
            return []

    async def close(self):
        """Close the HTTP client."""
        await self.client.aclose()
