"""CLI package."""

__all__ = ["app"]


def __getattr__(name: str):
	"""Lazily resolve the root Typer app to avoid eager dependency imports."""
	if name == "app":
		from adobe_experience.cli.main import app

		return app
	raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
