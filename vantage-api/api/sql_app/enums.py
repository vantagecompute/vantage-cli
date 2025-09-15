"""Core module for storing enumerations definitions."""
import enum
import math


class StorageSourceEnum(str, enum.Enum):

    """Storage source enumeration."""

    vantage = "vantage"
    imported = "imported"


class MountPointStatusEnum(str, enum.Enum):

    """Mount point status enumeration."""

    mounting = enum.auto()
    mounted = enum.auto()
    deleting = enum.auto()
    error = enum.auto()


class ClusterStatusEnum(str, enum.Enum):

    """Cluster status enumeration."""

    preparing = enum.auto()
    ready = enum.auto()
    deleting = enum.auto()
    failed = enum.auto()


class ClusterProviderEnum(str, enum.Enum):

    """Cluster provider enumeration."""

    aws = "aws"
    on_prem = "on_prem"


class CloudAccountEnum(str, enum.Enum):

    """Cloud account enumeration."""

    aws = "aws"


class ClusterQueueActionEnum(str, enum.Enum):

    """Cluster queue action enumeration."""

    cancel = "cancel"


class SubscriptionTiersNames(str, enum.Enum):

    """Subscription tiers names."""

    starter = "starter"
    teams = "teams"
    pro = "pro"
    enterprise = "enterprise"


class SubscriptionTypesNames(str, enum.Enum):

    """Subscription types names."""

    aws = "aws"
    cloud = "cloud"


class SubscriptionTierSeats(enum.Enum):

    """Subscription tier seats.

    This enum is mainly intended to be used during testing the app.
    Als, this enum ensures each subscription tier has its allowed seats
    where **None** means unlimited seats.
    """

    starter = 5
    teams = 20
    pro = 50
    enterprise = math.inf


class SubscriptionTierClusters(enum.Enum):

    """Subscription tier clusters.

    This enum is mainly intended to be used during testing the app.
    Als, this enum ensures each subscription tier has its allowed clusters
    where **None** means unlimited clusters.
    """

    starter = 2
    teams = 10
    pro = 20
    enterprise = math.inf


class SubscriptionTierStorageSystems(enum.Enum):

    """Subscription tier storage systems.

    This enum is mainly intended to be used during testing the app.
    Als, this enum ensures each subscription tier has its allowed storage systems
    where **None** means unlimited storage systems.
    """

    starter = 2
    teams = 10
    pro = 20
    enterprise = math.inf
