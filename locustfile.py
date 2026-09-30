import os
import time
from uuid import uuid4

from locust import HttpUser, between, task
from locust.exception import StopUser


class ApiUser(HttpUser):
    """Regular customer journeys."""

    weight = 10
    wait_time = between(1, 3)

    password = os.getenv("LOCUST_USER_PASSWORD", "LocustPass123!")
    escalation_timeout = int(os.getenv("LOCUST_ESCALATION_TIMEOUT", "90"))

    def on_start(self):
        self.email = f"locust_{uuid4().hex}@example.com"
        self.nickname = f"locust_{uuid4().hex[:16]}"
        self.token = None

        if not self.register_and_login():
            raise StopUser()

    @property
    def headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self.token}"}

    def register_and_login(self) -> bool:
        with self.client.post(
            "/api/auth/register",
            json={
                "email": self.email,
                "nickname": self.nickname,
                "password": self.password,
            },
            name="POST /api/auth/register",
            catch_response=True,
        ) as response:
            if response.status_code != 201:
                response.failure(f"registration: {response.status_code}")
                return False

        with self.client.post(
            "/api/auth/login",
            json={"email": self.email, "password": self.password},
            name="POST /api/auth/login",
            catch_response=True,
        ) as response:
            if response.status_code != 200:
                response.failure(f"login: {response.status_code}")
                return False

            self.token = response.json().get("access_token")
            if not self.token:
                response.failure("missing access_token")
                return False

        return True

    def create_conversation(self) -> int | None:
        with self.client.post(
            "/api/conversations/",
            json={"priority": "medium", "channel": "api"},
            headers=self.headers,
            name="POST /api/conversations/",
            catch_response=True,
        ) as response:
            if response.status_code != 201:
                response.failure(f"create conversation: {response.status_code}")
                return None

            conversation_id = response.json().get("id")
            if conversation_id is None:
                response.failure("missing conversation id")
                return None

            return conversation_id

    def send_message(self, conversation_id: int, content: str) -> bool:
        with self.client.post(
            f"/api/conversations/{conversation_id}/messages",
            json={"content": content},
            headers=self.headers,
            name="POST /api/conversations/{id}/messages",
            catch_response=True,
        ) as response:
            if response.status_code != 201:
                response.failure(f"send message: {response.status_code}")
                return False
        return True

    def wait_for_escalation(self, conversation_id: int) -> bool:
        deadline = time.monotonic() + self.escalation_timeout

        while time.monotonic() < deadline:
            with self.client.get(
                f"/api/conversations/{conversation_id}",
                headers=self.headers,
                name="GET /api/conversations/{id}",
                catch_response=True,
            ) as response:
                if response.status_code != 200:
                    response.failure(f"status check: {response.status_code}")
                elif response.json().get("status") == "escalated":
                    return True

            time.sleep(1)

        return False

    @task(3)
    def conversation_journey(self):
        """Create a conversation and send five customer messages."""

        conversation_id = self.create_conversation()
        if conversation_id is None:
            return

        for index in range(5):
            if not self.send_message(
                conversation_id,
                f"Load test customer message #{index + 1}",
            ):
                return

    @task(1)
    def escalation_journey(self):
        """Ask the AI for a human escalation and wait for the async escalation."""

        conversation_id = self.create_conversation()
        if conversation_id is None:
            return

        if not self.send_message(
            conversation_id,
            "Please escalate this conversation to a human operator.",
        ):
            return

        if not self.wait_for_escalation(conversation_id):
            self.environment.events.user_error.fire(
                user_instance=self,
                exception=RuntimeError(
                    f"Escalation timeout for conversation {conversation_id}"
                ),
            )

    @task(1)
    def read_and_close_journey(self):
        """Exercise conversation reads, message reads, cursor listing and close."""

        conversation_id = self.create_conversation()
        if conversation_id is None:
            return

        if not self.send_message(
            conversation_id,
            "Load test message for read and close journey.",
        ):
            return

        with self.client.get(
            f"/api/conversations/{conversation_id}/messages",
            headers=self.headers,
            name="GET /api/conversations/{id}/messages",
            catch_response=True,
        ) as response:
            if response.status_code != 200:
                response.failure(f"get messages: {response.status_code}")

        with self.client.get(
            f"/api/conversations/{conversation_id}",
            headers=self.headers,
            name="GET /api/conversations/{id}",
            catch_response=True,
        ) as response:
            if response.status_code != 200:
                response.failure(f"get conversation: {response.status_code}")

        with self.client.get(
            "/api/conversations/?limit=20",
            headers=self.headers,
            name="GET /api/conversations/",
            catch_response=True,
        ) as response:
            if response.status_code != 200:
                response.failure(f"list conversations: {response.status_code}")

        with self.client.post(
            f"/api/conversations/{conversation_id}/close",
            headers=self.headers,
            name="POST /api/conversations/{id}/close",
            catch_response=True,
        ) as response:
            if response.status_code != 200:
                response.failure(f"close conversation: {response.status_code}")


class OperatorUser(HttpUser):
    """Operator journeys over conversations escalated by ApiUser instances."""

    fixed_count = 1
    wait_time = between(1, 2)

    operator_email = os.getenv(
        "LOCUST_OPERATOR_EMAIL",
        "operator@example.com",
    )
    operator_password = os.getenv(
        "LOCUST_OPERATOR_PASSWORD",
        "OperatorPass123!",
    )

    def on_start(self):
        self.token = None
        if not self.login():
            raise StopUser()

    @property
    def headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self.token}"}

    def login(self) -> bool:
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
                response.failure(f"operator login: {response.status_code}")
                return False

            self.token = response.json().get("access_token")
            if not self.token:
                response.failure("missing operator access_token")
                return False

        return True

    def get_queue(self) -> list[dict]:
        with self.client.get(
            "/api/operator/queue",
            headers=self.headers,
            name="GET /api/operator/queue",
            catch_response=True,
        ) as response:
            if response.status_code != 200:
                response.failure(f"operator queue: {response.status_code}")
                return []
            return response.json()

    def assign(self, conversation_id: int) -> bool:
        with self.client.post(
            f"/api/operator/assign/{conversation_id}",
            headers=self.headers,
            name="POST /api/operator/assign/{id}",
            catch_response=True,
        ) as response:
            if response.status_code != 200:
                response.failure(f"assign: {response.status_code}")
                return False
        return True

    def reply(self, conversation_id: int) -> bool:
        with self.client.post(
            f"/api/operator/reply/{conversation_id}",
            json={"message": "The operator is handling your request."},
            headers=self.headers,
            name="POST /api/operator/reply/{id}",
            catch_response=True,
        ) as response:
            if response.status_code != 200:
                response.failure(f"operator reply: {response.status_code}")
                return False
        return True

    def close(self, conversation_id: int) -> bool:
        with self.client.post(
            f"/api/operator/close/{conversation_id}",
            headers=self.headers,
            name="POST /api/operator/close/{id}",
            catch_response=True,
        ) as response:
            if response.status_code != 200:
                response.failure(f"operator close: {response.status_code}")
                return False
        return True

    @task(5)
    def operator_queue_and_work_journey(self):
        """Poll the escalation queue, assign a conversation, reply and close it."""

        queue = self.get_queue()
        if not queue:
            return

        conversation_id = queue[0].get("id")
        if conversation_id is None:
            return

        if not self.assign(conversation_id):
            return

        if not self.reply(conversation_id):
            return

        self.close(conversation_id)

    @task(1)
    def operator_queue_read_journey(self):
        """Measure operator queue reads independently from conversation handling."""

        self.get_queue()
