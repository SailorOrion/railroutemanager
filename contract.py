from train import Train

class Contract:
    def __init__(self, contract_id, contract_type, window):
        self.cid = contract_id
        self.ctype = contract_type
        self.route = []
        self.route_source = None
        self.trains = {}
        self.route_complete = False
        self.w = window

    def add_train(self, train):
        self.trains[train.tid] = train

    def del_train(self, tid):
        t = self.trains[tid]
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

    def check_for_complete_route(self):
        handled_routes = {}
        self.w.update_debug(f"Checking route completion: {len(self.trains)}")
        for train_id, train in self.trains.items():
            tuple_list = tuple(train.locations())
            self.w.update_debug(f"{train_id}: {tuple_list}")
            if tuple_list in handled_routes:
                self.w.update_debug("Route complete!")
                #self.w.update_status(f"Closing route {self.cid}")
                self.route = train.locations()
                self.route_complete = True
                for train_id, train in self.trains.items():
                    train.finalize(self.end_of_route())
                return
            else:
                self.w.update_debug("Incomplete route")
                handled_routes[tuple_list] = True

    def update_route(self, tid):
        longest_route_length = self.length_of_route()
        self.w.update_debug(f"Processing {tid}: Current route length: {len(self.route)}")
        longest_route_id = None
        for train_id, train in self.trains.items():
            if train.num_locations() > longest_route_length:
                longest_route_length = train.num_locations()
                longest_route_id = train.tid

        self.w.update_debug(f"Processing {tid}: New route length: {longest_route_length}")
        if longest_route_length > self.length_of_route():
            self.w.update_debug(f"Processing {tid}: New route length: {self.trains[longest_route_id].num_locations()}, {longest_route_length}")
            self.route_complete = False
            self.route = self.trains[longest_route_id].locations()
            self.w.update_debug(f"Processing {tid}: {self.cid}: {str(self.route)}")
            for train_id, train in self.trains.items():
                train.done = False
        self.check_for_complete_route()

    def new_location_for_train(self, tid, location, delay):
        if tid not in self.trains:
            self.trains[tid] = Train(tid, location, delay)
            self.w.update_debug(f"New train: {tid} at {location}")
        else:
            self.trains[tid].new_location(location, delay)
            self.w.update_debug(f"New location {location} for {tid}")
        self.update_route(tid)
        if self.route_complete:
            self.trains[tid].finalize(self.end_of_route())

    def purge_trains(self):
        trains_to_delete = [tid for tid,t in self.trains.items() if t.done]
        return [self.del_train(tid) for tid in trains_to_delete]

    def print_info(self):
        return f'{"*" if not self.route_complete else " "}{self.cid:>4}: {self.start_of_route()}--{len(self.route)}-->{self.end_of_route()}'

    def __str__(self):
        return f"Contract {self.cid}" + str(self.trains)

