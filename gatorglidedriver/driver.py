from collections import deque

from internal.avlimpl.avltree import AvlTree
from internal.constants import BRANCH_PRIORITY
from internal.order.order import Order


class Driver:
    def __init__(self):
        self.priority_avl_tree = AvlTree(BRANCH_PRIORITY)

    def print_order(self, order_id: int):
        # print information about the order with orderId = order_id
        # output format: [orderId, currentSystemTime, orderValue, deliveryTime, ETA]
        order_info = self.__get_order_info(order_id)
        if order_info is not None:
            print(self.get_order_info_helper(order_info))

    def print_range(self, time1: int, time2: int):
        # prints order_ids of all the orders that will be delivered within the given times (including both times)
        # these orders include only UNDELIVERED orders. The format is as follows:
        # if orders exist [orderId1, orderId2, .........], There are no orders in that time period if none

        # search in the eta tree and get the order ids which lie within this time frame
        order_list = self.eta_searcher(time1, time2)
        sorted_orders = sorted(order_list, key=lambda sorted_order: sorted_order.est_toa)
        if len(sorted_orders) == 0:
            print("There are no orders in that time period")
        else:
            ans_str = "["
            for i, order in enumerate(sorted_orders):
                if i == len(sorted_orders) - 1:
                    ans_str += str(order.order_id)
                else:
                    ans_str += str(order.order_id) + ","
            ans_str += "]"
            print(ans_str)

    def get_rank_of(self, order_id: int) -> int:
        # prints how many orders will be delivered before it in the following format:
        # Order {orderId} will be delivered after {numberOfOrders} orders
        order_info = self.__get_order_info(order_id)
        if order_info is None:
            return 0
        order_list = self.get_rank_order_helper(order_info.est_toa)
        print("Order {} will be delivered after {} orders".format(order_id, len(order_list)))
        return len(order_list)

    def create_order(self, order_id: int, current_sys_time: int, order_value: int, delivery_time: int):
        # creates the order, prints the ETA, and also prints which previously unfulfilled orders  been delivered
        # along with their delivery times. Output format is as follows:
        # Order {orderId} has been created - ETA: {ETA}
        # Updated ETAs: [orderId1: ETA, orderId2: ETA,.........] if any ETAs have been updated
        # Order {orderId} has been delivered at time {ETA} for all such orders if they exist, each in a new line

        # we first get the current system time which is used to determine which orders have been finished
        # nodes which have eta <= current system time and delete these nodes
        drone_order_id = None
        delivered_orders = self.__get_delivered_orders(current_sys_time)
        # we then find the order which is supposed to be delivered before the one which was created now
        if self.priority_avl_tree.root is None:
            order = Order(order_id, current_sys_time, order_value, delivery_time)
            order.est_toa = current_sys_time + order.delivery_time
            self.priority_avl_tree.insert(order)
            print(order.create_order_string())
        else:
            order = Order(order_id, current_sys_time, order_value, delivery_time)
            next_best_priority_order = self.__get_previous_order(order)
            if next_best_priority_order is None:
                # this is the highest priority order
                # we just add the system time and delivery time if the drone is not in use
                # first check if the drone is in use by a particular order
                drone_order = self.__drone_in_use_order(current_sys_time)
                if drone_order is None:
                    # drone is not in use at the moment, so we can send it out to get this order done
                    order.est_toa = current_sys_time + order.delivery_time
                else:
                    # when the drone comes back i.e. at time (drone_order.est_toa + drone_order.delivery_time)
                    # we schedule it to deliver the created order as it is the most important at the moment
                    order.est_toa = drone_order.est_toa + drone_order.delivery_time + order.delivery_time
                    drone_order_id = drone_order.order_id
            else:
                # we schedule it after the inorder predecessor order is completed
                order.est_toa = (next_best_priority_order.est_toa + next_best_priority_order.delivery_time
                                 + order.delivery_time)

            self.priority_avl_tree.insert(order)
            print(order.create_order_string())

        for delivered_order in delivered_orders:
            self.priority_avl_tree.delete_node(delivered_order, False)
        # we now have to update the lower priority orders
        updated_orders = self.__update_lower_priority_orders(order, drone_order_id)
        updated_orders = self.sort_list_eta(updated_orders)
        if len(updated_orders) > 0:
            print(self.updated_orders_string(updated_orders))

        delivered_orders = self.sort_list_eta(delivered_orders)
        for delivered_order in delivered_orders:
            print(delivered_order.delivered_order_string())

    def cancel_order(self, order_id: int, current_sys_time: int):
        # cancels the order and updates the ETA of all the orders with lower priority
        # output format:
        # Order {orderId} has been canceled
        # Updated ETAs: [orderId1: ETA, orderId2: ETA, .........] if any ETAs have been updated
        # or
        # Cannot cancel. Order {orderId} has already been delivered
        # if the order is out for delivery or is already delivered
        delivered_orders = self.__get_delivered_orders(current_sys_time)

        if self.__order_has_been_delivered(order_id, current_sys_time):
            print("Cannot cancel. " + self.__order_already_delivered_string(order_id))
        else:
            # when we cancel an order, a round trip is cancelled
            # whose value is 2 * order.delivery time
            order = self.__get_order_info(order_id)
            # deleting the order from the priority tree
            self.priority_avl_tree.delete_node(order, False)
            print(self.__cancelled_order_string(order))
            # updating the eta of the lower priority orders
            updated_orders = self.__cancel_order_helper(order)
            updated_orders = self.sort_list_eta(updated_orders)
            if len(updated_orders) > 0:
                print(self.updated_orders_string(updated_orders))

        delivered_orders = self.sort_list_eta(delivered_orders)
        for delivered_order in delivered_orders:
            self.priority_avl_tree.delete_node(delivered_order, False)
            print(delivered_order.delivered_order_string())

    def update_time(self, order_id: int, current_sys_time: int, new_delivery_time: int):
        # takes the current system time, order_id and the new delivery time. It updates the ETAs of all the orders with
        # lower priority
        # Output format: Updated ETAs: [orderId1: ETA, orderId2: ETA, .........] if any ETAs have been updated
        # or
        # Cannot update. Order {orderId} has already been delivered if the order is out for delivery or is already
        # delivered
        delivered_orders = self.__get_delivered_orders(current_sys_time)
        if self.__order_has_been_delivered(order_id, current_sys_time):
            print("Cannot update. " + self.__order_already_delivered_string(order_id))
        else:
            order = self.__get_order_info(order_id)
            old_delivery_time = order.delivery_time
            updated_orders = self.__update_time_helper(order, new_delivery_time, old_delivery_time, order.est_toa)
            updated_orders = self.sort_list_eta(updated_orders)
            if len(updated_orders) > 0:
                print(self.updated_orders_string(updated_orders))
        delivered_orders = self.sort_list_eta(delivered_orders)
        for delivered_order in delivered_orders:
            self.priority_avl_tree.delete_node(delivered_order, False)
            print(delivered_order.delivered_order_string())

    def quit_gator_glide(self):
        # have to deliver the remaining orders
        remaining_orders = self.__quit_helper()
        remaining_orders = self.sort_list_eta(remaining_orders)
        for remaining_order in remaining_orders:
            print(remaining_order.delivered_order_string())
        # can clean up the program connections and io ops after this

    def __quit_helper(self):
        node = self.priority_avl_tree.root
        remaining_orders = []

        if node is None:
            return remaining_orders

        queue = deque()
        queue.append(node)

        while len(queue) > 0:
            node = queue.popleft()

            for key in node.order_info.keys():
                order = node.order_info[key]
                remaining_orders.append(order)

            if node.left is not None:
                queue.append(node.left)
            if node.right is not None:
                queue.append(node.right)

        return remaining_orders

    def __update_time_helper(self, check_order: Order, new_delivery_time: int, old_delivery_time: int, old_eta: int):
        node = self.priority_avl_tree.root
        updated_orders = []
        if node is None:
            return updated_orders
        queue = deque()
        queue.append(node)

        while len(queue) > 0:
            node = queue.popleft()

            for key in node.order_info.keys():
                if key == check_order.order_id:
                    updated_orders.append(node.order_info[key])
                    node.order_info[key].delivery_time = new_delivery_time
                    node.order_info[key].est_toa = node.order_info[key].est_toa - old_delivery_time + new_delivery_time
                elif node.order_info[key].est_toa > old_eta:
                    updated_orders.append(node.order_info[key])
                    node.order_info[key].est_toa = (node.order_info[key].est_toa
                                                    - (2 * old_delivery_time)
                                                    + (2 * new_delivery_time))
            if node.left is not None:
                queue.append(node.left)
            if node.right is not None:
                queue.append(node.right)
        return updated_orders

    @staticmethod
    def __order_already_delivered_string(order_id: int):
        return "Order " + str(order_id) + " has already been delivered"

    @staticmethod
    def __cancelled_order_string(order: Order) -> str:
        return "Order " + str(order.order_id) + " has been canceled"

    @staticmethod
    def get_order_info_helper(order_details: Order) -> str:
        return ("[" + str(order_details.order_id)
                + ", " + str(order_details.current_sys_time)
                + ", " + str(order_details.order_value)
                + ", " + str(order_details.delivery_time) + ", "
                + str(order_details.est_toa)
                + "]")

    @staticmethod
    def sort_list_eta(order_list: list[Order]):
        sorted_order_list = sorted(order_list, key=lambda sort_order: sort_order.est_toa)
        return sorted_order_list

    def eta_searcher(self, time1: int, time2: int) -> list[Order] | None:
        node = self.priority_avl_tree.root
        order_list = []

        if node is None:
            return None

        queue = deque()
        queue.append(node)

        while len(queue) > 0:
            node = queue.popleft()
            order_ids_present = node.order_info.keys()
            for order_id in order_ids_present:
                if time1 <= node.order_info[order_id].est_toa <= time2:
                    order_list.append(node.order_info[order_id])
            if node.left is not None:
                queue.append(node.left)
            if node.right is not None:
                queue.append(node.right)

        return order_list

    def get_rank_order_helper(self, eta: int) -> list[int]:
        node = self.priority_avl_tree.root
        if node is None:
            return []

        order_list = []
        queue = deque()
        queue.append(node)

        while len(queue) > 0:
            node = queue.popleft()
            for key in node.order_info.keys():
                if node.order_info[key].est_toa < eta:
                    order_list.append(key)
            if node.left is not None:
                queue.append(node.left)
            if node.right is not None:
                queue.append(node.right)
        return order_list

    def __get_delivered_orders(self, current_sys_time: int) -> list[Order]:
        # searches in avl tree for nodes with eta <= current_sys_time
        node = self.priority_avl_tree.root
        if node is None:
            return []

        delivered_orders = []
        queue = deque()
        queue.append(node)

        while len(queue) > 0:
            node = queue.popleft()
            for key in node.order_info.keys():
                if node.order_info[key].est_toa <= current_sys_time:
                    delivered_orders.append(node.order_info[key])
            if node.left is not None:
                queue.append(node.left)
            if node.right is not None:
                queue.append(node.right)
        return delivered_orders

    def __get_previous_order(self, check_order: Order) -> Order | None:
        previous_order = None
        node = self.priority_avl_tree.root

        queue = deque()
        queue.append(node)

        while len(queue) > 0:
            popped_node = queue.popleft()

            if popped_node.val >= check_order.priority:
                for key in popped_node.order_info.keys():
                    order = popped_node.order_info[key]
                    if previous_order is None:
                        previous_order = order
                    elif previous_order is not None and previous_order.est_toa < order.est_toa:
                        previous_order = order
            if popped_node.left is not None:
                queue.append(popped_node.left)
            if popped_node.right is not None:
                queue.append(popped_node.right)

        return previous_order

    def __drone_in_use_order(self, current_sys_time: int) -> Order | None:

        node = self.priority_avl_tree.root

        queue = deque()
        queue.append(node)

        while len(queue) > 0:
            popped_node = queue.popleft()

            for key in popped_node.order_info.keys():
                order = popped_node.order_info[key]
                if order.est_toa - order.delivery_time < current_sys_time:
                    return order
            if popped_node.left is not None:
                queue.append(popped_node.left)
            if popped_node.right is not None:
                queue.append(popped_node.right)
        return None

    def __update_lower_priority_orders(self, created_order: Order, drone_order_id: int) -> list[Order]:
        node = self.priority_avl_tree.root

        if node is None:
            return []

        queue = deque()
        queue.append(node)

        updated_orders = []

        while len(queue) > 0:
            node = queue.popleft()

            if node.val < created_order.priority:
                for key in node.order_info.keys():
                    if key != drone_order_id:
                        order = node.order_info[key]
                        order.est_toa += (2 * created_order.delivery_time)
                        updated_orders.append(order)
            if node.left is not None:
                queue.append(node.left)
            if node.right is not None:
                queue.append(node.right)
        return updated_orders

    @staticmethod
    def updated_orders_string(updated_orders: list[Order]) -> str:
        updated_str = "Updated ETAs: ["
        for i, updated_order in enumerate(updated_orders):
            if i == len(updated_orders) - 1:
                updated_str += (str(updated_order.order_id) + ":" + str(updated_order.est_toa))
            else:
                updated_str += (str(updated_order.order_id) + ":" + str(updated_order.est_toa) + ",")
        updated_str += "]"
        return updated_str

    def __get_order_info(self, order_id: int) -> Order | None:
        node = self.priority_avl_tree.root
        if node is None:
            return None

        queue = deque()
        queue.append(node)

        while len(queue) > 0:

            node = queue.popleft()
            if node.order_exists_id(order_id):
                return node.order_info[order_id]
            if node.left is not None:
                queue.append(node.left)
            if node.right is not None:
                queue.append(node.right)
        return None

    def __order_has_been_delivered(self, order_id: int, current_sys_time: int) -> bool:
        order = self.__get_order_info(order_id)
        if order is None:
            return True
        else:
            if order.out_for_delivery(current_sys_time):
                return True
            else:
                return False

    def __cancel_order_helper(self, order: Order) -> list[Order]:
        node = self.priority_avl_tree.root
        if node is None:
            return []
        reduce_eta = 2 * order.delivery_time
        updated_order_list = []
        queue = deque()
        queue.append(node)

        while len(queue) > 0:
            node = queue.popleft()

            for key in node.order_info.keys():
                if node.order_info[key].est_toa > order.est_toa:
                    updated_order_list.append(node.order_info[key])
                    node.order_info[key].est_toa -= reduce_eta
            if node.left is not None:
                queue.append(node.left)
            if node.right is not None:
                queue.append(node.right)

        return updated_order_list
