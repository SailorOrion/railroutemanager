import logging

from train import Train

class Contract:
    def __init__(self, contract_id, contract_type, window):
        self.cid = contract_id
        self.ctype = contract_type
        self.route = []
        self.line_leaders = []
        self.trains = {}
        self.route_complete = False
        self.w = window

    def add_train(self, train):
        self.trains[train.tid] = train

    def del_train(self, tid):
        t = self.trains[tid]
        logging.debug(f"Removing train {tid}")
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

    def is_active(self):
        return self.number_of_trains() > 0

    def check_for_complete_route(self, length):
        handled_routes = {}
        logging.debug(f"Checking route completion: {len(self.trains)} trains")
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
                logging.debug(f"Closing route {self.cid} with lead train {self.line_leaders}: {self.route}")
                self.route_complete = True
                for train_id, train in self.trains.items():
                    train.finalize(self.end_of_route())
                return
            else:
                logging.debug("Incomplete route")
                handled_routes[tuple_list] = train_id

    def update_route(self, tid):
        longest_route_length = self.length_of_route()
        logging.debug(f"---- route update ----")
        logging.debug(f"Processing route update for {tid}:")
        logging.debug(f"  Current contract route: {len(self.route)}:{self.route}")
        longest_route_id = None
        for train_id, train in self.trains.items():
            if train.num_locations() > longest_route_length:
                longest_route_length = train.num_locations()
                longest_route_id = train.tid

        if longest_route_length > self.length_of_route():
            if self.route_complete:
                logging.debug(f"  Reopening route {self.cid}, Previously: {self.route}, new: {self.trains[longest_route_id].locations()}")
            self.route_complete = False
            self.route = self.trains[longest_route_id].locations()
            logging.debug(f"  New route: {self.cid}: {str(self.route)}")
            for train_id, train in self.trains.items():
                train.done = False
        if not self.route_complete:
            self.check_for_complete_route(longest_route_length)

    def repair_line_leader(self, train):
        logging.debug("Checking for route extension for {self.cid}")
        if train.tid in self.line_leaders and train.current_location() not in self.route:
            logging.debug(f"New station {train.current_location()} found for line leader, adding to existing route {self.route}")
            new_location, new_delay = train.current_location(), train.current_delay()
            self.line_leaders = [train.tid, train.tid]
            train.set_route(self.route)
            train.new_location(new_location, new_delay)
            logging.debug(f"New route for train: {train.locations()}")

    def new_location_for_train(self, tid, location, delay):
        logging.debug(f"==== Arrival for contract {self.cid} ====")
        if tid not in self.trains:
            self.trains[tid] = Train(tid, location, delay)
            logging.debug(f"New train: {tid} at {location}")
            if self.route_complete:
                self.repair_line_leader(self.trains[tid])
        else:
            self.trains[tid].new_location(location, delay)
            logging.debug(f"New location {location} for {tid}, train route {self.trains[tid].locations()}")
        self.update_route(tid)
        if self.route_complete:
            self.trains[tid].finalize(self.end_of_route())

        return self.trains[tid].is_done()

    def purge_trains(self):
        trains_to_delete = [tid for tid,t in self.trains.items() if t.done]
        logging.debug(f"Trains to remove: {trains_to_delete}")
        return [self.del_train(tid) for tid in trains_to_delete]

    def print_info(self):
        return f'{"*" if not self.route_complete else " "}{self.cid:>4}: {self.start_of_route()}--{len(self.route)}-->{self.end_of_route()}'

    def __str__(self):
        return f"Contract {self.cid}" + str(self.trains)

