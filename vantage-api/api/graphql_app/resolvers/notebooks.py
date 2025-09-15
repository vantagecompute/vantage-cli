"""Core module for defining GraphQL resolvers for jupyter notebooks management."""
from typing import Optional, Union

import httpx
from httpx import RequestError
from loguru import logger
from sqlalchemy import delete, insert, select
from sqlalchemy.sql.expression import Delete, Insert, Select

from api.graphql_app.helpers import build_connection
from api.graphql_app.types import (
    Cluster,
    ClusterNotFound,
    Connection,
    CreateNotebookInput,
    Info,
    JSONScalar,
    JupyterHubStatus,
    NotebookServer,
    NotebookServerAlreadyExists,
    NotebookServerDeleted,
    NotebookServerNotFound,
    NotebookServerOrderingInput,
    NotebookServerProgress,
    Partition,
    PartitionNotFound,
)
from api.settings import SETTINGS
from api.sql_app import models


async def get_notebook_server(
    info: Info,
    first: int = 10,
    after: int = 1,
    filters: Optional[JSONScalar] = None,
    subfilters: Optional[JSONScalar] = None,
    ordering: Optional[NotebookServerOrderingInput] = None,
) -> Connection[NotebookServer]:
    """Get all notebooks."""
    return await build_connection(
        info=info,
        first=first,
        model=models.NotebookServerModel,
        scalar_type=NotebookServer,
        after=after,
        filters=filters,
        subfilters=subfilters,
        ordering=ordering,
        model_relations=[models.NotebookServerModel.cluster],
    )


async def get_jupyterhub_status(info: Info, client_id: str) -> JupyterHubStatus:
    """Check the JupyterHub status."""
    available = False
    if SETTINGS.STAGE == "production":
        jupyter_url = f"https://{client_id}.{SETTINGS.APP_DOMAIN}"
    else:
        jupyter_url = f"https://{client_id}.{SETTINGS.STAGE}.{SETTINGS.APP_DOMAIN}"

    try:
        response = httpx.get(f"{jupyter_url}/hub/api/", timeout=5.0)
        if response.status_code == 200:
            available = True
    except RequestError:
        available = False

    return JupyterHubStatus(available=available)


async def check_progress(
    info: Info, notebook_server_name: str
) -> Union[
    NotebookServerNotFound,
    NotebookServerProgress,
]:
    """Check if a notebook server is ready."""
    query: Select | Delete
    async with info.context.db_session(info.context.token_data.organization) as sess:
        query: Select = (
            select(
                models.NotebookServerModel,
                models.ClusterModel.creation_parameters,
            )
            .join(models.ClusterModel, models.NotebookServerModel.cluster_name == models.ClusterModel.name)
            .where(models.NotebookServerModel.name == notebook_server_name)
        )
        row = (await sess.execute(query)).one_or_none()
        if row is None:
            return NotebookServerNotFound(message=(f"Notebook Server {notebook_server_name} not found."))
        notebook_server_row, creation_parameters = row

        jupyterhub_token = creation_parameters.get("jupyterhub_token")

        headers = {
            "Authorization": f"token {jupyterhub_token}",
            "Content-Type": "application/json",
        }

        try:
            response = httpx.get(f"{notebook_server_row.server_url}/hub/api/users/ubuntu", headers=headers)
            logger.debug(f"Get notebook progress response: {response}")
            servers = response.json().get("servers")
            server_status = servers.get(f"{notebook_server_name}", {"ready": False})
        except Exception as err:
            logger.error(f"Error trying to get notebook server info: {err}")
            server_status = {"ready": False}

    return NotebookServerProgress(ready=server_status.get("ready"))


async def create_notebook(
    info: Info, create_notebook_input: CreateNotebookInput
) -> Union[ClusterNotFound, NotebookServerAlreadyExists, PartitionNotFound, NotebookServer]:
    """Create a notebook server resolver."""
    organization_id = info.context.token_data.organization
    owner_email = info.context.token_data.email

    async with info.context.db_session(organization_id) as sess:
        # validate the notebook
        query = select(models.NotebookServerModel).where(
            models.NotebookServerModel.name == create_notebook_input.name,
        )
        notebook_server: NotebookServer | None = (await sess.execute(query)).scalar_one_or_none()

        if notebook_server is not None:
            return NotebookServerAlreadyExists()

        # validate cluster
        query = select(models.ClusterModel).where(
            models.ClusterModel.name == create_notebook_input.cluster_name,
        )
        cluster: Cluster | None = (await sess.execute(query)).scalar_one_or_none()

        if cluster is None:
            return ClusterNotFound()

        # validate partition
        query = select(models.PartitionModel).where(
            models.PartitionModel.name == create_notebook_input.partition_name,
            models.PartitionModel.cluster_name == create_notebook_input.cluster_name,
        )
        partition: Partition | None = (await sess.execute(query)).scalar_one_or_none()

        if partition is None:
            return PartitionNotFound()

        # retrieve secret from keycloak
        jupyterhub_token = cluster.creation_parameters.get("jupyterhub_token")

        if SETTINGS.STAGE == "production":
            jupyter_url = f"https://{cluster.client_id}.{SETTINGS.APP_DOMAIN}"
        else:
            jupyter_url = f"https://{cluster.client_id}.{SETTINGS.STAGE}.{SETTINGS.APP_DOMAIN}"

        headers = {
            "Authorization": f"token {jupyterhub_token}",
            "Content-Type": "application/json",
        }
        request_payload = {
            "name": "ubuntu",
            "server_name": create_notebook_input.name,
            "partition": create_notebook_input.partition_name,
        }
        if create_notebook_input.memory is not None:
            request_payload[
                "memory"
            ] = f"{int(create_notebook_input.memory)}{create_notebook_input.memory_unit.value}"  # noqa

        if create_notebook_input.cpu_cores is not None:
            request_payload["nprocs"] = f"{create_notebook_input.cpu_cores}"

        if create_notebook_input.gpus is not None and int(create_notebook_input.gpus) > 0:
            request_payload["gres"] = f"gpu:{int(create_notebook_input.gpus)}"

        api_url = f"{jupyter_url}/hub/api/users/ubuntu/servers/{create_notebook_input.name}"

        logger.debug(f"Creating Notebook with the following specs: {request_payload}")
        create_notebook_response = httpx.post(
            api_url, headers=headers, json=request_payload, timeout=httpx.Timeout(20)
        )
        logger.debug(f"Create Notebook Server - Jupyter API Response: {create_notebook_response}")

        ubuntu_user_response = httpx.get(
            f"{jupyter_url}/hub/api/users/ubuntu", headers=headers, timeout=httpx.Timeout(20)
        )
        logger.debug(f"Ubuntu User - Jupyter API Response: {ubuntu_user_response}")

        slurm_job_id = int(
            ubuntu_user_response.json()
            .get("servers")
            .get(create_notebook_input.name)
            .get("state")
            .get("job_id")
        )

        server_payload = {
            "name": create_notebook_input.name,
            "owner": owner_email,
            "partition": create_notebook_input.partition_name,
            "cluster_name": create_notebook_input.cluster_name,
            "server_url": jupyter_url,
            "slurm_job_id": slurm_job_id,
        }

        # register notebook
        insert_query: Insert = (
            insert(models.NotebookServerModel).values(**server_payload).returning(models.NotebookServerModel)
        )

        notebook_server = (await sess.execute(insert_query)).one()
        await sess.commit()

    return NotebookServer(**notebook_server, cluster=cluster)


async def delete_notebook_server(
    info: Info, notebook_server_name: str
) -> Union[NotebookServerNotFound, NotebookServerDeleted]:
    """Delete a notebook server."""
    query: Select | Delete
    async with info.context.db_session(info.context.token_data.organization) as sess:
        query: Select = (
            select(
                models.NotebookServerModel,
                models.ClusterModel.creation_parameters,
            )
            .join(models.ClusterModel, models.NotebookServerModel.cluster_name == models.ClusterModel.name)
            .where(models.NotebookServerModel.name == notebook_server_name)
        )
        row = (await sess.execute(query)).one_or_none()

        if row is None or not (
            row[0].owner == info.context.token_data.email
            or "notebook:admin" in info.context.token_data.permissions
        ):
            return NotebookServerNotFound(message=(f"Notebook Server {notebook_server_name} not found."))

        notebook_server_row, creation_parameters = row

        jupyterhub_token = creation_parameters.get("jupyterhub_token")

        headers = {
            "Authorization": f"token {jupyterhub_token}",
            "Content-Type": "application/json",
        }

        # delete from jupyterhub
        response = httpx.delete(
            f"{notebook_server_row.server_url}/hub/api/users/ubuntu/servers/{notebook_server_name}",  # noqa
            headers=headers,
        )

        logger.debug(f"Delete notebook server response with status {response.status_code}.")  # noqa

        query: Delete = delete(models.NotebookServerModel).where(
            models.NotebookServerModel.name == notebook_server_name
        )
        await sess.execute(query)
        await sess.commit()

    return NotebookServerDeleted()
