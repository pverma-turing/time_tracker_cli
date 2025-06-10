"""
Configuration settings for the Task Time Tracker application.

This module contains centralized configuration constants and settings used
throughout the application. Centralizing these values makes the codebase more
maintainable and reduces duplication.
"""

# List of all available commands in the application
# This serves as a single source of truth for command names
AVAILABLE_COMMANDS = {
    "log": "LogCommand",
    "view": "ViewCommand",
    "summary": "SummaryCommand",
    'report': 'ReportCommand',
    'delete': "DeleteCommand",
    'edit': "EditCommand",
    'tag': "TagCommand",
    'analytics': "AnalyticsCommand"
}
