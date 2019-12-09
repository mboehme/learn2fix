import time

import pysmt.shortcuts as smt
from pysmt.exceptions import InternalSolverError

from observe import observe
from learner import Learner, NoFormulaFound


class IncrementalObserver(observe.SpecializedObserver):
    def observe_initial(self, data, labels, initial_indices):
        raise NotImplementedError()

    def observe_iteration(self, data, labels, formula, new_active_indices, solving_time, selection_time):
        raise NotImplementedError()


class IncrementalLearner(Learner):
    def __init__(self, name, selection_strategy, smt_solver=True):
        """
        Initializes a new incremental learner
        :param str name: The learner name
        :param SelectionStrategy selection_strategy: The selection strategy
        """
        Learner.__init__(self, "incremental_{}".format(name))
        self.selection_strategy = selection_strategy
        self.observer = observe.DispatchObserver()
        self.smt_solver = smt_solver

    def add_observer(self, observer):
        self.observer.add_observer(observer)

    def learn(self, domain, data, labels, initial_indices=None):
        if self.smt_solver:
            with smt.Solver() as solver:
                data, formula, labels = self.incremental_loop(domain, data, labels, initial_indices, solver)
        else:
            data, formula, labels = self.incremental_loop(domain, data, labels, initial_indices, None)

        return data, labels, formula

    def incremental_loop(self, domain, data, labels, initial_indices, solver):
        active_indices = list(range(len(data))) if initial_indices is None else initial_indices
        all_active_indices = active_indices
        self.observer.observe("initial", data, labels, active_indices)
        formula = None
        while len(active_indices) > 0:
            solving_start = time.time()
            try:
                formula = self.learn_partial(solver, domain, data, labels, active_indices)
            except InternalSolverError:
                raise NoFormulaFound(data, labels)
            except Exception as e:
                if "Z3Exception" in str(type(e)):
                    raise NoFormulaFound(data, labels)
                else:
                    raise e

            solving_time = time.time() - solving_start

            selection_start = time.time()
            data, labels, new_active_indices = \
                self.selection_strategy.select_active(domain, data, labels, formula, all_active_indices)
            active_indices = list(new_active_indices)
            all_active_indices += active_indices
            selection_time = time.time() - selection_start
            self.observer.observe("iteration", data, labels, formula, active_indices, solving_time, selection_time)
        return data, formula, labels

    def learn_partial(self, solver, domain, data, labels, new_active_indices):
        raise NotImplementedError()
