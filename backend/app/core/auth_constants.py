IDP_GROUP_PORTAL_ADMIN = "cosmolet_role_admin"
# Группа Keycloak «outstaff» — IdP-метка отдела, НЕ политика «менеджер портала».
# Менеджер = gid_number == SSO_GID_OUTSTAFF (см. permissions.is_manager_or_admin).
IDP_GROUP_OUTSTAFF = "outstaff"
IDP_GROUP_MANAGER = IDP_GROUP_OUTSTAFF  # алиас совместимости; не использовать для RBAC менеджера
IDP_GROUP_DEVELOPER = "students"

# Должности SSO (claim ``position``); см. документацию Effective Mobile SSO.
SSO_POSITION_AU_SPECIALIST = "au_specialist"
SSO_POSITION_STUDENT = "student"

# Основной отдел SSO (claim ``gid_number``). «Аутстафф» / АУ — единственный отдел менеджера.
SSO_GID_OUTSTAFF = "10000"

TIMESHEET_ONLY_POSITIONS: frozenset[str] = frozenset(
    {
        SSO_POSITION_AU_SPECIALIST,
        SSO_POSITION_STUDENT,
    }
)

IDP_KNOWN_PORTAL_GROUPS: tuple[str, ...] = (
    IDP_GROUP_PORTAL_ADMIN,
    IDP_GROUP_OUTSTAFF,
    IDP_GROUP_DEVELOPER,
)

SPA_OAUTH_CALLBACK_PATH = "/auth/callback"


def normalize_sso_gid_number(raw: object) -> str | None:
    """Привести gid_number из SSO (строка или int) к канонической строке."""
    if raw is None or isinstance(raw, bool):
        return None
    if isinstance(raw, int):
        return str(raw)
    if isinstance(raw, str):
        stripped = raw.strip()
        return stripped or None
    return None
