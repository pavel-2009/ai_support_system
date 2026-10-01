import gevent
import os
import time
from uuid import uuid4

from locust import FastHttpUser, between, task
from locust.exception import StopUser


class AuthenticatedUser(FastHttpUser):
    """Shared authentication and customer conversation helpers."""

    password = os.getenv("LOCUST_USER_PASSWORD", "LocustPass123!")
    ai_timeout = int(os.getenv("LOCUST_AI_TIMEOUT", "90"))
    poll_interval = float(os.getenv("LOCUST_POLL_INTERVAL", "1"))

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

            conversation_id = response.json().get("id")
            if conversation_id is None:
                response.failure("missing conversation id")
                return None

            return conversation_id

    def send_message(self, conversation_id: int, content: str) -> int | None:
        """Create one user message and return its database id."""
        idempotency_key = str(uuid4())

        with self.client.post(
            f"/api/conversations/{conversation_id}/messages",
            json={"content": content},
            headers={
                **self.headers,
                "Idempotency-Key": idempotency_key,
            },
            name="POST /api/conversations/{id}/messages",
            catch_response=True,
        ) as response:
            if response.status_code != 201:
                response.failure(f"send message: {response.status_code}")
                return None

            message_id = response.json().get("id")
            if message_id is None:
                response.failure("missing message id")
                return None

            return message_id

    def get_conversation_status(self, conversation_id: int) -> str | None:
        with self.client.get(
            f"/api/conversations/{conversation_id}",
            headers=self.headers,
            name="GET /api/conversations/{id}",
            catch_response=True,
        ) as response:
            if response.status_code != 200:
                response.failure(f"status check: {response.status_code}")
                return None

            return response.json().get("status")

    def get_messages(self, conversation_id: int) -> list[dict]:
        with self.client.get(
            f"/api/conversations/{conversation_id}/messages",
            headers=self.headers,
            name="GET /api/conversations/{id}/messages",
            catch_response=True,
        ) as response:
            if response.status_code != 200:
                response.failure(f"get messages: {response.status_code}")
                return []

            payload = response.json()
            if not isinstance(payload, list):
                response.failure("messages response is not a list")
                return []

            return payload

    def wait_for_ai_turn(self, conversation_id: int, user_message_id: int) -> str | None:
        """
        Wait for the asynchronous AI pipeline to finish.

        A user may send the next message only after the current turn reaches
        OPEN or ESCALATED. PENDING_AI is intentionally treated as an
        intermediate state, never as a state in which we send another message.

        Returns:
            "open"      -> AI answered and the conversation can continue.
            "escalated" -> AI pipeline escalated the conversation; no more
                           customer messages are sent in this journey.
            None        -> timeout or invalid terminal state.
        """
        started_at = time.perf_counter()
        deadline = started_at + self.ai_timeout

        while time.monotonic() < deadline:
            conversation_status = self.get_conversation_status(conversation_id)

            if conversation_status == "open":
                messages = self.get_messages(conversation_id)
                ai_messages = [
                    message
                    for message in messages
                    if message.get("conversation_id") == conversation_id
                    and message.get("sender_type") == "ai"
                    and message.get("id", 0) > user_message_id
                ]

                if ai_messages:
                    self.record_flow_wait(
                        "AI turn",
                        time.perf_counter() - started_at,
                        conversation_id,
                    )
                    return "open"

            elif conversation_status == "escalated":
                self.record_flow_wait(
                    "AI turn / escalation",
                    time.perf_counter() - started_at,
                    conversation_id,
                )
                return "escalated"

            elif conversation_status == "closed":
                self.record_flow_wait(
                    "AI turn",
                    time.perf_counter() - started_at,
                    conversation_id,
                    exception=RuntimeError("conversation closed while waiting for AI"),
                )
                return None

            time.sleep(self.poll_interval)

        self.record_flow_wait(
            "AI turn",
            time.perf_counter() - started_at,
            conversation_id,
            exception=TimeoutError(
                f"AI did not finish within {self.ai_timeout}s"
            ),
        )
        return None

    def record_flow_wait(
        self,
        name: str,
        duration: float,
        conversation_id: int,
        exception: Exception | None = None,
    ) -> None:
        self.environment.events.request.fire(
            request_type="FLOW",
            name=name,
            response_time=duration * 1000,
            response_length=0,
            response=None,
            context={"conversation_id": conversation_id},
            exception=exception,
        )


class ApiUser(AuthenticatedUser):
    """Realistic customer journeys."""

    weight = 10
    wait_time = between(1, 3)

    def on_start(self):
        self.email = f"locust_{uuid4().hex}@example.com"
        self.nickname = f"locust_{uuid4().hex[:16]}"
        self.token = None

        if not self.register_and_login():
            raise StopUser()

    def run_customer_turn(self, conversation_id: int, content: str) -> str | None:
        message_id = self.send_message(conversation_id, content)
        if message_id is None:
            return None

        return self.wait_for_ai_turn(conversation_id, message_id)

    @task(3)
    def conversation_journey(self):
        """
        Simulate one real conversation.

        The next user message is sent only after the previous AI turn has
        completed. This prevents the load test from manufacturing requests
        against PENDING_AI.
        """
        conversation_id = self.create_conversation()
        if conversation_id is None:
            return

        for index in range(5):
            result = self.run_customer_turn(
                conversation_id,
                f"Load test customer message #{index + 1}",
            )

            if result != "open":
                return

    @task(1)
    def escalation_journey(self):
        """Exercise an asynchronous escalation flow."""
        conversation_id = self.create_conversation()
        if conversation_id is None:
            return

        result = self.run_customer_turn(
            conversation_id,
            "Please escalate this conversation to a human operator.",
        )

        if result != "escalated":
            return

    @task(1)
    def read_and_close_journey(self):
        """Exercise reads and closing only after the AI turn is complete."""
        conversation_id = self.create_conversation()
        if conversation_id is None:
            return

        result = self.run_customer_turn(
            conversation_id,
            "Load test message for read and close journey.",
        )
        if result is None:
            return

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


class OperatorUser(AuthenticatedUser):
    """Operator journeys over conversations escalated by customer users."""

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
        self.get_queue()


class MessageRaceUser(AuthenticatedUser):
    """
    Dedicated concurrency test for the message creation race.

    Two requests intentionally target the same OPEN conversation at the same
    time. Exactly one message creation is expected to succeed; the other
    request is expected to be rejected after the conversation becomes
    PENDING_AI. The conversation is then allowed to complete normally.
    """

    weight = 1
    wait_time = between(5, 10)

    def on_start(self):
        self.email = f"locust_race_{uuid4().hex}@example.com"
        self.nickname = f"locust_race_{uuid4().hex[:16]}"
        self.token = None

        if not self.register_and_login():
            raise StopUser()

    def concurrent_send(self, conversation_id: int, result: dict, index: int) -> None:
        idempotency_key = str(uuid4())

        with self.client.post(
            f"/api/conversations/{conversation_id}/messages",
            json={"content": f"Concurrent race message #{index}"},
            headers={
                **self.headers,
                "Idempotency-Key": idempotency_key,
            },
            name="POST /api/conversations/{id}/messages [race]",
            catch_response=True,
        ) as response:
            result[index] = response.status_code

            if response.status_code == 201:
                response.success()
            elif response.status_code == 409:
                # 409 is expected for the loser of the same-conversation race.
                response.success()
            else:
                response.failure(f"race request: {response.status_code}")

    @task
    def concurrent_message_creation(self):
        conversation_id = self.create_conversation()
        if conversation_id is None:
            return

        results: dict[int, int] = {}
        jobs = [
            gevent.spawn(
                self.concurrent_send,
                conversation_id,
                results,
                index,
            )
            for index in (1, 2)
        ]
        gevent.joinall(jobs)

        success_count = sum(status == 201 for status in results.values())
        conflict_count = sum(status == 409 for status in results.values())

        if success_count != 1 or conflict_count != 1:
            self.environment.events.request.fire(
                request_type="FLOW",
                name="Concurrent message creation",
                response_time=0,
                response_length=0,
                response=None,
                context={"conversation_id": conversation_id},
                exception=RuntimeError(
                    f"expected exactly one 201 and one 409, got {results}"
                ),
            )
            return

        messages = self.get_messages(conversation_id)
        user_messages = [
            message
            for message in messages
            if message.get("sender_type") == "user"
        ]

        if len(user_messages) != 1:
            self.environment.events.request.fire(
                request_type="FLOW",
                name="Concurrent message creation",
                response_time=0,
                response_length=0,
                response=None,
                context={"conversation_id": conversation_id},
                exception=RuntimeError(
                    f"expected exactly one user message, got {len(user_messages)}"
                ),
            )
            return

        self.wait_for_ai_turn(
            conversation_id,
            user_messages[0]["id"],
        )
