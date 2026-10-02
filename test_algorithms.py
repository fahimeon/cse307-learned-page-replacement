"""Known examples and an independent exhaustive oracle for short traces."""
from functools import lru_cache
import random
import unittest
import numpy as np
from experiment import simulate


def brute_opt(trace, frames):
    @lru_cache(None)
    def solve(i, resident):
        if i == len(trace):
            return 0
        page = trace[i]
        cache = set(resident)
        if page in cache:
            return solve(i+1,resident)
        if len(cache) < frames:
            return 1 + solve(i+1,tuple(sorted(cache | {page})))
        return 1 + min(solve(i+1,tuple(sorted((cache-{victim})|{page}))) for victim in cache)
    return solve(0,())


class ReplacementTests(unittest.TestCase):
    def test_learned_ties_use_lru(self):
        class ConstantModel:
            classes_ = np.array([0,1])
            def predict_proba(self, x):
                return np.tile([.5,.5],(len(x),1))
        trace = [1,2,3,1,4,2,1,5,3,2,4,1]
        np.testing.assert_array_equal(simulate(trace,3,'Learned',ConstantModel())[0],
                                      simulate(trace,3,'LRU')[0])

    def test_learned_prefix_is_independent_of_future(self):
        class RecordingModel:
            classes_ = np.array([0,1])
            def __init__(self):
                self.inputs = []
            def predict_proba(self, x):
                self.inputs.append(np.array(x))
                recency = np.array(x)[:,0].astype(float)
                score = recency / (1 + recency)
                return np.column_stack([1-score,score])
        prefix = [1,2,3,1,4,2,5,1,3,2,4,5]
        a,b = RecordingModel(),RecordingModel()
        flags_a = simulate(prefix,3,'Learned',a)[0]
        flags_b = simulate(prefix+[99,99,99,1,1,2],3,'Learned',b)[0]
        np.testing.assert_array_equal(flags_a,flags_b[:len(prefix)])
        for first,second in zip(a.inputs,b.inputs):
            np.testing.assert_array_equal(first,second)

    def test_belady_example(self):
        trace = [1,2,3,4,1,2,5,1,2,3,4,5]
        self.assertEqual(int(simulate(trace,3,'FIFO')[0].sum()),9)
        self.assertEqual(int(simulate(trace,4,'FIFO')[0].sum()),10)
        self.assertEqual(int(simulate(trace,3,'OPT')[0].sum()),7)

    def test_lru_reference(self):
        trace = [7,0,1,2,0,3,0,4,2,3,0,3,2]
        self.assertEqual(int(simulate(trace,3,'LRU')[0].sum()),9)

    def test_small_exhaustive_oracle(self):
        rng = random.Random(307)
        for _ in range(80):
            trace = [rng.randrange(5) for _ in range(10)]
            for frames in [1,2,3]:
                optimal = int(simulate(trace,frames,'OPT')[0].sum())
                self.assertEqual(optimal,brute_opt(trace,frames))
                for policy in ['FIFO','LRU']:
                    self.assertLessEqual(optimal,int(simulate(trace,frames,policy)[0].sum()))

    def test_resident_and_empty(self):
        for policy in ['FIFO','LRU','OPT']:
            self.assertEqual(int(simulate([1,1,1],2,policy)[0].sum()),1)
            self.assertEqual(len(simulate([],2,policy)[0]),0)


if __name__ == '__main__':
    unittest.main()
