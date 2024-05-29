from collections import deque


class UniqueDeque:
    def __init__(self, max_length):
        self.deque = deque(maxlen=max_length)
        self.items_set = set()  # This helps in checking for uniqueness efficiently

    def append_left(self, item):
        if item not in self.items_set:
            if len(self.deque) >= self.deque.maxlen:
                # Remove the item that will be discarded from the set
                self.items_set.remove(self.deque.pop())
            self.deque.appendleft(item)
            self.items_set.add(item)
            return True
        else:
            return False

    def remove(self, item):
        if item not in self.items_set:
            return False
        else:
            self.items_set.remove(item)
            self.deque.remove(item)
            return True

    def __iter__(self):
        """Make the deque iterable."""
        return iter(self.deque)


def __repr__(self):
    return str(self.deque)
