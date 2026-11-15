"""Per-person contextual bandit for action plans (Spec 2): linear Thompson sampling.

Agrawal S, Goyal N. Thompson Sampling for Contextual Bandits with Linear Payoffs. ICML 2013 (PMLR 28(3):127-135).
Each action has a Bayesian linear model of "drift reversed within the follow-up window" (reward 1/0) on the
HotSummary context vector (backend/features.py context_vector). Prior means are warm-started from the what-if
forecast (content/plans/warm-start.json) plus a team-value weight on the driver the action addresses.
Label: "learns per person; demonstrated on simulated response, not proven".
"""
import numpy as np

from backend.features import CONTEXT_FEATURES

LEARNING_LABEL = "learns per person; demonstrated on simulated response, not proven"


class LinearThompson:
    def __init__(self, arms, prior_means, prior_precision=1.0, noise=0.5, seed=0):
        """arms: action ids; prior_means: {arm: vector of len(CONTEXT_FEATURES)}."""
        d = len(CONTEXT_FEATURES)
        self.arms, self.noise = list(arms), noise
        self.B = {a: prior_precision * np.eye(d) for a in self.arms}
        self.f = {a: prior_precision * np.asarray(prior_means.get(a, np.zeros(d)), float) for a in self.arms}
        self.rng = np.random.default_rng(seed)
        self.updates, self.last_reward = 0, None

    def mean(self, arm):
        return np.linalg.solve(self.B[arm], self.f[arm])

    def choose(self, x):
        x = np.asarray(x, float)
        scores = {}
        for a in self.arms:
            cov = self.noise ** 2 * np.linalg.inv(self.B[a])
            theta = self.rng.multivariate_normal(self.mean(a), (cov + cov.T) / 2)
            scores[a] = float(x @ theta)
        return max(self.arms, key=lambda a: scores[a])

    def update(self, arm, x, reward):
        x = np.asarray(x, float)
        self.B[arm] += np.outer(x, x)
        self.f[arm] += reward * x
        self.updates += 1
        self.last_reward = reward


def prior_means(arms, warm_start, addresses, driver_weight=1.0, scale=1.0):
    """Bias term from the what-if warm start; driver_weight on the context feature each action addresses."""
    out = {}
    for a in arms:
        m = np.zeros(len(CONTEXT_FEATURES))
        m[0] = scale * warm_start.get(a, 0.0)
        for feature in addresses.get(a, []):
            m[CONTEXT_FEATURES.index(feature)] += driver_weight
        out[a] = m
    return out
