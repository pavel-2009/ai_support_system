"""Unit-тесты для операторского роутера и celery-задачи LLM."""

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException

from app.models.user import UserRole
from app.routers.operator import conversation as operator_router


class TestOperatorRouter:
    @pytest.mark.asyncio
    async def test_get_conversation_queue_forbidden_for_regular_user(self):
        user = SimpleNamespace(id=1, role=UserRole.USER)

        with pytest.raises(HTTPException) as exc:
            await operator_router.get_conversation_queue(
                current_user=user,
                conversation_service=SimpleNamespace(get_active_queue=AsyncMock()),
            )

        assert exc.value.status_code == 403

    @pytest.mark.asyncio
    async def test_get_conversation_queue_returns_items_for_operator(self):
        user = SimpleNamespace(id=2, role=UserRole.OPERATOR)
        queue = [SimpleNamespace(id=10), SimpleNamespace(id=11)]
        service = SimpleNamespace(get_active_queue=AsyncMock(return_value=queue))

        result = await operator_router.get_conversation_queue(current_user=user, conversation_service=service)

        assert result == queue
        service.get_active_queue.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_get_conversation_queue_handles_unexpected_error(self):
        user = SimpleNamespace(id=2, role=UserRole.OPERATOR)
        service = SimpleNamespace(get_active_queue=AsyncMock(side_effect=RuntimeError("queue error")))

        with pytest.raises(HTTPException) as exc:
            await operator_router.get_conversation_queue(current_user=user, conversation_service=service)

        assert exc.value.status_code == 500

    @pytest.mark.asyncio
    async def test_assign_conversation_not_found_returns_404(self):
        user = SimpleNamespace(id=7, role=UserRole.OPERATOR)
        service = SimpleNamespace(assign_operator=AsyncMock(return_value=None))

        with pytest.raises(HTTPException) as exc:
            await operator_router.assign_conversation(77, current_user=user, conversation_service=service)

        assert exc.value.status_code == 404

    @pytest.mark.asyncio
    async def test_assign_conversation_handles_unexpected_error(self):
        user = SimpleNamespace(id=7, role=UserRole.OPERATOR)
        service = SimpleNamespace(assign_operator=AsyncMock(side_effect=RuntimeError("db down")))

        with pytest.raises(HTTPException) as exc:
            await operator_router.assign_conversation(77, current_user=user, conversation_service=service)

        assert exc.value.status_code == 500

    @pytest.mark.asyncio
    async def test_reply_to_conversation_returns_404_when_not_assigned(self):
        user = SimpleNamespace(id=3, role=UserRole.OPERATOR)
        message_service = SimpleNamespace(create_message=AsyncMock(return_value=None))

        with pytest.raises(HTTPException) as exc:
            await operator_router.reply_to_conversation(
                12,
                message="Ответ оператора",
                current_user=user,
                message_service=message_service,
            )

        assert exc.value.status_code == 404

    @pytest.mark.asyncio
    async def test_reply_to_conversation_success(self):
        user = SimpleNamespace(id=3, role=UserRole.OPERATOR)
        message_service = SimpleNamespace(
            create_message=AsyncMock(return_value=SimpleNamespace(id=100, content="ok"))
        )

        result = await operator_router.reply_to_conversation(
            12,
            message="Ответ оператора",
            current_user=user,
            message_service=message_service,
        )

        assert result.id == 100
        message_service.create_message.assert_awaited_once_with(
            12,
            sender_type="operator",
            sender_id=3,
            content="Ответ оператора",
        )

    @pytest.mark.asyncio
    async def test_operator_endpoints_forbidden_for_regular_user(self):
        user = SimpleNamespace(id=10, role=UserRole.USER)
        conv_service = SimpleNamespace(close=AsyncMock(), back_to_ai=AsyncMock(), assign_operator=AsyncMock())
        msg_service = SimpleNamespace(create_message=AsyncMock())

        with pytest.raises(HTTPException) as assign_exc:
            await operator_router.assign_conversation(1, current_user=user, conversation_service=conv_service)
        with pytest.raises(HTTPException) as reply_exc:
            await operator_router.reply_to_conversation(
                1, message="x", current_user=user, message_service=msg_service
            )
        with pytest.raises(HTTPException) as close_exc:
            await operator_router.close_conversation(1, current_user=user, conversation_service=conv_service)
        with pytest.raises(HTTPException) as back_exc:
            await operator_router.back_to_ai(1, current_user=user, conversation_service=conv_service)

        assert assign_exc.value.status_code == 403
        assert reply_exc.value.status_code == 403
        assert close_exc.value.status_code == 403
        assert back_exc.value.status_code == 403

    @pytest.mark.asyncio
    async def test_close_conversation_and_back_to_ai_success(self):
        user = SimpleNamespace(id=8, role=UserRole.ADMIN)
        service = SimpleNamespace(
            close=AsyncMock(return_value=True),
            back_to_ai=AsyncMock(return_value=SimpleNamespace(id=5, status=SimpleNamespace(value="open"))),
        )

        close_result = await operator_router.close_conversation(5, current_user=user, conversation_service=service)
        back_result = await operator_router.back_to_ai(5, current_user=user, conversation_service=service)

        assert close_result == {"detail": "Диалог успешно закрыт."}
        assert back_result == {"id": 5, "status": "open"}

    @pytest.mark.asyncio
    async def test_reply_close_back_to_ai_http_404_paths(self):
        user = SimpleNamespace(id=9, role=UserRole.OPERATOR)
        message_service = SimpleNamespace(create_message=AsyncMock(return_value=None))
        conversation_service = SimpleNamespace(
            close=AsyncMock(return_value=None),
            back_to_ai=AsyncMock(return_value=None),
        )

        with pytest.raises(HTTPException) as reply_exc:
            await operator_router.reply_to_conversation(
                55, message="x", current_user=user, message_service=message_service
            )
        with pytest.raises(HTTPException) as close_exc:
            await operator_router.close_conversation(55, current_user=user, conversation_service=conversation_service)
        with pytest.raises(HTTPException) as back_exc:
            await operator_router.back_to_ai(55, current_user=user, conversation_service=conversation_service)

        assert reply_exc.value.status_code == 404
        assert close_exc.value.status_code == 404
        assert back_exc.value.status_code == 404

    @pytest.mark.asyncio
    async def test_reply_close_back_to_ai_handle_unexpected_error(self):
        user = SimpleNamespace(id=9, role=UserRole.OPERATOR)
        message_service = SimpleNamespace(create_message=AsyncMock(side_effect=RuntimeError("msg error")))
        conversation_service = SimpleNamespace(
            close=AsyncMock(side_effect=RuntimeError("close error")),
            back_to_ai=AsyncMock(side_effect=RuntimeError("back error")),
        )

        with pytest.raises(HTTPException) as reply_exc:
            await operator_router.reply_to_conversation(
                55, message="x", current_user=user, message_service=message_service
            )
        with pytest.raises(HTTPException) as close_exc:
            await operator_router.close_conversation(55, current_user=user, conversation_service=conversation_service)
        with pytest.raises(HTTPException) as back_exc:
            await operator_router.back_to_ai(55, current_user=user, conversation_service=conversation_service)

        assert reply_exc.value.status_code == 500
        assert close_exc.value.status_code == 500
        assert back_exc.value.status_code == 500


class TestLLMTasks:
    @pytest.mark.asyncio
    async def test_process_async_creates_auto_reply_when_confident(self):
        fake_response = SimpleNamespace(answer="AI answer", confidence=0.95)

        session_ctx = MagicMock()
        session_ctx.__aenter__ = AsyncMock(return_value=SimpleNamespace())
        session_ctx.__aexit__ = AsyncMock(return_value=False)

        with patch("app.celery.tasks.llm_tasks.async_session", return_value=session_ctx):
            with patch("app.celery.tasks.llm_tasks.LLMService") as llm_service_cls:
                with patch("app.celery.tasks.llm_tasks.MessageService") as message_service_cls:
                    with patch("app.celery.tasks.llm_tasks.ConversationService") as conversation_service_cls:
                        llm_service = llm_service_cls.return_value
                        llm_service.generate_response = AsyncMock(return_value=fake_response)

                        message_service = message_service_cls.return_value
                        message_service.create_message = AsyncMock()

                        conversation_service = conversation_service_cls.return_value
                        conversation_service.update_conversation_status = AsyncMock()

                        from app.celery.tasks.llm_tasks import _process_llm_task_async

                        await _process_llm_task_async(conversation_id=42)

        message_service.create_message.assert_awaited_once()
        kwargs = message_service.create_message.await_args.kwargs
        assert kwargs["needs_review"] is False
        conversation_service.update_conversation_status.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_process_async_escalates_on_low_confidence(self):
        fake_response = SimpleNamespace(answer="Need operator", confidence=0.2)

        session_ctx = MagicMock()
        session_ctx.__aenter__ = AsyncMock(return_value=SimpleNamespace())
        session_ctx.__aexit__ = AsyncMock(return_value=False)

        with patch("app.celery.tasks.llm_tasks.async_session", return_value=session_ctx):
            with patch("app.celery.tasks.llm_tasks.LLMService") as llm_service_cls:
                with patch("app.celery.tasks.llm_tasks.MessageService") as message_service_cls:
                    with patch("app.celery.tasks.llm_tasks.ConversationService") as conversation_service_cls:
                        llm_service_cls.return_value.generate_response = AsyncMock(return_value=fake_response)

                        message_service = message_service_cls.return_value
                        message_service.create_message = AsyncMock()

                        conversation_service = conversation_service_cls.return_value
                        conversation_service.update_conversation_status = AsyncMock()

                        from app.celery.tasks.llm_tasks import _process_llm_task_async

                        await _process_llm_task_async(conversation_id=100)

        message_service.create_message.assert_not_awaited()
        conversation_service.update_conversation_status.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_process_async_creates_review_reply_on_mid_confidence(self):
        fake_response = SimpleNamespace(answer="Need review", confidence=0.7)

        session_ctx = MagicMock()
        session_ctx.__aenter__ = AsyncMock(return_value=SimpleNamespace())
        session_ctx.__aexit__ = AsyncMock(return_value=False)

        with patch("app.celery.tasks.llm_tasks.async_session", return_value=session_ctx):
            with patch("app.celery.tasks.llm_tasks.LLMService") as llm_service_cls:
                with patch("app.celery.tasks.llm_tasks.MessageService") as message_service_cls:
                    with patch("app.celery.tasks.llm_tasks.ConversationService") as conversation_service_cls:
                        llm_service_cls.return_value.generate_response = AsyncMock(return_value=fake_response)

                        message_service = message_service_cls.return_value
                        message_service.create_message = AsyncMock()

                        conversation_service = conversation_service_cls.return_value
                        conversation_service.update_conversation_status = AsyncMock()

                        from app.celery.tasks.llm_tasks import _process_llm_task_async

                        await _process_llm_task_async(conversation_id=777)

        kwargs = message_service.create_message.await_args.kwargs
        assert kwargs["needs_review"] is True
        conversation_service.update_conversation_status.assert_not_awaited()

    def test_process_llm_task_retries_on_exception(self):
        with patch("app.celery.tasks.llm_tasks.asyncio.run", side_effect=ValueError("boom")):
            from app.celery.tasks.llm_tasks import process_llm_task

            with patch.object(process_llm_task, "retry", side_effect=RuntimeError("retry called")) as retry_mock:
                with pytest.raises(RuntimeError, match="retry called"):
                    process_llm_task.run(1)

        retry_mock.assert_called_once()

    def test_process_llm_task_returns_ok(self):
        with patch("app.celery.tasks.llm_tasks.asyncio.run", return_value=None) as run_mock:
            from app.celery.tasks.llm_tasks import process_llm_task

            result = process_llm_task.run(5)

        assert result == "ok"
        run_mock.assert_called_once()
