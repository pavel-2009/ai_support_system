import gevent
import os
import time
from uuid import uuid4

from locust import FastHttpUser, between, task
from locust.exception import StopUser


class SupportUser(FastHttpUser):
    """Realistic customer flow: send a message and wait for AI before continuing."""

    wait_time = between(1, 3)
    ai_timeout = int(os.getenv("LOCUST_AI_TIMEOUT", "90"))
    poll_interval = float(os.getenv("LOCUST_POLL_INTERVAL", "1"))
    password = os.getenv("LOCUST_USER_PASSWORD", "LocustPass123!")

    def on_start(self):
        self.email = f"locust_{uuid4().hex}@example.com"
        self.nickname = f"locust_{uuid4().hex[:16]}"

        if not self.register_and_login():
            raise StopUser()

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
                response.failure(f"register: {response.status_code}")
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
            return bool(self.token)

    @property
    def headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self.token}"}

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
            return response.json().get("id")

    def send_message(self, conversation_id: int, content: str) -> int | None:
        with self.client.post(
            f"/api/conversations/{conversation_id}/messages",
            json={"content": content},
            headers={
                **self.headers,
                "Idempotency-Key": str(uuid4()),
            },
            name="POST /api/conversations/{id}/messages",
            catch_response=True,
        ) as response:
            if response.status_code != 201:
                response.failure(f"send message: {response.status_code}")
                return None
            return response.json().get("id")

    def conversation_status(self, conversation_id: int) -> str | None:
        with self.client.get(
            f"/api/conversations/{conversation_id}",
            headers=self.headers,
            name="GET /api/conversations/{id}",
            catch_response=True,
        ) as response:
            if response.status_code != 200:
                response.failure(f"get conversation: {response.status_code}")
                return None
            return response.json().get("status")

    def has_ai_response(self, conversation_id: int, user_message_id: int) -> bool:
        with self.client.get(
            f"/api/conversations/{conversation_id}/messages",
            headers=self.headers,
            name="GET /api/conversations/{id}/messages",
            catch_response=True,
        ) as response:
            if response.status_code != 200:
                response.failure(f"get messages: {response.status_code}")
                return False

            return any(
                message.get("sender_type") == "ai"
                and message.get("id", 0) > user_message_id
                for message in response.json()
            )

    def wait_for_ai(self, conversation_id: int, user_message_id: int) -> bool:
        deadline = time.monotonic() + self.ai_timeout

        while time.monotonic() < deadline:
            status = self.conversation_status(conversation_id)

            if status == "open" and self.has_ai_response(
                conversation_id,
                user_message_id,
            ):
                return True

            if status in {"escalated", "closed"}:
                return False

            time.sleep(self.poll_interval)

        return False

    @task
    def conversation(self):
        conversation_id = self.create_conversation()
        if conversation_id is None:
            return

        for index in range(5):
            message_id = self.send_message(
                conversation_id,
                f"Load test message #{index + 1}",
            )
            if message_id is None:
                return

            if not self.wait_for_ai(conversation_id, message_id):
                return


class MessageRaceUser(SupportUser):
    """Two simultaneous writes to one conversation; one must win."""

    weight = 0
    fixed_count = 0

    @task
    def race(self):
        conversation_id = self.create_conversation()
        if conversation_id is None:
            return

        results = {}

        def send(index: int):
            with self.client.post(
                f"/api/conversations/{conversation_id}/messages",
                json={"content": f"Race message #{index}"},
                headers={
                    **self.headers,
                    "Idempotency-Key": str(uuid4()),
                },
                name="POST /api/conversations/{id}/messages [race]",
                catch_response=True,
            ) as response:
                results[index] = response.status_code
                if response.status_code not in {201, 409}:
                    response.failure(f"race: {response.status_code}")

        jobs = [gevent.spawn(send, 1), gevent.spawn(send, 2)]
        gevent.joinall(jobs)

        if sorted(results.values()) != [201, 409]:
            self.environment.events.request.fire(
                request_type="FLOW",
                name="message race",
                response_time=0,
                response_length=0,
                response=None,
                exception=RuntimeError(f"unexpected race result: {results}"),
            )
