from internal.helpers import *


class Order:

    def __init__(self, order_id, current_sys_time, order_value, delivery_time):
        self.order_id = order_id
        self.current_sys_time = current_sys_time
        self.order_value = order_value
        self.delivery_time = delivery_time
        self.est_toa = None
        self.priority = self.__calculate_order_priority()

    def __calculate_order_priority(self):
        return get_priority(self.order_value, self.current_sys_time)

    def create_order_string(self) -> str:
        return "Order " + str(self.order_id) + " has been created - ETA: " + str(self.est_toa)

    def delivered_order_string(self) -> str:
        return "Order " + str(self.order_id) + " has been delivered at time " + str(self.est_toa)

    def out_for_delivery(self, current_sys_time: int) -> bool:
        if self.est_toa - self.delivery_time <= current_sys_time:
            return True
        return False
