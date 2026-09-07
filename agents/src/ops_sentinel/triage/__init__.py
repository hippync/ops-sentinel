"""Triage — classify an alarm into severity and a known incident type.

Routing, not diagnosis: cheap and fast. IncidentType.UNKNOWN short-circuits to a
human; the pipeline never guesses at an incident class it has no playbook for.
"""
