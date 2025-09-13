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
import pytest
from pydantic import ValidationError

from vantage_cli.commands.cluster import schema as cluster_schema


def test_vantage_cluster_context_creation():
    ctx = cluster_schema.VantageClusterContext(
        client_id="cid",
        client_secret="secret",
        oidc_domain="auth.example.com",
        oidc_base_url="https://auth.example.com/realms/vantage",
        base_api_url="https://api.example.com",
        tunnel_api_url="https://tunnel.example.com",
        jupyterhub_token="tok",
    )
    assert ctx.client_id == "cid"
    assert ctx.client_secret == "secret"
    assert ctx.jupyterhub_token == "tok"


def test_cluster_detail_schema_optional_fields_and_defaults():
    data = {
        "name": "cluster-a",
        "status": "RUNNING",
        "client_id": "cid",
        "description": "Test cluster",
        "owner_mail": "user@example.com",
        "provider": "localhost",
        "creation_parameters": {"cloud": "localhost"},
    }
    obj = cluster_schema.ClusterDetailSchema(**data)
    assert obj.name == "cluster-a"
    assert obj.client_secret is None  # Optional
    assert obj.cloud_account_id is None  # Optional
    assert obj.creation_parameters["cloud"] == "localhost"


def test_cluster_detail_schema_validation_error():
    # Missing required field 'name'
    data = {
        "status": "RUNNING",
        "client_id": "cid",
        "description": "Test cluster",
        "owner_mail": "user@example.com",
        "provider": "localhost",
        "creation_parameters": {},
    }
    with pytest.raises(ValidationError):
        cluster_schema.ClusterDetailSchema(**data)
