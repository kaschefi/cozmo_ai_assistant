import enum
import time
import threading
from typing import List, Dict, Any, Optional, Callable


class NodeStatus(enum.Enum):
    SUCCESS = "SUCCESS"
    FAILURE = "FAILURE"
    RUNNING = "RUNNING"


class Blackboard:
    """
    Thread-safe key-value store shared across behavior tree nodes
    for runtime state, target memory, and blackboard variables.
    """
    def __init__(self):
        self._lock = threading.Lock()
        self._data: Dict[str, Any] = {}

    def get(self, key: str, default: Any = None) -> Any:
        with self._lock:
            return self._data.get(key, default)

    def set(self, key: str, value: Any):
        with self._lock:
            self._data[key] = value

    def clear(self):
        with self._lock:
            self._data.clear()

    def snapshot(self) -> Dict[str, Any]:
        with self._lock:
            return dict(self._data)


class Node:
    """
    Abstract Base Class for all Behavior Tree Nodes.
    """
    def __init__(self, name: str):
        self.name = name
        self.status = NodeStatus.FAILURE

    def tick(self, blackboard: Blackboard) -> NodeStatus:
        raise NotImplementedError("Subclasses must implement tick()")

    def reset(self):
        self.status = NodeStatus.FAILURE

    def cancel(self):
        """Called when this node is preempted by a higher priority branch."""
        self.reset()

    def __repr__(self):
        return f"{self.__class__.__name__}(name='{self.name}', status={self.status.value})"


class Selector(Node):
    """
    Fallback / Selector Composite Node.
    Ticks children sequentially from left to right.
    - If a child returns RUNNING: returns RUNNING and cancels any subsequent children.
    - If a child returns SUCCESS: returns SUCCESS.
    - If all children return FAILURE: returns FAILURE.
    """
    def __init__(self, name: str, children: Optional[List[Node]] = None):
        super().__init__(name)
        self.children: List[Node] = children or []
        self._running_child_idx: Optional[int] = None

    def add_child(self, child: Node):
        self.children.append(child)

    def tick(self, blackboard: Blackboard) -> NodeStatus:
        for idx, child in enumerate(self.children):
            # If we were previously running a lower priority child, and now a higher one succeeds/runs, cancel the old one
            if self._running_child_idx is not None and idx < self._running_child_idx:
                self.children[self._running_child_idx].cancel()
                self._running_child_idx = None

            status = child.tick(blackboard)

            if status == NodeStatus.RUNNING:
                self._running_child_idx = idx
                self.status = NodeStatus.RUNNING
                return NodeStatus.RUNNING

            if status == NodeStatus.SUCCESS:
                if self._running_child_idx is not None and self._running_child_idx != idx:
                    self.children[self._running_child_idx].cancel()
                self._running_child_idx = None
                self.status = NodeStatus.SUCCESS
                return NodeStatus.SUCCESS

            # If this child failed, reset it and try next child
            child.reset()

        self._running_child_idx = None
        self.status = NodeStatus.FAILURE
        return NodeStatus.FAILURE

    def reset(self):
        super().reset()
        self._running_child_idx = None
        for child in self.children:
            child.reset()

    def cancel(self):
        super().cancel()
        self._running_child_idx = None
        for child in self.children:
            child.cancel()


class Sequence(Node):
    """
    Sequence Composite Node.
    Ticks children sequentially from left to right.
    - If a child returns RUNNING: returns RUNNING (resumes here next tick).
    - If a child returns FAILURE: returns FAILURE immediately.
    - If all children return SUCCESS: returns SUCCESS.
    """
    def __init__(self, name: str, children: Optional[List[Node]] = None):
        super().__init__(name)
        self.children: List[Node] = children or []
        self._curr_child_idx: int = 0

    def add_child(self, child: Node):
        self.children.append(child)

    def tick(self, blackboard: Blackboard) -> NodeStatus:
        while self._curr_child_idx < len(self.children):
            child = self.children[self._curr_child_idx]
            status = child.tick(blackboard)

            if status == NodeStatus.RUNNING:
                self.status = NodeStatus.RUNNING
                return NodeStatus.RUNNING

            if status == NodeStatus.FAILURE:
                self.reset()
                self.status = NodeStatus.FAILURE
                return NodeStatus.FAILURE

            # Child returned SUCCESS, advance to next
            child.reset()
            self._curr_child_idx += 1

        self.reset()
        self.status = NodeStatus.SUCCESS
        return NodeStatus.SUCCESS

    def reset(self):
        super().reset()
        self._curr_child_idx = 0
        for child in self.children:
            child.reset()

    def cancel(self):
        super().cancel()
        self._curr_child_idx = 0
        for child in self.children:
            child.cancel()


class ActionNode(Node):
    """
    Leaf node that executes an action callable.
    Action callable must accept (blackboard: Blackboard) and return NodeStatus or bool.
    """
    def __init__(self, name: str, action_fn: Callable[[Blackboard], Any], on_cancel_fn: Optional[Callable[[], None]] = None):
        super().__init__(name)
        self.action_fn = action_fn
        self.on_cancel_fn = on_cancel_fn

    def tick(self, blackboard: Blackboard) -> NodeStatus:
        res = self.action_fn(blackboard)
        if isinstance(res, NodeStatus):
            self.status = res
        elif isinstance(res, bool):
            self.status = NodeStatus.SUCCESS if res else NodeStatus.FAILURE
        else:
            self.status = NodeStatus.SUCCESS
        return self.status

    def cancel(self):
        super().cancel()
        if self.on_cancel_fn:
            try:
                self.on_cancel_fn()
            except Exception:
                pass


class ConditionNode(Node):
    """
    Leaf node that evaluates a boolean condition function.
    Returns SUCCESS if true, FAILURE if false. Never returns RUNNING.
    """
    def __init__(self, name: str, condition_fn: Callable[[Blackboard], bool]):
        super().__init__(name)
        self.condition_fn = condition_fn

    def tick(self, blackboard: Blackboard) -> NodeStatus:
        try:
            passed = bool(self.condition_fn(blackboard))
            self.status = NodeStatus.SUCCESS if passed else NodeStatus.FAILURE
        except Exception:
            self.status = NodeStatus.FAILURE
        return self.status
