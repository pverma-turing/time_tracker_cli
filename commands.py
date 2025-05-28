"""
Command handlers for the Task Time Tracker application.

This module contains the implementation of all commands (log, view, summary)
and the abstract Command base class. It follows the Command design pattern,
allowing for easy addition of new commands with consistent interfaces.

Each command implements:
1. Argument definition
2. Execution logic
3. Help text generation

The module is designed to be extended with additional commands while maintaining
a consistent user interface across the application.
"""

import argparse
from abc import ABC, abstractmethod


class Command(ABC):
    """
    Base command interface following the Command design pattern.

    This abstract base class defines the interface that all commands must implement.
    It ensures consistency across different commands and allows for polymorphic
    command execution in the main application.

    Subclasses must implement:
    - add_arguments: Define command-specific CLI arguments
    - execute: Implement the command's functionality
    """

    @abstractmethod
    def add_arguments(self, parser: argparse.ArgumentParser) -> None:
        """
        Add command-specific arguments to parser.

        This method is called during the parser setup phase to add any arguments
        specific to this command.

        Args:
            parser: The argument parser to add arguments to.
        """
        pass

    @abstractmethod
    def execute(self, args: argparse.Namespace) -> None:
        """
        Execute the command with the given arguments.

        This method contains the main logic for running the command based on the
        parsed command-line arguments.

        Args:
            args: Parsed command-line arguments relevant to this command.
        """
        pass

    def get_short_description(self) -> str:
        """
        Return a short description for the command to display in top-level help.

        This method provides a concise description of the command's purpose for
        display in the main help screen. By default, it extracts the first line
        of the class docstring.

        Returns:
            str: A short description of the command.
        """
        # By default, use the first line of the docstring as a short description
        if self.__doc__:
            return self.__doc__.split('\n')[0]
        return ""


class LogCommand(Command):
    """
    Command for logging time spent on tasks.

    This command allows users to record time entries with information about:
    - Task name
    - Duration
    - Optional description
    - Optional date (defaults to today)

    Example usage:
    ttt log "Coding" 1.5 -d "Implementing TTT CLI"
    """

    def get_short_description(self) -> str:
        """
        Return a short description for the log command.

        Returns:
            str: A concise description of the log command's purpose.
        """
        return "Record time spent on a task"

    def add_arguments(self, parser: argparse.ArgumentParser) -> None:
        """
        Add log command-specific arguments to parser.

        Configure the parser with all arguments needed for the log command,
        including required positional arguments and optional flags.

        Args:
            parser: The argument parser to add arguments to.
        """
        # Positional arguments are already required by default
        parser.add_argument('task', help='Name of the task')
        parser.add_argument('duration', type=float, help='Time spent on task (in hours)')
        parser.add_argument('-d', '--description', help='Description of what was done')
        parser.add_argument('--date', help='Date of the task (YYYY-MM-DD), defaults to today')

    def execute(self, args: argparse.Namespace) -> None:
        """
        Execute the log command with the given arguments.

        Record a new time entry based on the provided arguments.

        Args:
            args: Parsed command-line arguments including task, duration, etc.
        """
        from tracker import log_task

        # Log the task and get the entry
        entry = log_task(
            task=args.task,
            duration=args.duration,
            description=args.description if hasattr(args, 'description') else None,
            date=args.date if hasattr(args, 'date') else None
        )

        # Print confirmation message
        print(f"Logged {args.duration}h for '{args.task}'")

        # Display additional details if debug mode is enabled
        if hasattr(args, 'debug') and args.debug:
            print(f"Entry details: {entry}")


class ViewCommand(Command):
    """
    Command for viewing logged time entries.

    This command displays time entries with optional filtering by:
    - Task name
    - Date
    - Limiting the number of entries shown

    Example usage:
    ttt view -t "Coding" -d "2023-04-15" -l 10
    """

    def get_short_description(self) -> str:
        """
        Return a short description for the view command.

        Returns:
            str: A concise description of the view command's purpose.
        """
        return "Display time entries with optional filtering"

    def add_arguments(self, parser: argparse.ArgumentParser) -> None:
        """
        Add view command-specific arguments to parser.

        Configure the parser with all arguments needed for viewing time entries,
        including various filtering options.

        Args:
            parser: The argument parser to add arguments to.
        """
        parser.add_argument('-t', '--task', help='Filter entries by task name')
        parser.add_argument('-d', '--date', help='Filter entries by date (YYYY-MM-DD)')
        parser.add_argument('-l', '--limit', type=int, help='Limit the number of entries shown')

    def execute(self, args: argparse.Namespace) -> None:
        """
        Execute the view command with the given arguments.

        Display time entries based on the provided filtering arguments.

        Args:
            args: Parsed command-line arguments including filter options.
        """
        print("[Placeholder] Viewing time entries")
        # Actual implementation will be added later


class SummaryCommand(Command):
    """
    Command for summarizing time data.

    This command generates reports summarizing time entries with options for:
    - Date range filtering
    - Grouping by task, day, week, or month

    Example usage:
    ttt summary --from-date 2023-04-01 --to-date 2023-04-30 -g week
    """

    def get_short_description(self) -> str:
        """
        Return a short description for the summary command.

        Returns:
            str: A concise description of the summary command's purpose.
        """
        return "Generate summary reports of tracked time"

    def add_arguments(self, parser: argparse.ArgumentParser) -> None:
        """
        Add summary command-specific arguments to parser.

        Configure the parser with all arguments needed for generating summary reports,
        including date range and grouping options.

        Args:
            parser: The argument parser to add arguments to.
        """
        parser.add_argument('--from-date', help='Start date for summary (YYYY-MM-DD)')
        parser.add_argument('--to-date', help='End date for summary (YYYY-MM-DD)')
        parser.add_argument('-g', '--group-by', choices=['task', 'day', 'week', 'month'],
                           default='task', help='Group summary by category')

    def execute(self, args: argparse.Namespace) -> None:
        """
        Execute the summary command with the given arguments.

        Generate and display a summary report based on the provided filtering and
        grouping options.

        Args:
            args: Parsed command-line arguments including date ranges and grouping.
        """
        print("[Placeholder] Generating time summary")
        # Actual implementation will be added later