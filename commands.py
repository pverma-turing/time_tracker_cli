"""
Command handlers for the Task Time Tracker application.

This module contains the implementation of all commands (log, view, summary)
and the abstract Command base class.
"""

import argparse
from abc import ABC, abstractmethod


class Command(ABC):
    """Base command interface following Command pattern."""

    @abstractmethod
    def add_arguments(self, parser: argparse.ArgumentParser) -> None:
        """Add command-specific arguments to parser."""
        pass

    @abstractmethod
    def execute(self, args: argparse.Namespace) -> None:
        """Execute the command with the given arguments."""
        pass

    def get_short_description(self) -> str:
        """Return a short description for the command to display in top-level help."""
        # By default, use the first line of the docstring as a short description
        if self.__doc__:
            return self.__doc__.split('\n')[0]
        return ""


class LogCommand(Command):
    """Command for logging time spent on tasks."""

    def get_short_description(self) -> str:
        """Return a short description for the log command."""
        return "Record time spent on a task"

    def add_arguments(self, parser: argparse.ArgumentParser) -> None:
        # Positional arguments are already required by default
        parser.add_argument('task', help='Name of the task')
        parser.add_argument('duration', type=float, help='Time spent on task (in hours)')
        parser.add_argument('-d', '--description', help='Description of what was done')
        parser.add_argument('--date', help='Date of the task (YYYY-MM-DD), defaults to today')

    def execute(self, args: argparse.Namespace) -> None:
        print(f"[Placeholder] Logging {args.duration} hours for task '{args.task}'")
        # Actual implementation will be added later


class ViewCommand(Command):
    """Command for viewing logged time entries."""

    def get_short_description(self) -> str:
        """Return a short description for the view command."""
        return "Display time entries with optional filtering"

    def add_arguments(self, parser: argparse.ArgumentParser) -> None:
        parser.add_argument('-t', '--task', help='Filter entries by task name')
        parser.add_argument('-d', '--date', help='Filter entries by date (YYYY-MM-DD)')
        parser.add_argument('-l', '--limit', type=int, help='Limit the number of entries shown')

    def execute(self, args: argparse.Namespace) -> None:
        print("[Placeholder] Viewing time entries")
        # Actual implementation will be added later


class SummaryCommand(Command):
    """Command for summarizing time data."""

    def get_short_description(self) -> str:
        """Return a short description for the summary command."""
        return "Generate summary reports of tracked time"

    def add_arguments(self, parser: argparse.ArgumentParser) -> None:
        parser.add_argument('--from-date', help='Start date for summary (YYYY-MM-DD)')
        parser.add_argument('--to-date', help='End date for summary (YYYY-MM-DD)')
        parser.add_argument('-g', '--group-by', choices=['task', 'day', 'week', 'month'],
                           default='task', help='Group summary by category')

    def execute(self, args: argparse.Namespace) -> None:
        print("[Placeholder] Generating time summary")
        # Actual implementation will be added later