"""
Iteration limit management.

Encapsulates the 50 / 100 / 200 threshold logic for the reduction loop.
"""

from src.config.settings import (
    SOFT_ITERATION_LIMIT,
    WARN_ITERATION_LIMIT,
    HARD_ITERATION_LIMIT,
)


def check_iteration_limit(iteration, sentence, on_limit_reached):
    """evaluate iteration thresholds and decide whether to continue.

    parameters:
        iteration        — current iteration count (0-based)
        sentence         — current sentence state (for display)
        on_limit_reached — callback(iteration_count, current_sentence)
                           returns True to continue, False to stop

    returns:
        (should_continue, status)
        should_continue — True to keep going, False to stop
        status          — None if continuing, 'limit_reached' if stopping
    """
    # hard limit — unconditional stop
    if iteration >= HARD_ITERATION_LIMIT:
        return False, "limit_reached"

    # warn limit — extra warning at WARN_ITERATION_LIMIT
    if iteration == WARN_ITERATION_LIMIT:
        if on_limit_reached:
            should_continue = on_limit_reached(iteration, sentence, warn=True)
            if not should_continue:
                return False, "limit_reached"
        return True, None

    # soft limit — pause and ask every SOFT_ITERATION_LIMIT iterations
    if iteration > 0 and iteration % SOFT_ITERATION_LIMIT == 0:
        if on_limit_reached:
            should_continue = on_limit_reached(iteration, sentence)
            if not should_continue:
                return False, "limit_reached"

    return True, None
