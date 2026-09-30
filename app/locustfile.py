import os
import time
from uuid import uuid4

from locust import HttpUser, between, task


class SupportUser(HttpUser):
    """
    Locust virtual user for AI Support load testing.

    Journeys:
        1. Register -> Login
        2. Create conversation -> Send 5 messages
        3. Create conversation -> Ask AI to escalate
           -> Wait for escalation -> Operator login
           -> Assign conversation -> Operator reply
    """

    wait_time = between(1, 3)

    user_password = os.getenv(
        "LOCUST_USER_PASSWORD",
        "LocustPass123!",
    )

    operator_email = os.getenv(
        "LOCUST_OPERATOR_EMAIL",
        "operator@example.com",
    )

    operator_password = os.getenv(
        "LOCUST_OPERATOR_PASSWORD",
        "OperatorPass123!",
    )

    escalation_timeout = int(
        os.getenv("LOCUST_ESCALATION_TIMEOUT", "60")
    )

    def on_start(self):
        """Register and authenticate a new virtual user."""

        self.email = f"locust_{uuid4().hex}@example.com"
        self.nickname = f"locust_{uuid4().hex[:16]}"

        self.token = None
        self.operator_token = None

        self.register_and_login()

    # ------------------------------------------------------------------
    # Authentication
    # ------------------------------------------------------------------

    def register_and_login(self):
        """Register the virtual user and obtain an access token."""

        with self.client.post(
            "/api/auth/register",
            json={
                "email": self.email,
                "nickname": self.nickname,
                "password": self.user_password,
            },
            name="POST /api/auth/register",
            catch_response=True,
        ) as response:
            if response.status_code != 201:
                response.failure(
                    f"Registration failed: {response.status_code}"
                )
                return

        with self.client.post(
            "/api/auth/login",
            json={
                "email": self.email,
                "password": self.user_password,
            },
            name="POST /api/auth/login",
            catch_response=True,
        ) as response:
            if response.status_code != 200:
                response.failure(
                    f"Login failed: {response.status_code}"
                )
                return

            data = response.json()
            self.token = data.get("access_token")

            if not self.token:
                response.failure(
                    "Login response does not contain access_token"
                )

    def login_operator(self):
        """Authenticate the operator."""

        with self.client.post(
            "/api/auth/login",
            json={
                "email": self.operator_email,
                "password": self.operator_password,
            },
            name="POST /api/auth/login [operator]",
            catch_response=True,
        ) as response:
            if response.status_code != 200:
                response.failure(
                    f"Operator login failed: {response.status_code}"
                )
                return False

            data = response.json()
            self.operator_token = data.get("access_token")

            if not self.operator_token:
                response.failure(
                    "Operator login response does not contain access_token"
                )
                return False

        return True

    # ------------------------------------------------------------------
    # Headers
    # ------------------------------------------------------------------

    @property
    def user_headers(self):
        return {
            "Authorization": f"Bearer {self.token}",
        }

    @property
    def operator_headers(self):
        return {
            "Authorization": f"Bearer {self.operator_token}",
        }

    # ------------------------------------------------------------------
    # Conversation operations
    # ------------------------------------------------------------------

    def create_conversation(self):
        """Create a new conversation."""

        with self.client.post(
            "/api/conversations/",
            json={
                "priority": "medium",
                "channel": "api",
            },
            headers=self.user_headers,
            name="POST /api/conversations/",
            catch_response=True,
        ) as response:
            if response.status_code != 201:
                response.failure(
                    f"Conversation creation failed: "
                    f"{response.status_code}"
                )
                return None

            data = response.json()
            conversation_id = data.get("id")

            if conversation_id is None:
                response.failure(
                    "Conversation response does not contain id"
                )
                return None

            return conversation_id

    def send_message(self, conversation_id: int, content: str):
        """Send a user message."""

        with self.client.post(
            f"/api/conversations/{conversation_id}/messages",
            json={
                "content": content,
            },
            headers=self.user_headers,
            name="POST /api/conversations/{id}/messages",
            catch_response=True,
        ) as response:
            if response.status_code != 201:
                response.failure(
                    f"Message creation failed: "
                    f"{response.status_code}"
                )
                return False

        return True

    # ------------------------------------------------------------------
    # Escalation
    # ------------------------------------------------------------------

    def wait_for_escalation(self, conversation_id: int):
        """
        Wait until Celery + LLM processing changes the conversation
        status to 'escalated'.

        Returns True when escalation happens.
        """

        started_at = time.monotonic()

        while time.monotonic() - started_at < self.escalation_timeout:
            with self.client.get(
                f"/api/conversations/{conversation_id}",
                headers=self.user_headers,
                name="GET /api/conversations/{id}",
                catch_response=True,
            ) as response:
                if response.status_code != 200:
                    response.failure(
                        f"Conversation status check failed: "
                        f"{response.status_code}"
                    )
                    time.sleep(1)
                    continue

                status_value = response.json().get("status")

                if status_value == "escalated":
                    return True

            time.sleep(1)

        return False

    # ------------------------------------------------------------------
    # Operator operations
    # ------------------------------------------------------------------

    def assign_conversation(self, conversation_id: int):
        """Assign an escalated conversation to the operator."""

        with self.client.post(
            f"/api/operator/assign/{conversation_id}",
            headers=self.operator_headers,
            name="POST /api/operator/assign/{id}",
            catch_response=True,
        ) as response:
            if response.status_code != 200:
                response.failure(
                    f"Conversation assignment failed: "
                    f"{response.status_code}"
                )
                return False

        return True

    def operator_reply(self, conversation_id: int):
        """Send a reply from the operator."""

        with self.client.post(
            f"/api/operator/reply/{conversation_id}",
            json={
                "message": "The operator is handling your request.",
            },
            headers=self.operator_headers,
            name="POST /api/operator/reply/{id}",
            catch_response=True,
        ) as response:
            if response.status_code != 200:
                response.failure(
                    f"Operator reply failed: {response.status_code}"
                )
                return False

        return True

    # ------------------------------------------------------------------
    # Journeys
    # ------------------------------------------------------------------

    @task(3)
    def conversation_journey(self):
        """
        Journey:
            create conversation
            -> send 5 messages
        """

        if not self.token:
            return

        conversation_id = self.create_conversation()

        if conversation_id is None:
            return

        for index in range(5):
            if not self.send_message(
                conversation_id,
                f"Load test message #{index + 1}",
            ):
                return

    @task(1)
    def escalation_journey(self):
        """
        Journey:
            create conversation
            -> explicitly ask AI to escalate
            -> wait for Celery/LLM escalation
            -> operator login
            -> assign conversation
            -> operator reply
        """

        if not self.token:
            return

        conversation_id = self.create_conversation()

        if conversation_id is None:
            return

        if not self.send_message(
            conversation_id,
            "Please escalate this conversation to a human operator.",
        ):
            return

        if not self.wait_for_escalation(conversation_id):
            return

        if self.operator_token is None:
            if not self.login_operator():
                return

        if not self.assign_conversation(conversation_id):
            return

        self.operator_reply(conversation_id)