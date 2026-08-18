"""Ambient Healthcare & Patient Triage Agent Package."""
from .agent import agent

root_agent = agent

__all__ = ["agent", "root_agent"]
