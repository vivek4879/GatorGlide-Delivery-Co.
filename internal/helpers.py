from internal.constants import *


def get_priority(order_value: int, order_creation_time: int) -> float:
    normalized_order_weight = order_value / 50
    priority = VALUEWEIGHT * normalized_order_weight - TIMEWEIGHT * order_creation_time
    # print(priority)
    return priority
