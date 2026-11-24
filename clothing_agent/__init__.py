# Lets `adk web` / `adk run` find root_agent when google-adk is installed.
# Demo mode works without it.
try:
    from . import agent  # noqa: F401
except ImportError:
    pass
