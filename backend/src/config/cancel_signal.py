"""
请求级取消信号管理
用于在 Agent 运行期间接收前端取消请求
"""
from threading import Lock, Event
from typing import Dict, Set

_lock = Lock()
_pending_requests: Dict[str, Event] = {}
_cancelled_ids: Set[str] = set()


def register_request(request_id: str) -> Event:
    """注册一个可取消的请求"""
    event = Event()
    with _lock:
        if request_id in _cancelled_ids:
            event.set()
        _pending_requests[request_id] = event
    return event


def cancel_request(request_id: str) -> bool:
    """取消指定请求"""
    with _lock:
        _cancelled_ids.add(request_id)
        event = _pending_requests.get(request_id)
    if event:
        event.set()
        return True
    return False


def clear_request(request_id: str) -> None:
    """清理请求"""
    with _lock:
        _pending_requests.pop(request_id, None)
        _cancelled_ids.discard(request_id)


def is_cancelled(request_id: str) -> bool:
    """检查请求是否已被取消"""
    with _lock:
        if request_id in _cancelled_ids:
            return True
    return False
