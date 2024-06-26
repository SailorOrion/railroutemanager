import logging

from train import Train


class Contract:
    def __init__(self, contract_id, contract_type, window):
        self.cid = contract_id
        self.ctype = contract_type
        self.route = []
        self.line_leaders = []
        self.trains = {}
        self.completed_trains = {}
        self.route_complete = False
        self.w = window

    def add_train(self, train):
        self.trains[train.tid] = train

    def del_train(self, tid):
        t = self.trains[tid]
        logging.debug(f"Removing train {tid}")
        self.completed_trains[tid] = self.trains[tid]
        del self.trains[tid]
        return t

    def length_of_route(self):
        return len(self.route)

    def start_of_route(self):
        if self.length_of_route() > 0:
            return self.route[0]
        return "N/A"

    def end_of_route(self):
        if self.length_of_route() > 0:
            return self.route[-1]
        return "N/A"

    def number_of_trains(self):
        return len(self.trains)

    def is_active(self) -> bool:
        return self.number_of_trains() > 0

    def make_train_detail(self, train) -> list:
        elems = [None] * (len(self.route) + 1)
        elems[0] = (f'{train.tid:>8}', 0)
        logging.info(f'{train.tid}:{train.stops()}')
        start_of_route = self.route.index(train.first_location())
        # the +1 is for the title
        for idx, stop in enumerate(train.stops(), start=start_of_route + 1):
            delay = stop.delay
            color_pair = 0
            if delay >= 120:
                color_pair = 2
            elif delay >= 60:
                color_pair = 1
            elems[idx] = (f'{stop.delay:>8.0f}', color_pair)
        return elems

    def make_detail_view(self):
        rows = []
        title = "Station"
        title_row = [(f'{title:14}', 0)]
        title_row.extend([(f'{location[0:14]:14}', 0) for location in self.route])
        rows.append(title_row)
        for train in sorted(self.completed_trains.values(), key=lambda t: t.time_of_birth()):
            if train.tid not in self.trains:
                rows.append(self.make_train_detail(train))
        for train in sorted(self.trains.values(), key=lambda t: t.time_of_birth()):
            rows.append(self.make_train_detail(train))
        return f'Detail for contract {self.cid}', list(map(list, zip(*rows)))

    def check_for_complete_route(self, length) -> bool:
        handled_routes = {}
        logging.debug(f"Checking route completion: {len(self.trains)} trains: {[train.tid for train in self.trains.values()]}")
        for train_id, train in self.trains.items():
            logging.debug(f"  {train_id}: {train.locations()}")
            tuple_list = tuple(train.locations())
            if len(tuple_list) < length:
                logging.debug(f"Discarding {train_id}, since {len(tuple_list)} < {length}")
                continue
            if tuple_list in handled_routes:
                logging.debug(f"Leaders: {train_id} and {handled_routes[tuple_list]}")
                self.route = train.locations()
                self.line_leaders = [train_id, handled_routes[tuple_list]]
                logging.debug(f"Closing route {self.cid}: {self.route}")
                logging.info(f"Closing route {self.cid} \
                                with lead train {self.line_leaders}: {self.route}")
                self.route_complete = True
                for _, train_2 in self.trains.items():
                    train_2.finalize(self.end_of_route())
                return True
            else:
                logging.debug("Incomplete route")
                handled_routes[tuple_list] = train_id
        return False

    def update_route(self, tid) -> bool:
        longest_route_length = self.length_of_route()
        logging.debug("---- route update ----")
        logging.debug(f"Processing route update for {tid}:")
        logging.debug(f"  Current contract route: {len(self.route)}:{self.route}")
        longest_route_id = None
        for train_id, train in self.trains.items():
            if train.num_locations() > longest_route_length:
                longest_route_length = train.num_locations()
                longest_route_id = train.tid

        if longest_route_length > self.length_of_route():
            if self.route_complete:
                logging.debug(f"  Reopening route {self.cid}, previously: {self.route}, new: {self.trains[longest_route_id].locations()}")
            self.route_complete = False
            self.route = self.trains[longest_route_id].locations()
            logging.debug(f"  New route: {self.cid}: {str(self.route)}")
            for train_id, train in self.trains.items():
                train.done = False
        if not self.route_complete:
            return self.check_for_complete_route(longest_route_length)
        return False

    def repair_line_leader(self, train):
        logging.debug("Checking for route extension for {self.cid}")
        if train.tid in self.line_leaders and train.current_location() not in self.route:
            logging.debug(f"New station {train.current_location()} found for line leader, adding to existing route {self.route}")
            new_location, new_delay = train.current_location(), train.current_delay()
            self.line_leaders = [train.tid, train.tid]
            train.set_route(self.route)
            train.new_location(new_location, new_delay)
            logging.debug(f"New route for train: {train.locations()}")

    def new_location_for_train(self, tid, location, delay) -> bool:
        logging.debug(f"==== Arrival for contract {self.cid} ====")
        if tid not in self.trains:
            self.trains[tid] = Train(tid, location, delay)
            logging.debug(f"New train: {tid} at {location}")
            if self.route_complete:
                self.repair_line_leader(self.trains[tid])
                if self.length_of_route() == 1:
                    self.trains[tid].finalize(self.end_of_route())
        else:
            self.trains[tid].new_location(location, delay)
            logging.debug(f"{location} for {tid}, train route {self.trains[tid].locations()}")
            if self.route_complete:
                self.trains[tid].finalize(self.end_of_route())
        closed_route = self.update_route(tid)

        return closed_route

    def purge_trains(self) -> list:
        trains_to_delete = [tid for tid, t in self.trains.items() if t.done]
        logging.debug(f"Trains to remove: {trains_to_delete}")
        return [self.del_train(tid) for tid in trains_to_delete]

    def get_delay_info(self) -> str:
        delay_info = list("_" * 4)
        for tid, t in self.completed_trains.items():
            for stop in t.stops():
                if stop.delay > 120:
                    delay_info[0] = "!"
                elif stop.delay > 60:
                    delay_info[0] = "?"
                elif stop.delay < -120:
                    delay_info[1] = '*'
                elif stop.delay < -60:
                    delay_info[1] = '+'
        for tid, t in self.trains.items():
            for stop in t.stops():
                if stop.delay > 120:
                    delay_info[2] = "!"
                elif stop.delay > 60:
                    delay_info[2] = "?"
                elif stop.delay < -120:
                    delay_info[3] = '*'
                elif stop.delay < -60:
                    delay_info[3] = '+'
        return ''.join(delay_info)

    def print_info(self) -> str:
        return f'{"*" if not self.route_complete else " "}{self.get_delay_info()}{self.cid:>5}: {self.start_of_route()}--{len(self.route)}-->{self.end_of_route()}'

    def __str__(self) -> str:
        return f"Contract {self.cid}" + str(self.trains)
