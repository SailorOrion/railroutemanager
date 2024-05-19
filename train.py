from collections import namedtuple

Stop = namedtuple("Stop", ["location", "delay"])


class Train:
    def __init__(self, train_id, location, delay):
        self.tid = train_id
        self._locations = []
        self._locations.append(Stop(location, delay))
        self.done = False

    def __hash__(self):
        return hash(self.tid)

    def __eq__(self, other):
        return self.tid == other.tid

    def locations(self):
        return [L.location for L in self._locations]

    def stops(self):
        return self._locations

    def set_route(self, route):
        self._locations = []
        for location in route:
            self.new_location(location, -3.14)

    def new_location(self, location, delay):
        self._locations.append(Stop(location, delay))

    def num_locations(self):
        return len(self._locations)

    def current_location(self):
        return self._locations[-1].location

    def previous_location(self):
        return self._locations[-2].location

    def first_location(self):
        return self._locations[0].location

    def current_delay(self):
        return self._locations[-1].delay

    def print_info(self):
        if self.num_locations() == 1:
            return f"| {self.current_delay():4.0f} | {self.current_location()}->?"
        elif self.num_locations() == 2:
            return f"| {self.current_delay():4.0f} | {self.previous_location()}->{self.current_location()}"
        else:
            return f"| {self.current_delay():4.0f} | {self.first_location()}--->{self.previous_location()}->{self.current_location()}"

    def finalize(self, terminus):
        if self.current_location() == terminus:
            self.done = True

    def is_done(self):
        return self.done

    def __repr__(self):
        return f"{self.tid}: {self.current_location()}({self.num_locations()}: {self._locations})"
