from __future__ import print_function

import numpy as np
import pysmt.shortcuts as smt
from pysmt.fnode import FNode
from pysmt.typing import REAL
from typing import Set, Tuple, List

from incremental_learner import IncrementalLearner
from pywmi import Domain


class KCnfSmtLearner(IncrementalLearner):
    def __init__(self, conjunction_count, half_space_count, selection_strategy, symmetries, allow_negations=True):
        IncrementalLearner.__init__(self, "cnf_smt", selection_strategy)
        self.conjunction_count = conjunction_count
        self.half_space_count = half_space_count
        self.symmetries = symmetries
        self.allow_negations = allow_negations

    def learn_partial(self, solver, domain: Domain, data: np.ndarray, labels: np.ndarray, new_active_indices: Set):

        # Constants
        n_b_original = len(domain.bool_vars)
        n_b = n_b_original * 2
        n_r = len(domain.real_vars)

        n_h_original = self.half_space_count if n_r > 0 else 0
        n_h = n_h_original * 2 if self.allow_negations else n_h_original

        n_c = self.conjunction_count
        n_d = data.shape[0]

        real_indices = np.array([domain.var_types[v] == smt.REAL for v in domain.variables])
        real_features = data[:, real_indices]
        bool_features = data[:, np.logical_not(real_indices)]

        # Variables
        a_hr = [[smt.Symbol("a_hr[{}][{}]".format(h, r), REAL) for r in range(n_r)] for h in range(n_h_original)]
        b_h = [smt.Symbol("b_h[{}]".format(h), REAL) for h in range(n_h_original)]
        s_ch = [[smt.Symbol("s_ch[{}][{}]".format(c, h)) for h in range(n_h)] for c in range(n_c)]
        s_cb = [[smt.Symbol("s_cb[{}][{}]".format(c, b)) for b in range(n_b)] for c in range(n_c)]

        # Aux variables
        s_ih = [[smt.Symbol("s_ih[{}][{}]".format(i, h)) for h in range(n_h)] for i in range(n_d)]
        s_ic = [[smt.Symbol("s_ic[{}][{}]".format(i, c)) for c in range(n_c)] for i in range(n_d)]

        def pair(real: bool, c: int, index: int) -> Tuple[FNode, FNode]:
            if real:
                return s_ch[c][index], s_ch[c][index + n_h_original]
            else:
                return s_cb[c][index], s_cb[c][index + n_b_original]

        def order_equal(pair1, pair2):
            x_t, x_f, y_t, y_f = pair1 + pair2
            return smt.Iff(x_t, y_t) & smt.Iff(x_f, y_f)

        def order_geq(pair1, pair2):
            x_t, x_f, y_t, y_f = pair1 + pair2
            return x_t | y_f | ((~x_f) & (~y_t))

        def pairs(c: int) -> List[Tuple[FNode, FNode]]:
            return [pair(True, c, i) for i in range(n_h_original)] + [pair(False, c, i) for i in range(n_b_original)]

        def order_geq_lex(c1: int, c2: int):
            pairs_c1, pairs_c2 = pairs(c1), pairs(c2)
            assert len(pairs_c1) == len(pairs_c2)
            constraints = smt.TRUE()
            for j in range(len(pairs_c1)):
                condition = smt.TRUE()
                for i in range(j):
                    condition &= order_equal(pairs_c1[i], pairs_c2[i])
                constraints &= smt.Implies(condition, order_geq(pairs_c1[j], pairs_c2[j]))
            return constraints

        # Constraints
        for i in new_active_indices:
            x_r, x_b, label = [float(val) for val in real_features[i]], bool_features[i], labels[i]

            for h in range(n_h_original):
                sum_coefficients = smt.Plus([a_hr[h][r] * smt.Real(x_r[r]) for r in range(n_r)])
                solver.add_assertion(smt.Iff(s_ih[i][h], sum_coefficients <= b_h[h]))

            for h in range(n_h_original, n_h):
                solver.add_assertion(smt.Iff(s_ih[i][h], ~s_ih[i][h - n_h_original]))

            for c in range(n_c):
                solver.add_assertion(smt.Iff(s_ic[i][c], smt.Or(
                    [smt.FALSE()]
                    + [(s_ch[c][h] & s_ih[i][h]) for h in range(n_h)]
                    + [s_cb[c][b] for b in range(n_b_original) if x_b[b]]
                    + [s_cb[c][b] for b in range(n_b_original, n_b) if not x_b[b - n_b_original]]
                )))

            # --- [start] symmetry breaking ---
            # Mutually exclusive
            if "m" in self.symmetries:
                for c in range(n_c):
                    for h in range(n_h_original):
                        solver.add_assertion(~(s_ch[c][h] & s_ch[c][h + n_h_original]))
                    for b in range(n_b_original):
                        solver.add_assertion(~(s_cb[c][b] & s_cb[c][b + n_b_original]))

            # Normalized
            if "n" in self.symmetries:
                for h in range(n_h_original):
                    solver.add_assertion(smt.Equals(b_h[h], smt.Real(1.0)) | smt.Equals(b_h[h], smt.Real(0.0)))

            # Vertical symmetries
            if "v" in self.symmetries:
                for c in range(n_c - 1):
                    solver.add_assertion(order_geq_lex(c, c + 1))

            # Horizontal symmetries
            if "h" in self.symmetries:
                for h in range(n_h_original - 1):
                    solver.add_assertion(a_hr[h][0] >= a_hr[h + 1][0])
            # --- [end] symmetry breaking ---

            if label:
                solver.add_assertion(smt.And([s_ic[i][c] for c in range(n_c)]))
            else:
                solver.add_assertion(smt.Or([~s_ic[i][c] for c in range(n_c)]))

        solver.solve()
        model = solver.get_model()

        x_vars = [domain.get_symbol(domain.real_vars[r]) for r in range(n_r)]
        half_spaces = [
            smt.Plus([model.get_value(a_hr[h][r]) * x_vars[r] for r in range(n_r)]) <= model.get_value(b_h[h])
            for h in range(n_h_original)
        ] + [
            smt.Plus([model.get_value(a_hr[h][r]) * x_vars[r] for r in range(n_r)]) > model.get_value(b_h[h])
            for h in range(n_h - n_h_original)
        ]

        b_vars = [domain.get_symbol(domain.bool_vars[b]) for b in range(n_b_original)]
        bool_literals = [b_vars[b] for b in range(n_b_original)]
        bool_literals += [~b_vars[b] for b in range(n_b - n_b_original)]

        conjunctions = [
            [half_spaces[h] for h in range(n_h) if model.get_py_value(s_ch[c][h])]
            + [bool_literals[b] for b in range(n_b) if model.get_py_value(s_cb[c][b])]
            for c in range(n_c)
        ]

        return smt.And([smt.Or(conjunction) for conjunction in conjunctions])
