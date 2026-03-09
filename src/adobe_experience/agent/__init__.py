"""AI agent package."""

__all__ = ["AIInferenceEngine"]


def __getattr__(name: str):
	"""Lazily resolve heavy imports to avoid side effects during test collection."""
	if name == "AIInferenceEngine":
		from adobe_experience.agent.inference import AIInferenceEngine

		return AIInferenceEngine
	raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
