#!/usr/bin/env python3
"""
Task Time Tracker (TTT) - A simple command-line tool to track time spent on tasks.
"""

import argparse
import datetime
from abc import ABC, abstractmethod
from typing import List, Dict, Optional, Any


class Task:
    """Represents a task in the time tracking system."""

    def __init__(self, name: str, description: Optional[str] = None):
        self.name = name
        self.description = description


class TimeEntry:
    """Represents a single time entry for a task."""

    def __init__(self, task_name: str, duration: float, date: Optional[datetime.date] = None,
                 description: Optional[str] = None):
        self.task_name = task_name
        self.duration = duration
        self.date = date or datetime.date.today()
        self.description = description


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


class LogCommand(Command):
    """Command for logging time spent on tasks."""

    def add_arguments(self, parser: argparse.ArgumentParser) -> None:
        parser.add_argument('task', help='Name of the task')
        parser.add_argument('duration', type=float, help='Time spent on task (in hours)')
        parser.add_argument('-d', '--description', help='Description of what was done')
        parser.add_argument('--date', help='Date of the task (YYYY-MM-DD), defaults to today')

    def execute(self, args: argparse.Namespace) -> None:
        print(f"[Placeholder] Logging {args.duration} hours for task '{args.task}'")
        # Actual implementation will be added later


class ViewCommand(Command):
    """Command for viewing logged time entries."""

    def add_arguments(self, parser: argparse.ArgumentParser) -> None:
        parser.add_argument('-t', '--task', help='Filter entries by task name')
        parser.add_argument('-d', '--date', help='Filter entries by date (YYYY-MM-DD)')
        parser.add_argument('-l', '--limit', type=int, help='Limit the number of entries shown')

    def execute(self, args: argparse.Namespace) -> None:
        print("[Placeholder] Viewing time entries")
        # Actual implementation will be added later


class SummaryCommand(Command):
    """Command for summarizing time data."""

    def add_arguments(self, parser: argparse.ArgumentParser) -> None:
        parser.add_argument('--from-date', help='Start date for summary (YYYY-MM-DD)')
        parser.add_argument('--to-date', help='End date for summary (YYYY-MM-DD)')
        parser.add_argument('-g', '--group-by', choices=['task', 'day', 'week', 'month'],
                            default='task', help='Group summary by category')

    def execute(self, args: argparse.Namespace) -> None:
        print("[Placeholder] Generating time summary")
        # Actual implementation will be added later


class TaskTracker:
    """Main class that manages the time tracking application."""

    def __init__(self):
        self.commands = {
            'log': LogCommand(),
            'view': ViewCommand(),
            'summary': SummaryCommand()
        }

    def setup_parser(self) -> argparse.ArgumentParser:
        """Set up the command-line argument parser."""
        parser = argparse.ArgumentParser(
            description='Task Time Tracker (TTT) - Track time spent on tasks',
            formatter_class=argparse.RawDescriptionHelpFormatter
        )

        subparsers = parser.add_subparsers(dest='command', help='Command to run')

        # Add each command's subparser
        for name, command in self.commands.items():
            subparser = subparsers.add_parser(name, help=command.__doc__)
            command.add_arguments(subparser)

        return parser

    def run(self, args=None):
        """Run the task tracker application."""
        parser = self.setup_parser()
        parsed_args = parser.parse_args(args)

        if not parsed_args.command:
            parser.print_help()
            return

        # Execute the selected command
        self.commands[parsed_args.command].execute(parsed_args)


def main():
    """Main entry point for the application."""
    tracker = TaskTracker()
    tracker.run()


if __name__ == '__main__':
    main()