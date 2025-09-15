"""Core module for defining general queries against the Keycloak database used across the app."""
from textwrap import dedent

CHECK_EMAIL_AVAILABILITY_FOR_INVITATION = dedent(
    """
    SELECT
        ue.*,
        ugm.*,
        o.*
    FROM
        user_entity ue
    INNER JOIN
        user_group_membership ugm ON ue.id = ugm.user_id
    INNER JOIN
        keycloak_group kg ON ugm.group_id = kg.id
    LEFT JOIN
        org o ON ugm.group_id = o.group_id
    WHERE
        ue.email = $1
        AND kg.type = 1;
    """
).strip()


GET_ORGANIZATION_ID_BY_NAME = dedent(
    """
    SELECT id
    FROM org
    WHERE alias = $1;
    """
).strip()


GET_USER_ID = dedent(
    """
    SELECT id
    FROM user_entity
    WHERE email = $1 and realm = 'vantage';
    """
).strip()
