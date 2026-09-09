"""Класс для управления событиями в системе."""

import inspect
from typing import Any, Awaitable, Callable, Dict, List, Type, Union

from app.domain.events import DomainEvent


class EventBus:
    """Класс для управления событиями в системе"""

    def __init__(self):
        self._subscribers: Dict[
            Type[DomainEvent],
            List[Callable[[DomainEvent], Union[Any, Awaitable[Any]]]],
        ] = {}

    def subscribe(
        self,
        event_type: Type[DomainEvent],
        handler: Callable[[DomainEvent], Union[Any, Awaitable[Any]]],
    ) -> Callable[[DomainEvent], Union[Any, Awaitable[Any]]]:
        """Подписка на событие."""
        if event_type not in self._subscribers:
            self._subscribers[event_type] = []
        self._subscribers[event_type].append(handler)
        return handler

    def on_event(self, event_type: Type[DomainEvent]):
        """Декоратор для подписки обработчика на событие."""
        def decorator(handler: Callable[[DomainEvent], Union[Any, Awaitable[Any]]]):
            return self.subscribe(event_type, handler)

        return decorator

    def publish(self, event: DomainEvent):
        """Синхронно публикует событие.

        Для async-обработчиков используйте ``publish_async``.
        """
        event_type = type(event)
        if event_type in self._subscribers:
            for handler in self._subscribers[event_type]:
                result = handler(event)
                if inspect.isawaitable(result):
                    if inspect.iscoroutine(result):
                        result.close()
                    raise RuntimeError(
                        "Async event handler cannot be used with publish(); "
                        "use publish_async() instead"
                    )

    async def publish_async(self, event: DomainEvent):
        """Асинхронно публикует событие, поддерживая sync и async обработчики."""
        event_type = type(event)
        for handler in self._subscribers.get(event_type, []):
            result = handler(event)
            if inspect.isawaitable(result):
                await result


event_bus = EventBus()


def on_event(event_type: Type[DomainEvent], event_bus: EventBus):
    """Декоратор для подписки обработчика через переданный event bus."""
    return event_bus.on_event(event_type)
