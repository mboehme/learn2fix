import heapq

import time

from learner import NoFormulaFound


class ParameterFrontier(object):
    def __init__(self, w_k, w_h):
        self.c = lambda k, h: w_k * k + w_h * h
        self.pq = []
        self.tried = set()

    def push(self, k, h):
        if (k, h) not in self.tried:
            heapq.heappush(self.pq, (self.c(k, h), k, h))
            self.tried.add((k, h))

    def pop(self):
        c, k, h = heapq.heappop(self.pq)
        return k, h


def learn_bottom_up(data, labels, learn_f, w_k, w_h, init_k=1, init_h=0, max_k=None, max_h=None):
    """
    Learns a CNF(k, h) SMT formula phi using the learner encapsulated in init_learner such that
    C(k, h) = w_k * k + w_h * h is minimal.
    :param data: List of tuples of assignments and labels
    :param labels: Array of labels
    :param learn_f: Function called with data, k and h: learn_f(data, k, h)
    :param w_k: The weight assigned to k
    :param w_h: The weight assigned to h
    :param init_k:  The minimal value for k
    :param init_h:  The minimal value for h
    :param max_k:   The maximal value for k
    :param max_h:   The maximal value for h
    :return: A tuple containing: 1) the CNF(k, h) formula phi with minimal complexity C(k, h); 2) k; and 3) h
    """
    solution = None
    frontier = ParameterFrontier(w_k, w_h)
    frontier.push(init_k, init_h)
    i = 0
    while solution is None:
        i += 1
        k, h = frontier.pop()
        # print("Attempting to solve with k={} and h={}".format(k, h))
        start = time.time()
        try:
            solution = learn_f(data, labels, i, k, h)
            # print("Found solution after {:.2f}s".format(time.time() - start))
        except NoFormulaFound as e:
            data = e.data
            labels = e.labels
        if max_k is None or k + 1 <= max_k:
            frontier.push(k + 1, h)
        if max_h is None or h + 1 <= max_h:
            frontier.push(k, h + 1)
    return solution, k, h
