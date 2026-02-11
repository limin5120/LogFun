import contextvars

# Stores the Function ID of the currently executing traced function.
# Default is 0 (Global/Unknown context)
CURRENT_FUNC_ID = contextvars.ContextVar('logfun_func_id', default=0)

# Stores the Log Buffer (Already existed in logger.py, moving here for centrality is better,
# but to minimize changes we can keep buffer in logger or move both here.
# Let's keep buffer in logger for now to reduce diff, but context is crucial).
