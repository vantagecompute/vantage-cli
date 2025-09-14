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
"""Tests for the Juju localhost bundle YAML configuration."""

import copy

from vantage_cli.apps.slurm_juju_localhost.bundle_yaml import VANTAGE_JUPYTERHUB_YAML


class TestVantageJupyterhubYaml:
    """Test the VANTAGE_JUPYTERHUB_YAML bundle configuration."""

    def test_bundle_structure(self):
        """Test that the bundle has the expected top-level structure."""
        assert "applications" in VANTAGE_JUPYTERHUB_YAML
        assert "machines" in VANTAGE_JUPYTERHUB_YAML
        assert "relations" in VANTAGE_JUPYTERHUB_YAML

    def test_required_applications_present(self):
        """Test that all required applications are present in the bundle."""
        applications = VANTAGE_JUPYTERHUB_YAML["applications"]
        required_apps = [
            "jobbergate-agent",
            "vantage-agent",
            "vantage-jupyterhub-nfs-client",
            "mysql",
            "influxdb",
            "slurmdbd",
            "vantage-jupyterhub",
            "sackd",
            "slurmctld",
            "slurmd",
        ]

        for app in required_apps:
            assert app in applications, f"Required application '{app}' not found in bundle"

    def test_jobbergate_agent_configuration(self):
        """Test jobbergate-agent application configuration."""
        app = VANTAGE_JUPYTERHUB_YAML["applications"]["jobbergate-agent"]

        assert app["charm"] == "jobbergate-agent"
        assert app["base"] == "ubuntu@24.04/stable"
        assert app["channel"] == "edge"
        assert app["num_units"] == 0

        # Test required configuration options
        options = app["options"]
        required_options = [
            "jobbergate-agent-base-api-url",
            "jobbergate-agent-oidc-domain",
            "jobbergate-agent-oidc-client-id",
            "jobbergate-agent-oidc-client-secret",
        ]

        for option in required_options:
            assert option in options, f"Required option '{option}' not found in jobbergate-agent"
            assert options[option] == "", f"Option '{option}' should be empty string by default"

    def test_vantage_agent_configuration(self):
        """Test vantage-agent application configuration."""
        app = VANTAGE_JUPYTERHUB_YAML["applications"]["vantage-agent"]

        assert app["charm"] == "vantage-agent"
        assert app["base"] == "ubuntu@24.04/stable"
        assert app["channel"] == "edge"
        assert app["num_units"] == 0

        # Test required configuration options
        options = app["options"]
        required_options = [
            "vantage-agent-base-api-url",
            "vantage-agent-oidc-domain",
            "vantage-agent-oidc-client-id",
            "vantage-agent-oidc-client-secret",
            "vantage-agent-cluster-name",
        ]

        for option in required_options:
            assert option in options, f"Required option '{option}' not found in vantage-agent"
            assert options[option] == "", f"Option '{option}' should be empty string by default"

    def test_vantage_jupyterhub_configuration(self):
        """Test vantage-jupyterhub application configuration."""
        app = VANTAGE_JUPYTERHUB_YAML["applications"]["vantage-jupyterhub"]

        assert app["charm"] == "vantage-jupyterhub"
        assert app["base"] == "ubuntu@24.04/stable"
        assert app["channel"] == "edge"
        assert app["num_units"] == 1
        assert app["to"] == ["3"]
        assert app["constraints"] == "arch=amd64 cpu-cores=2 mem=2048 virt-type=virtual-machine"

        # Test configuration options
        options = app["options"]
        assert "vantage-jupyterhub-config-secret-id" in options
        assert options["vantage-jupyterhub-config-secret-id"] == ""

    def test_slurmctld_configuration(self):
        """Test slurmctld application configuration."""
        app = VANTAGE_JUPYTERHUB_YAML["applications"]["slurmctld"]

        assert app["charm"] == "slurmctld"
        assert app["base"] == "ubuntu@24.04/stable"
        assert app["channel"] == "latest/edge"
        assert app["num_units"] == 1
        assert app["to"] == ["4"]
        assert app["constraints"] == "arch=amd64 cpu-cores=2 mem=2048 virt-type=virtual-machine"

        # Test configuration options
        options = app["options"]
        assert options["default-partition"] == "slurmd"
        assert "cluster-name" in options
        assert options["cluster-name"] == ""

    def test_slurmd_configuration(self):
        """Test slurmd application configuration."""
        app = VANTAGE_JUPYTERHUB_YAML["applications"]["slurmd"]

        assert app["charm"] == "slurmd"
        assert app["base"] == "ubuntu@24.04/stable"
        assert app["channel"] == "latest/edge"
        assert app["num_units"] == 1
        assert app["to"] == ["5"]
        assert app["constraints"] == "arch=amd64 cpu-cores=4 mem=8192 virt-type=virtual-machine"

    def test_mysql_configuration(self):
        """Test mysql application configuration."""
        app = VANTAGE_JUPYTERHUB_YAML["applications"]["mysql"]

        assert app["charm"] == "mysql"
        assert app["base"] == "ubuntu@22.04/stable"
        assert app["channel"] == "8.0/stable"
        assert app["num_units"] == 1
        assert app["to"] == ["0"]
        assert app["constraints"] == "arch=amd64"
        assert app["storage"] == {"database": "rootfs,1,1024M"}

    def test_influxdb_configuration(self):
        """Test influxdb application configuration."""
        app = VANTAGE_JUPYTERHUB_YAML["applications"]["influxdb"]

        assert app["charm"] == "influxdb"
        assert app["channel"] == "stable"
        assert app["base"] == "ubuntu@20.04/stable"
        assert app["num_units"] == 1
        assert app["to"] == ["1"]
        assert app["constraints"] == "arch=amd64"

    def test_machines_configuration(self):
        """Test machine definitions."""
        machines = VANTAGE_JUPYTERHUB_YAML["machines"]

        # Test that all required machines are present
        required_machines = ["0", "1", "2", "3", "4", "5"]
        for machine in required_machines:
            assert machine in machines, f"Required machine '{machine}' not found"

        # Test specific machine configurations
        assert machines["0"]["base"] == "ubuntu@22.04/stable"
        assert machines["1"]["base"] == "ubuntu@20.04/stable"
        assert machines["2"]["base"] == "ubuntu@24.04/stable"
        assert machines["3"]["base"] == "ubuntu@24.04/stable"
        assert machines["4"]["base"] == "ubuntu@24.04/stable"
        assert machines["5"]["base"] == "ubuntu@24.04/stable"

        # Test constraints
        assert "arch=amd64" in machines["0"]["constraints"]
        assert "cpu-cores=2 mem=2048 virt-type=virtual-machine" in machines["3"]["constraints"]
        assert "cpu-cores=4 mem=8192 virt-type=virtual-machine" in machines["5"]["constraints"]

    def test_relations_configuration(self):
        """Test that all required relations are present."""
        relations = VANTAGE_JUPYTERHUB_YAML["relations"]

        expected_relations = [
            ["slurmdbd:database", "mysql:database"],
            ["slurmctld:influxdb", "influxdb:query"],
            ["slurmdbd:slurmctld", "slurmctld:slurmdbd"],
            ["slurmd:slurmctld", "slurmctld:slurmd"],
            ["sackd:slurmctld", "slurmctld:login-node"],
            ["vantage-jupyterhub-nfs-client:juju-info", "slurmd:juju-info"],
            ["vantage-jupyterhub:filesystem", "vantage-jupyterhub-nfs-client:filesystem"],
            ["sackd:juju-info", "vantage-agent:juju-info"],
            ["sackd:juju-info", "jobbergate-agent:juju-info"],
        ]

        for relation in expected_relations:
            assert relation in relations, f"Required relation {relation} not found"

    def test_bundle_immutability(self):
        """Test that the bundle can be safely copied and modified."""
        # This test ensures that the bundle can be copied for customization
        # without affecting the original
        original = VANTAGE_JUPYTERHUB_YAML
        copied = copy.deepcopy(original)

        # Modify the copy
        copied["applications"]["slurmctld"]["options"]["cluster-name"] = "test-cluster"
        copied["applications"]["vantage-agent"]["options"]["vantage-agent-cluster-name"] = (
            "test-cluster"
        )

        # Ensure original is unchanged
        assert original["applications"]["slurmctld"]["options"]["cluster-name"] == ""
        assert (
            original["applications"]["vantage-agent"]["options"]["vantage-agent-cluster-name"]
            == ""
        )

        # Ensure copy was modified
        assert copied["applications"]["slurmctld"]["options"]["cluster-name"] == "test-cluster"
        assert (
            copied["applications"]["vantage-agent"]["options"]["vantage-agent-cluster-name"]
            == "test-cluster"
        )

    def test_all_applications_have_required_fields(self):
        """Test that all applications have required fields."""
        applications = VANTAGE_JUPYTERHUB_YAML["applications"]

        for app_name, app_config in applications.items():
            assert "charm" in app_config, f"Application '{app_name}' missing 'charm' field"
            assert "base" in app_config, f"Application '{app_name}' missing 'base' field"
            assert "channel" in app_config, f"Application '{app_name}' missing 'channel' field"
            assert "num_units" in app_config, f"Application '{app_name}' missing 'num_units' field"

    def test_configuration_options_are_strings(self):
        """Test that all configuration options are strings (empty by default)."""
        applications = VANTAGE_JUPYTERHUB_YAML["applications"]

        for app_name, app_config in applications.items():
            if "options" in app_config:
                for option_name, option_value in app_config["options"].items():
                    if option_name.endswith(("-url", "-domain", "-id", "-secret", "-name")):
                        assert isinstance(option_value, str), (
                            f"Option '{option_name}' in '{app_name}' should be a string, got {type(option_value)}"
                        )
