"""Tests for the queue actions GraphQL API."""
from collections.abc import Callable
from typing import AsyncContextManager

import pytest
from sqlalchemy import insert, select
from sqlalchemy.ext.asyncio import AsyncSession

from api.graphql_app import schema
from api.graphql_app.types import Context
from api.sql_app.enums import ClusterQueueActionEnum
from api.sql_app.models import ClusterQueueActionsModel, QueueModel
from tests.conftest import SeededData


class TestClusterQueueActionsQuery:
    """Test all logic related to cluster queue actions query."""

    @pytest.mark.asyncio
    async def test_query_cluster_queue_actions__empty_result(
        self,
        enforce_strawberry_context_authentication: None,
    ):
        """Test the cluster queue actions query when no actions exist."""
        context = Context()

        query = """
        query clusterQueueActions {
            clusterQueueActions {
                edges {
                    node {
                        id
                        clusterName
                        queueId
                        action
                    }
                }
                total
            }
        }
        """

        resp = await schema.execute(query, context_value=context)

        assert resp.errors is None
        assert resp.data["clusterQueueActions"]["edges"] == []
        assert resp.data["clusterQueueActions"]["total"] == 0

    @pytest.mark.asyncio
    async def test_query_cluster_queue_actions__with_data(
        self,
        seed_database: SeededData,
        get_session: Callable[[], AsyncContextManager[AsyncSession]],
        enforce_strawberry_context_authentication: None,
        clean_up_database: None,
    ):
        """Test the cluster queue actions query with existing data."""
        context = Context()

        # First, create a queue for the seeded cluster
        async with get_session() as sess:
            queue_data = {
                "cluster_name": seed_database.cluster.name,
                "name": "test_queue",
                "info": {"partition": "compute", "state": "RUNNING"},
            }
            queue_query = insert(QueueModel).values(queue_data).returning(QueueModel.id)
            queue_id = (await sess.execute(queue_query)).scalar()

            # Create a queue action
            action_data = {
                "cluster_name": seed_database.cluster.name,
                "queue_id": queue_id,
                "action": ClusterQueueActionEnum.cancel,
            }
            action_query = (
                insert(ClusterQueueActionsModel).values(action_data).returning(ClusterQueueActionsModel.id)
            )
            action_id = (await sess.execute(action_query)).scalar()
            await sess.commit()

        query = """
        query clusterQueueActions {
            clusterQueueActions {
                edges {
                    node {
                        id
                        clusterName
                        queueId
                        action
                        queue {
                            id
                            name
                            info
                        }
                        cluster {
                            name
                            clientId
                        }
                    }
                }
                total
            }
        }
        """

        resp = await schema.execute(query, context_value=context)

        assert resp.errors is None
        assert len(resp.data["clusterQueueActions"]["edges"]) == 1
        assert resp.data["clusterQueueActions"]["total"] == 1

        action_node = resp.data["clusterQueueActions"]["edges"][0]["node"]
        assert action_node["id"] == action_id
        assert action_node["clusterName"] == seed_database.cluster.name
        assert action_node["queueId"] == queue_id
        assert action_node["action"] == "cancel"
        assert action_node["queue"]["name"] == "test_queue"
        assert action_node["cluster"]["name"] == seed_database.cluster.name


class TestAddQueueActionMutation:
    """Test all logic related to add queue action mutation."""

    @pytest.mark.asyncio
    async def test_add_queue_action__success(
        self,
        seed_database: SeededData,
        get_session: Callable[[], AsyncContextManager[AsyncSession]],
        enforce_strawberry_context_authentication: None,
        clean_up_database: None,
    ):
        """Test successful addition of a queue action."""
        context = Context()

        # First, create a queue for the seeded cluster
        async with get_session() as sess:
            queue_data = {
                "cluster_name": seed_database.cluster.name,
                "name": "test_queue",
                "info": {"partition": "compute", "state": "RUNNING"},
            }
            queue_query = insert(QueueModel).values(queue_data).returning(QueueModel.id)
            queue_id = (await sess.execute(queue_query)).scalar()
            await sess.commit()

        query = """
        mutation addQueueAction($input: ClusterQueueActionsInput!) {
            addQueueAction(input: $input) {
                __typename
                ... on ClusterQueueActions {
                    id
                    clusterName
                    queueId
                    action
                }
                ... on InvalidInput {
                    message
                }
            }
        }
        """

        variables = {
            "input": {
                "clusterName": seed_database.cluster.name,
                "queueId": queue_id,
                "action": "cancel",
            }
        }

        resp = await schema.execute(query, variable_values=variables, context_value=context)

        assert resp.errors is None
        assert resp.data["addQueueAction"]["__typename"] == "ClusterQueueActions"
        assert resp.data["addQueueAction"]["clusterName"] == seed_database.cluster.name
        assert resp.data["addQueueAction"]["queueId"] == queue_id
        assert resp.data["addQueueAction"]["action"] == "cancel"

        # Verify the action was created in the database
        async with get_session() as sess:
            action_query = select(ClusterQueueActionsModel).where(
                ClusterQueueActionsModel.cluster_name == seed_database.cluster.name,
                ClusterQueueActionsModel.queue_id == queue_id,
            )
            action = (await sess.execute(action_query)).scalar_one_or_none()
            assert action is not None
            assert action.action == ClusterQueueActionEnum.cancel

    @pytest.mark.asyncio
    async def test_add_queue_action__queue_not_found(
        self,
        seed_database: SeededData,
        enforce_strawberry_context_authentication: None,
        clean_up_database: None,
    ):
        """Test add queue action when the queue doesn't exist."""
        context = Context()

        query = """
        mutation addQueueAction($input: ClusterQueueActionsInput!) {
            addQueueAction(input: $input) {
                __typename
                ... on InvalidInput {
                    message
                }
                ... on ClusterQueueActions {
                    id
                }
            }
        }
        """

        variables = {
            "input": {
                "clusterName": seed_database.cluster.name,
                "queueId": 99999,  # Non-existent queue ID
                "action": "cancel",
            }
        }

        resp = await schema.execute(query, variable_values=variables, context_value=context)

        assert resp.errors is None
        assert resp.data["addQueueAction"]["__typename"] == "InvalidInput"
        assert resp.data["addQueueAction"]["message"] == "Queue not found"

    @pytest.mark.asyncio
    async def test_add_queue_action__action_already_exists(
        self,
        seed_database: SeededData,
        get_session: Callable[[], AsyncContextManager[AsyncSession]],
        enforce_strawberry_context_authentication: None,
        clean_up_database: None,
    ):
        """Test add queue action when the action already exists for the cluster and queue."""
        context = Context()

        # First, create a queue and an existing action
        async with get_session() as sess:
            queue_data = {
                "cluster_name": seed_database.cluster.name,
                "name": "test_queue",
                "info": {"partition": "compute", "state": "RUNNING"},
            }
            queue_query = insert(QueueModel).values(queue_data).returning(QueueModel.id)
            queue_id = (await sess.execute(queue_query)).scalar()

            # Create an existing action
            action_data = {
                "cluster_name": seed_database.cluster.name,
                "queue_id": queue_id,
                "action": ClusterQueueActionEnum.cancel,
            }
            action_query = insert(ClusterQueueActionsModel).values(action_data)
            await sess.execute(action_query)
            await sess.commit()

        query = """
        mutation addQueueAction($input: ClusterQueueActionsInput!) {
            addQueueAction(input: $input) {
                __typename
                ... on InvalidInput {
                    message
                }
                ... on ClusterQueueActions {
                    id
                }
            }
        }
        """

        variables = {
            "input": {
                "clusterName": seed_database.cluster.name,
                "queueId": queue_id,
                "action": "cancel",
            }
        }

        resp = await schema.execute(query, variable_values=variables, context_value=context)

        assert resp.errors is None
        assert resp.data["addQueueAction"]["__typename"] == "InvalidInput"
        assert resp.data["addQueueAction"]["message"] == "Action already exists for this cluster and queue"


class TestRemoveQueueActionMutation:
    """Test all logic related to remove queue action mutation."""

    @pytest.mark.asyncio
    async def test_remove_queue_action__success(
        self,
        seed_database: SeededData,
        get_session: Callable[[], AsyncContextManager[AsyncSession]],
        enforce_strawberry_context_authentication: None,
        clean_up_database: None,
    ):
        """Test successful removal of a queue action."""
        context = Context()

        # First, create a queue and an action to remove
        async with get_session() as sess:
            queue_data = {
                "cluster_name": seed_database.cluster.name,
                "name": "test_queue",
                "info": {"partition": "compute", "state": "RUNNING"},
            }
            queue_query = insert(QueueModel).values(queue_data).returning(QueueModel.id)
            queue_id = (await sess.execute(queue_query)).scalar()

            # Create an action to remove
            action_data = {
                "cluster_name": seed_database.cluster.name,
                "queue_id": queue_id,
                "action": ClusterQueueActionEnum.cancel,
            }
            action_query = (
                insert(ClusterQueueActionsModel).values(action_data).returning(ClusterQueueActionsModel.id)
            )
            action_id = (await sess.execute(action_query)).scalar()
            await sess.commit()

        query = """
        mutation removeQueueAction($id: Int!) {
            removeQueueAction(id: $id) {
                __typename
                ... on RemoveQueueActionSuccess {
                    message
                }
                ... on InvalidInput {
                    message
                }
            }
        }
        """

        variables = {"id": action_id}

        resp = await schema.execute(query, variable_values=variables, context_value=context)

        assert resp.errors is None
        assert resp.data["removeQueueAction"]["__typename"] == "RemoveQueueActionSuccess"
        assert resp.data["removeQueueAction"]["message"] == "Queue action removed successfully"

        # Verify the action was removed from the database
        async with get_session() as sess:
            action_query = select(ClusterQueueActionsModel).where(ClusterQueueActionsModel.id == action_id)
            action = (await sess.execute(action_query)).scalar_one_or_none()
            assert action is None

    @pytest.mark.asyncio
    async def test_remove_queue_action__action_not_found(
        self,
        enforce_strawberry_context_authentication: None,
    ):
        """Test remove queue action when the action doesn't exist."""
        context = Context()

        query = """
        mutation removeQueueAction($id: Int!) {
            removeQueueAction(id: $id) {
                __typename
                ... on InvalidInput {
                    message
                }
                ... on RemoveQueueActionSuccess {
                    message
                }
            }
        }
        """

        variables = {"id": 99999}  # Non-existent action ID

        resp = await schema.execute(query, variable_values=variables, context_value=context)

        assert resp.errors is None
        assert resp.data["removeQueueAction"]["__typename"] == "InvalidInput"
        assert resp.data["removeQueueAction"]["message"] == "Queue action not found"

    @pytest.mark.asyncio
    async def test_remove_queue_action__multiple_actions_removal(
        self,
        seed_database: SeededData,
        get_session: Callable[[], AsyncContextManager[AsyncSession]],
        enforce_strawberry_context_authentication: None,
        clean_up_database: None,
    ):
        """Test that removing one action doesn't affect others."""
        context = Context()

        # Create multiple queues and actions
        async with get_session() as sess:
            queue1_data = {
                "cluster_name": seed_database.cluster.name,
                "name": "test_queue_1",
                "info": {"partition": "compute", "state": "RUNNING"},
            }
            queue1_query = insert(QueueModel).values(queue1_data).returning(QueueModel.id)
            queue1_id = (await sess.execute(queue1_query)).scalar()

            queue2_data = {
                "cluster_name": seed_database.cluster.name,
                "name": "test_queue_2",
                "info": {"partition": "gpu", "state": "RUNNING"},
            }
            queue2_query = insert(QueueModel).values(queue2_data).returning(QueueModel.id)
            queue2_id = (await sess.execute(queue2_query)).scalar()

            # Create two actions
            action1_data = {
                "cluster_name": seed_database.cluster.name,
                "queue_id": queue1_id,
                "action": ClusterQueueActionEnum.cancel,
            }
            action1_query = (
                insert(ClusterQueueActionsModel).values(action1_data).returning(ClusterQueueActionsModel.id)
            )
            action1_id = (await sess.execute(action1_query)).scalar()

            action2_data = {
                "cluster_name": seed_database.cluster.name,
                "queue_id": queue2_id,
                "action": ClusterQueueActionEnum.cancel,
            }
            action2_query = (
                insert(ClusterQueueActionsModel).values(action2_data).returning(ClusterQueueActionsModel.id)
            )
            action2_id = (await sess.execute(action2_query)).scalar()
            await sess.commit()

        query = """
        mutation removeQueueAction($id: Int!) {
            removeQueueAction(id: $id) {
                __typename
                ... on RemoveQueueActionSuccess {
                    message
                }
            }
        }
        """

        # Remove the first action
        variables = {"id": action1_id}
        resp = await schema.execute(query, variable_values=variables, context_value=context)

        assert resp.errors is None
        assert resp.data["removeQueueAction"]["__typename"] == "RemoveQueueActionSuccess"

        # Verify only the first action was removed
        async with get_session() as sess:
            # First action should be gone
            action1_query = select(ClusterQueueActionsModel).where(ClusterQueueActionsModel.id == action1_id)
            action1 = (await sess.execute(action1_query)).scalar_one_or_none()
            assert action1 is None

            # Second action should still exist
            action2_query = select(ClusterQueueActionsModel).where(ClusterQueueActionsModel.id == action2_id)
            action2 = (await sess.execute(action2_query)).scalar_one_or_none()
            assert action2 is not None
            assert action2.queue_id == queue2_id


class TestQueueActionsIntegration:
    """Integration tests for queue actions functionality."""

    @pytest.mark.asyncio
    async def test_full_queue_action_workflow(
        self,
        seed_database: SeededData,
        get_session: Callable[[], AsyncContextManager[AsyncSession]],
        enforce_strawberry_context_authentication: None,
        clean_up_database: None,
    ):
        """Test the complete workflow: query empty, add action, query with data, remove action, query empty again."""  # noqa: E501
        context = Context()

        # First, create a queue for the seeded cluster
        async with get_session() as sess:
            queue_data = {
                "cluster_name": seed_database.cluster.name,
                "name": "workflow_queue",
                "info": {"partition": "compute", "state": "RUNNING"},
            }
            queue_query = insert(QueueModel).values(queue_data).returning(QueueModel.id)
            queue_id = (await sess.execute(queue_query)).scalar()
            await sess.commit()

        # Step 1: Query empty actions
        query_actions = """
        query clusterQueueActions {
            clusterQueueActions {
                total
                edges {
                    node {
                        id
                    }
                }
            }
        }
        """

        resp = await schema.execute(query_actions, context_value=context)
        assert resp.errors is None
        assert resp.data["clusterQueueActions"]["total"] == 0

        # Step 2: Add an action
        add_mutation = """
        mutation addQueueAction($input: ClusterQueueActionsInput!) {
            addQueueAction(input: $input) {
                __typename
                ... on ClusterQueueActions {
                    id
                    clusterName
                    queueId
                    action
                }
            }
        }
        """

        add_variables = {
            "input": {
                "clusterName": seed_database.cluster.name,
                "queueId": queue_id,
                "action": "cancel",
            }
        }

        resp = await schema.execute(add_mutation, variable_values=add_variables, context_value=context)
        assert resp.errors is None
        assert resp.data["addQueueAction"]["__typename"] == "ClusterQueueActions"
        action_id = int(resp.data["addQueueAction"]["id"])

        # Step 3: Query with data
        resp = await schema.execute(query_actions, context_value=context)
        assert resp.errors is None
        assert resp.data["clusterQueueActions"]["total"] == 1
        assert int(resp.data["clusterQueueActions"]["edges"][0]["node"]["id"]) == action_id

        # Step 4: Remove the action
        remove_mutation = """
        mutation removeQueueAction($id: Int!) {
            removeQueueAction(id: $id) {
                __typename
                ... on RemoveQueueActionSuccess {
                    message
                }
            }
        }
        """

        remove_variables = {"id": action_id}
        resp = await schema.execute(remove_mutation, variable_values=remove_variables, context_value=context)
        assert resp.errors is None
        assert resp.data["removeQueueAction"]["__typename"] == "RemoveQueueActionSuccess"

        # Step 5: Query empty again
        resp = await schema.execute(query_actions, context_value=context)
        assert resp.errors is None
        assert resp.data["clusterQueueActions"]["total"] == 0
