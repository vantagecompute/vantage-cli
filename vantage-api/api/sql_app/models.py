"""Core module for storing base sqlalchemy models."""
from typing import List

from sqlalchemy import (
    ARRAY,
    Boolean,
    Column,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
    inspect,
    sql,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, relationship
from sqlalchemy.orm.decl_api import declarative_mixin
from sqlalchemy.orm.mapper import Mapper

from api.sql_app import Base, enums


@declarative_mixin
class StaticReferenceMixin:

    """Common resources between all tables.

    The attributes define rows and the methods API-level resources.
    """

    def as_dict(self):
        """Transform the SQLAlchemy model to a dictionary. It also returns the relations."""
        mapper: Mapper = inspect(self).mapper
        return {
            **{col.key: getattr(self, col.key) for col in mapper.column_attrs},
            **{
                rel: getattr(self, rel) if getattr(self, rel) is not None else []
                for rel in mapper.relationships.keys()
            },
        }


class ClusterModel(Base, StaticReferenceMixin):

    """Cluster table schema."""

    __tablename__ = "cluster"

    name = Column(String, primary_key=True, unique=True)
    status = Column(Enum(enums.ClusterStatusEnum))
    client_id = Column(String, index=True)
    description = Column(String)
    owner_email = Column(String)
    creation_parameters = Column(JSONB, nullable=True)
    creation_status_details = Column(ARRAY(JSONB), nullable=True, default=[])
    provider = Column(
        Enum(enums.ClusterProviderEnum),
        default=enums.ClusterProviderEnum.on_prem,
        values_callable=lambda x: [e.value for e in x],
    )
    cloud_account_id = Column(Integer, ForeignKey("cloud_account.id", ondelete="CASCADE"), nullable=True)

    cloud_account: Mapped["CloudAccountModel"] = relationship(
        "CloudAccountModel", back_populates="cluster", lazy="subquery"
    )
    mount_points: Mapped[List["MountPointModel"]] = relationship(
        "MountPointModel", back_populates="cluster", lazy="subquery"
    )
    slurm_cluster_config: Mapped["SlurmClusterConfig"] = relationship(
        "SlurmClusterConfig", back_populates="cluster", lazy="subquery", uselist=False
    )
    all_partition_info: Mapped["AllPartitionInfo"] = relationship(
        "AllPartitionInfo", back_populates="cluster", lazy="subquery"
    )
    all_queue_info: Mapped["AllQueueInfo"] = relationship(
        "AllQueueInfo", back_populates="cluster", lazy="subquery"
    )
    all_node_info: Mapped["AllNodeInfo"] = relationship(
        "AllNodeInfo", back_populates="cluster", lazy="subquery"
    )
    partitions: Mapped[list["PartitionModel"]] = relationship(
        "PartitionModel", back_populates="cluster", lazy="subquery"
    )
    cluster_partitions: Mapped[list["ClusterPartitionsModel"]] = relationship(
        "ClusterPartitionsModel", back_populates="cluster", lazy="subquery"
    )
    nodes: Mapped[list["NodeModel"]] = relationship("NodeModel", back_populates="cluster", lazy="subquery")
    agent_health_check: Mapped["AgentHealthCheckModel"] = relationship(
        "AgentHealthCheckModel", back_populates="cluster", lazy="subquery", uselist=False
    )
    notebook_servers: Mapped[list["NotebookServerModel"]] = relationship(
        "NotebookServerModel", back_populates="cluster", lazy="subquery"
    )
    queue: Mapped["QueueModel"] = relationship("QueueModel", back_populates="cluster", lazy="subquery")
    cluster_queue_actions: Mapped[list["ClusterQueueActionsModel"]] = relationship(
        "ClusterQueueActionsModel", back_populates="cluster", lazy="subquery"
    )


class StorageModel(Base, StaticReferenceMixin):

    """Storage table schema."""

    __tablename__ = "storage"

    id = Column(Integer, primary_key=True, autoincrement=True, unique=True, nullable=False)
    fs_id = Column(String, unique=True, primary_key=True)
    name = Column(String, unique=True)
    region = Column(String, nullable=False)
    source = Column(Enum(enums.StorageSourceEnum), nullable=False)
    owner = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=sql.func.now(), nullable=False)
    cloud_account_id = Column(Integer, ForeignKey("cloud_account.id", ondelete="CASCADE"), nullable=False)

    mount_points: Mapped[List["MountPointModel"]] = relationship(
        "MountPointModel", back_populates="storage", lazy="subquery"
    )
    cloud_account: Mapped["CloudAccountModel"] = relationship(
        "CloudAccountModel", back_populates="storage", lazy="subquery"
    )


class MountPointModel(Base, StaticReferenceMixin):

    """Mount point table schema."""

    __tablename__ = "mount_point"

    id = Column(Integer, primary_key=True, autoincrement=True, unique=True, nullable=False)
    cluster_name = Column(String, ForeignKey(ClusterModel.name), primary_key=True)
    storage_id = Column(Integer, ForeignKey(StorageModel.id), primary_key=True)
    client_id = Column(String, nullable=False)
    mount_point = Column(String, server_default="/nfs", nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=sql.func.now(), nullable=False)
    status = Column(Enum(enums.MountPointStatusEnum), server_default="mounting")
    error = Column(String, nullable=True)

    storage: Mapped["StorageModel"] = relationship(
        "StorageModel", back_populates="mount_points", lazy="subquery"
    )
    cluster: Mapped["ClusterModel"] = relationship(
        "ClusterModel", back_populates="mount_points", lazy="subquery"
    )


class CloudAccountModel(Base, StaticReferenceMixin):

    """Cloud account table schema.

    Originally, the schema was defined on [PENG-1795](https://app.clickup.com/t/18022949/PENG-1795).
    """

    __tablename__ = "cloud_account"

    id = Column(Integer, primary_key=True, autoincrement=True, unique=True, nullable=False)
    provider = Column(Enum(enums.CloudAccountEnum), nullable=False)
    name = Column(String, unique=True, nullable=False)
    assisted_cloud_account = Column(Boolean, nullable=False, default=False)
    description = Column(String, nullable=True)
    attributes = Column(JSONB, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=sql.func.now(), nullable=False)
    updated_at = Column(
        DateTime(timezone=True),
        server_default=sql.func.now(),
        nullable=False,
        onupdate=sql.func.current_timestamp(),
    )

    cluster: Mapped[ClusterModel] = relationship(
        "ClusterModel", back_populates="cloud_account", lazy="subquery"
    )
    storage: Mapped[StorageModel] = relationship(
        "StorageModel", back_populates="cloud_account", lazy="subquery"
    )


class CloudAccountApiKeyModel(Base, StaticReferenceMixin):

    """Cloud account API key table schema."""

    __tablename__ = "cloud_account_api_key"

    id = Column(Integer, primary_key=True, autoincrement=True, unique=True, nullable=False)
    api_key = Column(String, nullable=False, unique=True)
    organization_id = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=sql.func.now(), nullable=False)


class SubscriptionModel(Base, StaticReferenceMixin):

    """Subscription table schema."""

    __tablename__ = "subscription"

    id = Column(Integer, primary_key=True, autoincrement=True, unique=True, nullable=False)
    organization_id = Column(String, nullable=False, index=True)
    type_id = Column(Integer, ForeignKey("subscription_type.id", ondelete="CASCADE"), nullable=False)
    tier_id = Column(Integer, ForeignKey("subscription_tier.id", ondelete="CASCADE"), nullable=False)
    detail_data = Column(JSONB, nullable=False, default={})
    created_at = Column(DateTime(timezone=True), server_default=sql.func.now(), nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=True)
    is_free_trial = Column(Boolean, nullable=False, default=False)

    subscription_type: Mapped["SubscriptionTypeModel"] = relationship(
        "SubscriptionTypeModel", back_populates="subscription", lazy="subquery"
    )
    subscription_tier: Mapped["SubscriptionTierModel"] = relationship(
        "SubscriptionTierModel", back_populates="subscription", lazy="subquery"
    )


class SubscriptionTypeModel(Base, StaticReferenceMixin):

    """Subscription type table schema."""

    __tablename__ = "subscription_type"

    id = Column(Integer, primary_key=True, autoincrement=True, unique=True, nullable=False)
    name = Column(Enum(enums.SubscriptionTypesNames))

    subscription: Mapped[list[SubscriptionModel]] = relationship(
        "SubscriptionModel", back_populates="subscription_type", lazy="subquery"
    )


class SubscriptionTierModel(Base, StaticReferenceMixin):

    """Subscription tier table schema."""

    __tablename__ = "subscription_tier"

    id = Column(Integer, primary_key=True, autoincrement=True, unique=True, nullable=False)
    name = Column(Enum(enums.SubscriptionTiersNames))
    seats = Column(Integer, nullable=True)
    clusters = Column(Integer, nullable=True)
    storage_systems = Column(Integer, nullable=True)

    subscription: Mapped[list[SubscriptionModel]] = relationship(
        "SubscriptionModel", back_populates="subscription_tier", lazy="subquery"
    )


class PendingAwsSubscriptionsModel(Base, StaticReferenceMixin):

    """Pending AWS subscriptions table schema."""

    __tablename__ = "pending_aws_subscriptions"

    id = Column(Integer, primary_key=True, autoincrement=True, unique=True, nullable=False)
    organization_id = Column(String, nullable=False, index=True)
    customer_aws_account_id = Column(String, nullable=False, unique=True)
    customer_identifier = Column(String, nullable=False, unique=True)
    product_code = Column(String, nullable=False)
    has_failed = Column(Boolean, nullable=False, server_default="false")
    created_at = Column(DateTime(timezone=True), server_default=sql.func.now(), nullable=False)


class OrganizationFreeTrialsModel(Base, StaticReferenceMixin):

    """Organization free trials table schema."""

    __tablename__ = "organization_free_trials"

    id = Column(Integer, primary_key=True, autoincrement=True, unique=True, nullable=False)
    organization_id = Column(String, nullable=False, index=True)


class SlurmClusterConfig(Base, StaticReferenceMixin):

    """Slurm cluster config table schema."""

    __tablename__ = "slurm_cluster_config"

    id = Column(Integer, primary_key=True, autoincrement=True, unique=True, nullable=False)
    cluster_name = Column(
        String, ForeignKey(ClusterModel.name, ondelete="CASCADE"), nullable=False, unique=True, index=True
    )
    info = Column(JSONB, nullable=False, default={})
    updated_at = Column(
        DateTime(timezone=True),
        server_default=sql.func.now(),
        nullable=False,
        onupdate=sql.func.current_timestamp(),
    )

    cluster: Mapped["ClusterModel"] = relationship(
        "ClusterModel", back_populates="slurm_cluster_config", lazy="subquery", uselist=False
    )


class AllPartitionInfo(Base, StaticReferenceMixin):

    """All partition info table schema."""

    __tablename__ = "all_partition_info"

    id = Column(Integer, primary_key=True, autoincrement=True, unique=True, nullable=False)
    cluster_name = Column(
        String, ForeignKey(ClusterModel.name, ondelete="CASCADE"), nullable=False, unique=True, index=True
    )
    info = Column(JSONB, nullable=False, default={})
    updated_at = Column(
        DateTime(timezone=True),
        server_default=sql.func.now(),
        nullable=False,
        onupdate=sql.func.current_timestamp(),
    )

    cluster: Mapped["ClusterModel"] = relationship(
        "ClusterModel", back_populates="all_partition_info", lazy="subquery", uselist=False
    )


class AllNodeInfo(Base, StaticReferenceMixin):

    """All node info table schema."""

    __tablename__ = "all_node_info"

    id = Column(Integer, primary_key=True, autoincrement=True, unique=True, nullable=False)
    cluster_name = Column(
        String, ForeignKey(ClusterModel.name, ondelete="CASCADE"), nullable=False, unique=True, index=True
    )
    info = Column(JSONB, nullable=False, default={})
    updated_at = Column(
        DateTime(timezone=True),
        server_default=sql.func.now(),
        nullable=False,
        onupdate=sql.func.current_timestamp(),
    )

    cluster: Mapped["ClusterModel"] = relationship(
        "ClusterModel", back_populates="all_node_info", lazy="subquery", uselist=False
    )


class AllQueueInfo(Base, StaticReferenceMixin):

    """All queue info table schema."""

    __tablename__ = "all_queue_info"

    id = Column(Integer, primary_key=True, autoincrement=True, unique=True, nullable=False)
    cluster_name = Column(
        String, ForeignKey(ClusterModel.name, ondelete="CASCADE"), nullable=False, unique=True, index=True
    )
    info = Column(JSONB, nullable=False, default={})
    updated_at = Column(
        DateTime(timezone=True),
        server_default=sql.func.now(),
        nullable=False,
        onupdate=sql.func.current_timestamp(),
    )

    cluster: Mapped["ClusterModel"] = relationship(
        "ClusterModel", back_populates="all_queue_info", lazy="subquery", uselist=False
    )


class PartitionModel(Base, StaticReferenceMixin):

    """Partition table schema."""

    __tablename__ = "partition_info"
    __table_args__ = (UniqueConstraint("cluster_name", "name", name="uix_cluster_name_name"),)

    id = Column(Integer, primary_key=True, autoincrement=True, unique=True, nullable=False)
    cluster_name = Column(
        String, ForeignKey(ClusterModel.name, ondelete="CASCADE"), nullable=False, index=True
    )
    name = Column(String, nullable=False, index=True)
    info = Column(JSONB, nullable=False, default={})
    updated_at = Column(
        DateTime(timezone=True),
        server_default=sql.func.now(),
        nullable=False,
        onupdate=sql.func.current_timestamp(),
    )

    cluster: Mapped["ClusterModel"] = relationship(
        "ClusterModel", back_populates="partitions", lazy="subquery", uselist=False
    )


class QueueModel(Base, StaticReferenceMixin):

    """Queue table schema."""

    __tablename__ = "queue_info"
    __table_args__ = (UniqueConstraint("cluster_name", name="uix_cluster_name"),)

    id = Column(Integer, primary_key=True, autoincrement=True, unique=True, nullable=False)
    cluster_name = Column(
        String,
        ForeignKey(ClusterModel.name, ondelete="CASCADE", onupdate="CASCADE"),
        nullable=False,
        index=True,
    )
    name = Column(String, nullable=False, index=True)
    info = Column(JSONB, nullable=False, default={})
    updated_at = Column(
        DateTime(timezone=True),
        server_default=sql.func.now(),
        nullable=False,
        onupdate=sql.func.current_timestamp(),
    )

    cluster: Mapped["ClusterModel"] = relationship(
        "ClusterModel", back_populates="queue", lazy="subquery", uselist=False
    )
    cluster_queue_actions: Mapped[list["ClusterQueueActionsModel"]] = relationship(
        "ClusterQueueActionsModel", back_populates="queue", lazy="subquery"
    )

class NodeModel(Base, StaticReferenceMixin):

    """Node table schema."""

    __tablename__ = "node_info"
    __table_args__ = (UniqueConstraint("cluster_name", "name", name="uix_cluster_name_name"),)

    id = Column(Integer, primary_key=True, autoincrement=True, unique=True, nullable=False)
    cluster_name = Column(
        String, ForeignKey(ClusterModel.name, ondelete="CASCADE"), nullable=False, index=True
    )
    name = Column(String, nullable=False, index=True)
    partition_names = Column(ARRAY(String), nullable=False)
    info = Column(JSONB, nullable=False, default={})
    updated_at = Column(
        DateTime(timezone=True),
        server_default=sql.func.now(),
        nullable=False,
        onupdate=sql.func.current_timestamp(),
    )

    cluster: Mapped["ClusterModel"] = relationship(
        "ClusterModel", back_populates="nodes", lazy="subquery", uselist=False
    )


class AgentHealthCheckModel(Base, StaticReferenceMixin):

    """Agent health check table schema."""

    __tablename__ = "agent_health_check"

    id = Column(Integer, primary_key=True, autoincrement=True, unique=True, nullable=False)
    cluster_name = Column(
        String, ForeignKey(ClusterModel.name, ondelete="CASCADE"), nullable=False, index=True, unique=True
    )
    interval = Column(Integer, nullable=False)
    last_reported = Column(
        DateTime(timezone=True),
        server_default=sql.func.now(),
        nullable=False,
        onupdate=sql.func.current_timestamp(),
    )

    cluster: Mapped["ClusterModel"] = relationship(
        "ClusterModel", back_populates="agent_health_check", lazy="subquery", uselist=False
    )


class AwsNodeTypesModel(Base, StaticReferenceMixin):

    """AWS node types table schema."""

    __tablename__ = "aws_node_types"
    __table_args__ = (UniqueConstraint("instance_type", "aws_region", name="uix_instance_type_aws_region"),)

    id = Column(Integer, primary_key=True, autoincrement=True, unique=True, nullable=False)
    instance_type = Column(String, nullable=False, index=True)
    aws_region = Column(String, nullable=False, index=True)
    cpu_manufacturer = Column(String, nullable=False, index=True)
    cpu_name = Column(String, nullable=False, index=True)
    cpu_arch = Column(String, nullable=False, index=True)
    num_cpus = Column(Integer, nullable=False)
    memory = Column(Integer, nullable=False)
    gpu_manufacturer = Column(String, nullable=True, index=True)
    gpu_name = Column(String, nullable=True, index=True)
    num_gpus = Column(Integer, nullable=False)
    price_per_hour = Column(Float, nullable=False)


class AwsNodeTypesFiltersModel(Base, StaticReferenceMixin):

    """AWS node types filters table schema."""

    __tablename__ = "aws_node_types_filters"

    filter_name = Column(String, primary_key=True, nullable=False)
    filter_values = Column(ARRAY(String), nullable=False)


class ClusterPartitionsModel(Base, StaticReferenceMixin):
    """Cluster partitions table schema."""

    __tablename__ = "cluster_partitions"
    id = Column(Integer, primary_key=True, autoincrement=True, unique=True, nullable=False)
    cluster_name = Column(String, ForeignKey("cluster.name", ondelete="CASCADE"), nullable=True)
    name = Column(String, nullable=False)
    node_type = Column(String, nullable=False)
    max_node_count = Column(Integer, nullable=False)
    is_default = Column(Boolean, nullable=False, default=False)

    cluster: Mapped["ClusterModel"] = relationship(
        "ClusterModel", back_populates="cluster_partitions", lazy="subquery", uselist=False
    )


class NotebookServerModel(Base, StaticReferenceMixin):

    """Partition table schema."""

    __tablename__ = "notebook_servers"
    __table_args__ = (UniqueConstraint("cluster_name", "name", name="uix_cluster_name_name"),)

    id = Column(Integer, primary_key=True, autoincrement=True, unique=True, nullable=False)
    cluster_name = Column(
        String, ForeignKey(ClusterModel.name, ondelete="CASCADE"), nullable=False, index=True
    )
    name = Column(String, nullable=False, index=True)
    owner = Column(String, nullable=True)
    partition = Column(String, nullable=True)
    server_url = Column(String, nullable=False)
    slurm_job_id = Column(Integer, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=sql.func.now(), nullable=False)

    updated_at = Column(
        DateTime(timezone=True),
        server_default=sql.func.now(),
        nullable=False,
        onupdate=sql.func.current_timestamp(),
    )

    cluster: Mapped["ClusterModel"] = relationship(
        "ClusterModel", back_populates="notebook_servers", lazy="subquery", uselist=False
    )


class ClusterQueueActionsModel(Base, StaticReferenceMixin):

    """Cluster queue actions table schema."""

    __tablename__ = "cluster_queue_actions"
    __table_args__ = (UniqueConstraint("cluster_name", "queue_id", name="uix_cluster_name_queue_id"),)

    id = Column(Integer, primary_key=True, autoincrement=True, unique=True, nullable=False)
    cluster_name = Column(
        String, ForeignKey(ClusterModel.name, ondelete="CASCADE"), nullable=False, index=True
    )
    queue_id = Column(Integer, ForeignKey(QueueModel.id, ondelete="CASCADE"), nullable=False, index=True)
    action = Column(Enum(enums.ClusterQueueActionEnum), nullable=False)

    queue: Mapped[QueueModel] = relationship(
        "QueueModel", back_populates="cluster_queue_actions", lazy="subquery", uselist=False
    )
    cluster: Mapped[ClusterModel] = relationship(
        "ClusterModel", back_populates="cluster_queue_actions", lazy="subquery", uselist=False
    )
