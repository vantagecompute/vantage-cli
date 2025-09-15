=========
Changelog
=========

Tracking of all notable changes to the Vantage API project.

Unreleased
----------

- Switch to linuxproc proctrack type and linux accounting gather type in the slurm.conf file (source commit: `cc7c21e01cbd9be9458cbf517b4e717f81c05988`_).

.. _cc7c21e01cbd9be9458cbf517b4e717f81c05988: https://github.com/omnivector-solutions/vantage-api/commit/cc7c21e01cbd9be9458cbf517b4e717f81c05988

3.0.0 - 2025-08-22
------------------

- Redesign how files are imported to the head node's CFN options  (`PENG-3023`_).
- Bake notebook resources in the head node image  (`PENG-3025`_).
- Add the jupyter notebook to cloud cluster (`PENG-2962`_).
- Modify the cloud cluster stack to create a folder at */nfs/mnt* and give all permissions to the *ubuntu* user.
- Add support for read-only database connections in thte *break_out_slurm_information* function.
- Bump the cloud cluster version to 2.0.2/1 and modify the *slurm.conf* to avoid cgroup error.
- Update the Jobbergate API version to *5.6.0* in the Dockerfile.
- Update the Notifications API version to *1.0.0* in the Dockerfile.
- Add an extension to the GraphQL schema to hide *AttributeError* from the GraphQL response.
- Bump pydantic from 1.10.2 to 1.10.13.
- Change the base image from *python:3.10-slim-buster* to *python:3.10-slim-bookworm*.
- Add a column to the *notebook_servers* table to store the slurm job id of the notebook server  (`PENG-3038`_).
- Fix how the Google IdP payload is built.
- Update the EC2 instance data in the *aws_node_types* table (`PENG-2680`_).
- Implement functionality to track clusters' queue (`PENG-3043`_).
- Provide support for CPU, memory and GPU options in the create notebook mutation  (`PENG-3028`_).
- Fix delete dns records when delete clusters
- Implement GraphQL queries for getting the available VPCs and subnets (`PENG-3062`_).
- Implement mechanism to cancel jobs in the queue (`PENG-3069`_).
- Add *notebook:\** permissions to notebook related GraphQL queries and mutations (`PENG-3080`_).

.. _PENG-3025: https://app.clickup.com/t/18022949/PENG-3025
.. _PENG-2962: https://app.clickup.com/t/18022949/PENG-2962
.. _PENG-3023: https://app.clickup.com/t/18022949/PENG-3023
.. _PENG-3038: https://app.clickup.com/t/18022949/PENG-3038
.. _PENG-2680: https://app.clickup.com/t/18022949/PENG-2680
.. _PENG-3043: https://app.clickup.com/t/18022949/PENG-3043
.. _PENG-3028: https://app.clickup.com/t/18022949/PENG-3028
.. _PENG-3062: https://app.clickup.com/t/18022949/PENG-3062
.. _PENG-3069: https://app.clickup.com/t/18022949/PENG-3069
.. _PENG-3080: https://app.clickup.com/t/18022949/PENG-3080

2.7.0 - 2025-03-13
------------------

- Patch the cloud cluster logic for enabling GPU integration (`PENG-2628`_).
- Updated the jobbergate-api version in the vantage-api Dockerfile.
- Modify the *generate_azure_config* function to comply with the *microsoft* provider instead of *oidc*.
- Modify the cloud cluster stack for installing the agents based on the environment (`PENG-2913`_).
- Enable QA environment as a stage flage in the Cloud Account stack.

.. _PENG-2628: https://app.clickup.com/t/18022949/PENG-2628
.. _PENG-2913: https://app.clickup.com/t/18022949/PENG-2913

2.6.0 - 2025-02-10
------------------

- Patch the settings to make it possible to disable Sentry.
- Fix how the *deleteCluster* mutation identify cloud cluster resources on AWS.
- Fix *UnboundLocalError* when querying the sshKeys query and no key pair is available in the AWS region.
- Fix how the *deleteCluster* mutation identify cloud cluster resources on AWS.
- Updated cloud account stack policies with *ec2:DeleteTags* policy.
- Updated the AMI ids for head and compute nodes.
- Prevent *KeyError* when accessing the *isFreeTrialTermPresent* key in the parsed SNS message (subscription related)
- Updated the cloud account stack policy.
- Sort alphabetically the actions of the statement in the cloud account policy.
- Patch the *_delete_aws_cluster_async* function to pass the cleaned cluster name as argument to the *destroy_stack* function.
- Update the cloud cluster creation to configure the cluster name as is in the API while configuring the Vantage Agent snap.
- Fix geting the wrong stack_id in searching stacks for cloud clusters.
- Modify the alembic revision efb840bd688d to get the current database name from the inspector.
- Remove setting the config *task-self-update-interval-seconds* from both agents in the cloud cluster stack.
- Update the cloud cluster to set up Slurm's job metrics collection and store in InfluxDB (`PENG-2467`_).
- Fix the [Slow DB Query](https://omnivector.sentry.io/issues/6094208801/events/a2f56660d2394548b31c92bde7cbd98c/?project=4506588298608640&statsPeriod=14d) problem.
- Adjust the default values of the sample rates for Sentry (`PENG-2592`_).
- Create an index for the *client_id* column in the *cluster* table.
- Modify code for handling the error *NoResultFound* instead of *IntegrityError* when inserting Slurm's data; consequently, solve the error `VANTAGE-API-4T`_.
- Add an exception handler for the *IntegrityError* error in the *reportAgentHealth* mutation.
- Patch the cloud cluster for enabling the configless mode.
- Migrate Vantage domain to vantagecompute.ai (`PENG-2461`_).

.. _PENG-2592: https://app.clickup.com/t/18022949/PENG-2592
.. _PENG-2461: https://app.clickup.com/t/18022949/PENG-2461
.. _VANTAGE-API-4T: https://omnivector.sentry.io/issues/6099808382

2.5.20 - 2025-01-13
-------------------

- Modify the head node user data by adding the `is-cloud-cluster` config in the Vantage Agent snap.

.. _PENG-2467: https://app.clickup.com/t/18022949/PENG-2467

2.5.0 - 2024-11-13
------------------

- Update the cloud cluster stack to install the agents from the Snap Store in *classic* mode.
- Update the Vantage integration policy for cloud accounts (`PENG-2448`_)
- Update the *update_organization* endpoint to allow setting the organization domain (`PENG-2451`_).
- Update the *aws_node_types* table so the columns *gpu_manufacturer* and *gpu_name* have *NULL* instead of *NaN* (`PENG-2444`_).
- Add a setting parameter to configure Armasec's logging (`PENG-2443`_).
- Update vantage api to support cloud cluster with multiple partitions (`PENG-2344`_).

.. _PENG-2448: https://app.clickup.com/t/18022949/PENG-2448
.. _PENG-2451: https://app.clickup.com/t/18022949/PENG-2451
.. _PENG-2444: https://app.clickup.com/t/18022949/PENG-2444
.. _PENG-2344: https://app.clickup.com/t/18022949/PENG-2344

2.4.0 - 2024-10-02
------------------

- Add configurations in the settings for customizing the pool size of the database engines.
- Fix the wrong stack name when getting the stack from aws
- Fix timestamp format and avatar_url in user details route (`PENG-2394`_).
- Fix the idp enpoint returning 500 error for azure idp (`PENG-2393`_).
- Update the Vantage integration policy.
- Implement the API support for the Vantage Agent (`PENG-2359`_).
- Return 428 in the */organizations/my* endpoint in case the user doesn't exist (`PENG-2353`_).
- Fix the wrong stack name when getting the stack from aws.
- Install the Jobbergate and Vantage agents from the Snap Store in the cloud clusters (`PENG-2371`_).

.. _PENG-2353: https://app.clickup.com/t/18022949/PENG-2353
.. _PENG-2393: https://app.clickup.com/t/18022949/PENG-2393
.. _PENG-2394: https://app.clickup.com/t/18022949/PENG-2394
.. _PENG-2359: https://app.clickup.com/t/18022949/PENG-2359


2.3.0 - 2024-08-26
------------------

- Add new statuses in the **IamRoleStateEnum** enum:
  - *NOT_FOUND_OR_NOT_ACCESSIBLE* for the cases where is not performed the assume role operation.
  - *IN_USE* state for the cases where the ARN already exists in the organization
- Fix the *update_user_profile* endpoint to properly update the user's avatar URL.
- Patch the cluster status by adding the status *failed* and renaming the status *connected* to *ready* and *prepared* to *preparing* (`PENG-2195`_).

.. _PENG-2195: https://app.clickup.com/t/18022949/PENG-2195

2.2.0 - 2024-08-14
------------------

- Implement an endpoint to change the user's first and last name, as well as its avatar URL (`PENG-2337`_).
- Shorten the organization free trial period to 14 days (`PENG-2335`_).
- Fix cluster deletion by searching the stack using cluster name instead cluster id.
- Modify the *get_stack_status* function to return *None* in case the stack doesn't exist (`PENG-2321`_).
- Modify the cluster deletion behaviour for deleting the cloud cluster when the CloudFormation stack is in *DELETE_COMPLETE* state (`PENG-2321`_).
- Modify the permissions required by the endpoint */admin/management/members/{user_id}/groups* to fix a unwanted bug (`PENG-2322`_).
- Modify packages' versions in the *Dockerfile*:
    1. Jobbergate API from *5.0.0* to *5.2.0*;
    2. License Manager from *3.1.0* to *3.3.0*.
- Modify the *ClusterName* configuration in the *slurm.conf* file to use a cleaned cluster name instead of the Keycloak's client ID.
- Add missing Jobbergate permissions (*jobbergate:clusters:read* and *jobbergate:clusters:update*) to clusters' clients when creating them.

.. _PENG-2337: https://app.clickup.com/t/18022949/PENG-2337
.. _PENG-2335: https://app.clickup.com/t/18022949/PENG-2335
.. _PENG-2321: https://app.clickup.com/t/18022949/PENG-2321
.. _PENG-2321: https://app.clickup.com/t/18022949/PENG-2321
.. _PENG-2322: https://app.clickup.com/t/18022949/PENG-2322

2.1.0 - 2024-07-03
------------------
- Update the invites and roles endpoints to return the total in their `GET` requests.
- Modify the *get_user_organization* endpoint to always return a list of organizations, even if the user is not part of any organization (`PENG-2313`_).
- Implement endpoint to update the organization settings (`PENG-2025`_).
- Create an endpoint to delete an organization. As well as, a patch was added in the RPC Server script to handle the deletion of an organization (`PENG-1992`_).

.. _PENG-2313: https://app.clickup.com/t/18022949/PENG-2313
.. _PENG-2025: https://app.clickup.com/t/18022949/PENG-2025
.. _PENG-1992: https://app.clickup.com/t/18022949/PENG-1992

2.0.0 - 2024-06-13
------------------

- Patch the *POST /admin/management/walkthrough* endpoint to fix the bug where users were losing their names on Keycloak (`PENG-2296`_).
- Modify the response of the *checkClusterAvailabilityForDeletion* query for returning an enum instead of a string in the *reason* field.
- Build subscriptions into Vantage with the AWS Marketplace (`PENG-1813`_).
- Fix the Unsubscribe pending handler in the SQS Listener.
- Added the unsubscribe_pending handler in the sqs listener (`PENG-2270`_).
- Fix SQS Listener to handle different scenarios when processing a subscription message.
- Implement logic to limit the resource creation based on the subscription tier and type (`PENG-2173`_).
- Update SQS Listeners to the new subscription mode (`PENG-2090`_).
- Implement a GraphQL query for checking if a cluster can be deleted (`PENG-2225`_).
- Implement logic to allow multiple instance types by region when deploying a cloud cluster (`PENG-2181`_).
- Create an endpoint to check if a given IAM role is valid or not based on its existence, permissions and ARN regex (`PENG-2092`_).
- Update walkthrough route to fit the keycloak version 24 requirements.
- Update the Jobbergate version to 5.0.0 in Dockerfile.
- Update the Jobbergate agent version to 5.0.0 in the cloud cluster stack.
- Remove the Slurmrestd settings from the cloud cluster stack when setting up the Jobbergate agent.
- Update the Vantage API to give the new clusters the correct set of permissions (`PENG-2168`_).

.. _PENG-2296: https://app.clickup.com/t/18022949/PENG-2296
.. _PENG-2270: https://app.clickup.com/t/18022949/PENG-2270
.. _PENG-2090: https://app.clickup.com/t/18022949/PENG-2090
.. _PENG-2225: https://app.clickup.com/t/18022949/PENG-2225
.. _PENG-2181: https://app.clickup.com/t/18022949/PENG-2181
.. _PENG-2092: https://app.clickup.com/t/18022949/PENG-2092
.. _PENG-2168: https://app.clickup.com/t/18022949/PENG-2168
.. _PENG-2198: https://app.clickup.com/t/18022949/PENG-2198
.. _PENG-2173: https://app.clickup.com/t/18022949/PENG-2173
.. _PENG-1813: https://app.clickup.com/t/18022949/PENG-1813


1.3.0 - 2024-04-01
------------------

- Revise the implementation of mounting storage into cloud clusters to also mount the storage into the compute nodes (`PENG-2169`_).
- Fix bug in the cloud cluster stack where the region was fixed as us-west-2.
- Fix bug where existing users that don't belong to any organization were prevented to have the correct permissions after joining an organization by invitation (`PENG-2148`_).
- Disable cloud account deletion if the cloud account is in use (`PENG-2126`_).
- Fix the Jobbergate Agent version in the Cloudformation templates, as well as add a new variable to the *.env* file for the agent in the cloud cluster.
- Create an endpoint to check if the requester has a pending invite to any organization.

.. _PENG-2148: https://app.clickup.com/t/18022949/PENG-2148
.. _PENG-2126: https://app.clickup.com/t/18022949/PENG-2126
.. _PENG-2169: https://app.clickup.com/t/18022949/PENG-2169

1.2.0 - 2024-03-21
------------------

- Implement logic to cache the database engines in a local dictionary.
- Upgrade the *boto3* version to *^1.34.29* in order to solve conflict with the OpenTelemetry auto intrumentation. For reference about the issue, check out the link https://github.com/open-telemetry/opentelemetry-operator/issues/1774.
- Fix logic in the Cloud Account stack lambda function where the authorization header wasn't being set when calling the API.
- Fix the trust relationship and update account role permissions (`PENG-2095`_).
- Fix: Await database connection when deleting a cluster.
- Fix the database query execution into background threads.
- Fix the *5d31f6787421* migration by applying many fixes to the migration script:
    1. Fix queries passed to *conn.execute* calls by using the *sqlalchemy.text* function before;
    2. Remove the execution of the ``SELECT lastval()`` query due to the fact that it's not necessary;
    3. Remove the *drop_contraint* call from the downgrade method.
- Update the Jobbergate version in Dockerfile from version 4.3.0a2 to 4.4.0.
- Update the License Manager version in Dockerfile from version 3.0.12 to 3.1.0.
- Update the SOS version in Dockerfile from version 1.3.0 to 1.6.1.
- Update the Notifications version in Dockerfile from version 0.4.0 to 0.6.0.
- Fix the trust relationship and update account role permissions (`PENG-2095`_).
- Modify the code base to use the new AMIs for the cloud cluster (`PENG-1744`_).

.. _PENG-2095: https://app.clickup.com/t/18022949/PENG-2095
.. _PENG-1744: https://app.clickup.com/t/18022949/PENG-1744

1.1.0 - 2024-02-21
------------------

- Updated the Jobbergate version in Dockerfile from version 4.0.2 to 4.3.0a2.
- Fix fails when deleting cloud aws cluster due fk constraint  (`PENG-1671`_).
- Implement backend components for the new Cloud Accounts (`PENG-1795`_).
- Integrate the Cluster API with the Cloud Accounts (`PENG-1800`_).
- Fix bug where the organization creator wasn't granted Full Admin permissions (`PENG-2078`_).
- Integrate the Storage section with the Cloud Accounts (`PENG-1823`_).

.. _PENG-1671: https://app.clickup.com/t/18022949/PENG-1671
.. _PENG-1795: https://app.clickup.com/t/18022949/PENG-1795
.. _PENG-1800: https://app.clickup.com/t/18022949/PENG-1800
.. _PENG-2078: https://app.clickup.com/t/18022949/PENG-2078
.. _PENG-1823: https://app.clickup.com/t/18022949/PENG-1823

1.0.0 - 2024-01-15
------------------

- Merge the Admin API 2.1.2 (`Admin API CHANGELOG`_) and the Cluster API 6.4.0 (`Cluster API CHANGELOG`_).

.. _Admin API CHANGELOG: https://github.com/omnivector-solutions/armada-admin-api/blob/release/2.1/CHANGELOG.rst
.. _Cluster API CHANGELOG: https://github.com/omnivector-solutions/armada-api/blob/release/6.4/CHANGELOG.rst
