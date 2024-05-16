from collections import deque


class UniqueDeque:
    def __init__(self, maxlen):
        self.deque = deque(maxlen=maxlen)
        self.items_set = set()  # This helps in checking for uniqueness efficiently

    def appendleft(self, item):
        if item not in self.items_set:
            if len(self.deque) >= self.deque.maxlen:
                # Remove the item that will be discarded from the set
                self.items_set.remove(self.deque.pop())
            self.deque.appendleft(item)
            self.items_set.add(item)
            return True
        else:
            return False

    def __iter__(self):
        """Make the deque iterable."""
        return iter(self.deque)


def __repr__(self):
    return str(self.deque)
