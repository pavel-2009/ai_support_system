from app.models.user import UserRole


def test_user_roles_enum_values() -> None:
    assert UserRole.USER.value == "user"
    assert UserRole.OPERATOR.value == "operator"
    assert UserRole.ADMIN.value == "admin"


def test_user_roles_are_unique() -> None:
    values = {role.value for role in UserRole}
    assert values == {"user", "operator", "admin"}
