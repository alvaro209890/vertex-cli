"""CLI integration for Claude Code."""

# Lazy imports: modules are imported on demand to avoid
# triggering heavy dependencies at package init time.


def CLISessionManager(*args, **kwargs):
    """Lazy import for CLISessionManager."""
    from .manager import CLISessionManager as _cls

    return _cls(*args, **kwargs)


def CLISession(*args, **kwargs):
    """Lazy import for CLISession."""
    from .session import CLISession as _cls

    return _cls(*args, **kwargs)


__all__ = ["CLISession", "CLISessionManager"]
