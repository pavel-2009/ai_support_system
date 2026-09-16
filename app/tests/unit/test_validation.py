"""Negative and boundary tests for API input validation."""

import pytest
from pydantic import ValidationError

from app.models.conversation import Channel, Priority
from app.schemas.conversation import ConversationCreate
from app.schemas.message import MessageCreate
from app.schemas.user import UserCreate, UserUpdate


class TestMessageValidation:
    def test_content_cannot_exceed_10000_characters(self):
        with pytest.raises(ValidationError):
            MessageCreate(content="a" * 10_001)

    def test_html_tags_are_removed(self):
        message = MessageCreate(content='<script>alert("xss")</script>Hello <b>world</b>')
        assert message.content == 'alert("xss")Hello world'

    def test_html_only_content_is_rejected(self):
        with pytest.raises(ValidationError):
            MessageCreate(content="<script></script>")


class TestUserValidation:
    def test_invalid_email_is_rejected(self):
        with pytest.raises(ValidationError):
            UserCreate(
                email="not-an-email",
                nickname="valid_user",
                password="StrongPass1!",
            )

    @pytest.mark.parametrize(
        "password",
        [
            "short1!",
            "Password!",
            "password1!",
            "Password1",
        ],
    )
    def test_weak_password_is_rejected(self, password: str):
        with pytest.raises(ValidationError):
            UserCreate(
                email="user@example.com",
                nickname="valid_user",
                password=password,
            )

    @pytest.mark.parametrize(
        "nickname",
        ["ab", "bad.name", "русский", "user name", "a" * 33],
    )
    def test_invalid_username_is_rejected(self, nickname: str):
        with pytest.raises(ValidationError):
            UserCreate(
                email="user@example.com",
                nickname=nickname,
                password="StrongPass1!",
            )

    def test_hyphenated_username_is_accepted(self):
        user = UserCreate(
            email="user@example.com",
            nickname="operator-8407d1c1",
            password="StrongPass1!",
        )
        assert user.nickname == "operator-8407d1c1"

    def test_invalid_username_is_rejected_on_update(self):
        with pytest.raises(ValidationError):
            UserUpdate(nickname="bad.name")


class TestConversationValidation:
    def test_invalid_priority_is_rejected(self):
        with pytest.raises(ValidationError):
            ConversationCreate(priority="urgent")

    def test_invalid_channel_is_rejected(self):
        with pytest.raises(ValidationError):
            ConversationCreate(channel="telegram")

    def test_valid_enum_values_are_accepted(self):
        conversation = ConversationCreate(
            priority=Priority.HIGH,
            channel=Channel.WEB,
        )
        assert conversation.priority is Priority.HIGH
        assert conversation.channel is Channel.WEB
