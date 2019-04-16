from math import exp
import numpy as np


def sigmoid_increments(sum, n_points, abruptness=1):
    """
    Returns stepwise increments that result in logistic
    growth from 0 to sum over n_points
    :param sum: float, cumulative sum of the increments
    :param n_points: int, number of increments
    :param abruptness: float, how fast the transition is
    :return: np.array, array of increments
    """
    range = (-5, 5)
    points = np.linspace(*range, n_points)
    increments = np.array([logistic_deriv(x, abruptness) for x in points])
    return sum*increments/np.sum(increments)


def logistic(x, k):
    return 1/(1+exp(-k*x))


def logistic_deriv(x, k):
    l = logistic(x, k)
    return l*(1-l)

