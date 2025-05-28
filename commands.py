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
import datetime
import sys
from abc import ABC, abstractmethod
from typing import List, Dict, Any
from utils import read_config_file


def filter_and_sort_logs(logs: List[Dict[str, Any]], args) -> List[Dict[str, Any]]:
    """
    Filter and sort task logs based on command-line arguments.

    This function applies various filters (task, category, date) and sorts
    the logs by date and timestamp (newest first).

    Args:
        logs: List of task log entries
        args: Command line arguments with optional filters

    Returns:
        Filtered and sorted list of log entries

    Raises:
        ValueError: If the date format is invalid
    """
    if not logs:
        return logs

    # Sort logs by date and timestamp (newest first)
    logs.sort(key=lambda entry: (entry.get('date', ''), entry.get('timestamp', '')), reverse=True)

    # Make a copy to avoid modifying the original list during iteration
    filtered_logs = logs.copy()
    active_filters = []
    # Display logs in a tabular format
    if not logs:
        print("No tasks found.")
    else:
        print_task_table(logs)
        print(f"\nTotal tasks shown: {len(logs)}")

    # Filter by task name if specified (partial match)
    if hasattr(args, 'task') and args.task:
        active_filters.append(f"task matching '{args.task}'")
        task_filter = args.task.lower()
        filtered_logs = [entry for entry in filtered_logs
                         if task_filter in entry.get('task', '').lower()]

    # Filter by category if specified
    if hasattr(args, 'category') and args.category:
        active_filters.append(f"category '{args.category}'")
        category_filter = args.category.lower()
        filtered_logs = [entry for entry in filtered_logs
                         if entry.get('category', '').lower() == category_filter]

    # Filter by date if specified
    if hasattr(args, 'date') and args.date:
        active_filters.append(f"date '{args.date}'")
        try:
            # Validate date format by attempting to parse it
            date_obj = datetime.date.fromisoformat(args.date)
            date_str = date_obj.isoformat()  # Normalize to standard format
            filtered_logs = [entry for entry in filtered_logs
                             if entry.get('date', '') == date_str]
        except ValueError:
            raise ValueError(f"Invalid date format: '{args.date}'. Please use YYYY-MM-DD format.")

    # Apply limit if specified
    if hasattr(args, 'limit') and args.limit and args.limit > 0:
        active_filters.append(f"limit '{args.limit}'")
        filtered_logs = filtered_logs[:args.limit]  # Get the most recent entries up to the limit

    # Display applied filters if any
    if active_filters:
        print(f"Filters applied: {', '.join(active_filters)}")
        print()

    return filtered_logs


def print_task_table(logs: List[Dict[str, Any]]) -> None:
    """
    Print a formatted table of task entries.

    This function creates a clean tabular representation of task logs
    with columns aligned and proper headers.

    Args:
        logs: List of task entry dictionaries to display
    """
    # Define table headers and column widths
    headers = ["Task", "Duration", "Category", "Date", "Description"]
    widths = [25, 10, 15, 12, 40]  # Wider description field as requested (40 chars)

    # Calculate total width for the table border
    total_width = sum(widths) + len(headers) * 3 - 2

    # Create header row with border
    header_row = "| " + " | ".join(h.ljust(w) for h, w in zip(headers, widths)) + " |"
    border = "+" + "-" * (total_width) + "+"

    print(border)
    print(header_row)
    print(border.replace("-", "="))  # Use '=' for header separator

    # Print each task entry as a row
    for entry in logs:
        # Extract values with defaults for missing fields
        task = entry.get('task', '')

        # Format duration with 2 decimal places
        duration_val = entry.get('duration', 0)
        duration = f"{duration_val:.2f}h"

        category = entry.get('category', '')
        if not category:
            category = "-"

        date = entry.get('date', '')

        description = entry.get('description', '')
        if not description:
            description = "-"

        # Truncate long values and add ellipsis
        if len(task) > widths[0] - 3:
            task = task[:widths[0] - 3] + "..."
        if len(category) > widths[2] - 3:
            category = category[:widths[2] - 3] + "..."
        if len(description) > widths[4] - 3:
            description = description[:widths[4] - 3] + "..."

        # Format the row
        row = [
            task.ljust(widths[0]),
            duration.ljust(widths[1]),
            category.ljust(widths[2]),
            date.ljust(widths[3]),
            description.ljust(widths[4])
        ]

        print("| " + " | ".join(row) + " |")

    # Bottom border
    print(border)


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
        # Function to validate positive duration
        def positive_float(value):
            try:
                fvalue = float(value)
                if fvalue <= 0:
                    raise argparse.ArgumentTypeError("Duration must be greater than 0.")
                return fvalue
            except ValueError:
                raise argparse.ArgumentTypeError("Duration must be a number.")

        # Function to validate date format
        def validate_date(value):
            if not value:
                return value
            try:
                date = datetime.date.fromisoformat(value.strip())
                return date.isoformat()
            except ValueError:
                raise argparse.ArgumentTypeError("Invalid date format. Use YYYY-MM-DD.")

        # Add arguments with validation
        parser.add_argument('task', help='Name of the task')
        parser.add_argument('duration', type=positive_float,
                            help='Time spent on task (in hours, must be positive)')
        parser.add_argument('-c', '--category',
                            help='Category of the task (e.g., work, personal, exercise)')
        parser.add_argument('-d', '--description',
                            help='Description of what was done')
        parser.add_argument('--date', type=validate_date,
                            help='Date of the task (YYYY-MM-DD), defaults to today')

    def execute(self, args: argparse.Namespace) -> None:
        """
        Execute the log command with the given arguments.

        Record a new time entry based on the provided arguments.

        Args:
            args: Parsed command-line arguments including task, duration, etc.
        """
        from tracker import log_task

        # Configuration dictionary
        config = None

        try:
            # Read config file if provided
            if hasattr(args, 'config') and args.config:
                try:
                    config = read_config_file(args.config)
                    if hasattr(args, 'debug') and args.debug:
                        print(f"Using configuration from: {args.config}")
                except (FileNotFoundError, ValueError) as e:
                    print(f"Warning: Could not read config file: {e}")

            # Pass config to log_task
            entry = log_task(
                task=args.task,
                duration=args.duration,
                category=args.category if hasattr(args, 'category') else None,
                description=args.description if hasattr(args, 'description') else None,
                date=args.date if hasattr(args, 'date') else None,
                config=config
            )
            # Enhanced debug output
            if hasattr(args, 'debug') and args.debug:
                if '_log_file' in entry:
                    print(f"Log saved to: {entry['_log_file']}")

            # Success output...

        except ValueError as e:
            # Display a clear error message for validation errors
            print(f"Error: {str(e)}")
            sys.exit(1)
        except Exception as e:
            # Handle other unexpected errors with a generic message
            print(f"Error: An unexpected error occurred: {str(e)}")

            # Show stack trace in debug mode
            if hasattr(args, 'debug') and args.debug:
                import traceback
                print("\nDebug information:")
                print(traceback.format_exc())

            sys.exit(1)


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
        parser.add_argument('-t', '--task', help='Filter entries by task name (partial match supported)')
        parser.add_argument('-c', '--category', help='Filter entries by category (exact match)')
        parser.add_argument('-d', '--date', help='Filter entries by exact date (YYYY-MM-DD)')
        parser.add_argument('-l', '--limit', type=int, help='Limit the number of entries shown')

    def execute(self, args: argparse.Namespace) -> None:
        """
        Execute the view command with the given arguments.

        Display time entries based on the provided filtering arguments.

        Args:
            args: Parsed command-line arguments including filter options.
        """
        import sys
        from storage import load_logs
        from utils import read_config_file

        try:
            # Configuration dictionary
            config = None
            log_file_path = None

            # Read config file if provided
            if hasattr(args, 'config') and args.config:
                try:
                    config = read_config_file(args.config)
                    if 'log_file_path' in config:
                        log_file_path = config['log_file_path']

                    if hasattr(args, 'debug') and args.debug:
                        print(f"Using configuration from: {args.config}")
                        if log_file_path:
                            print(f"Using log file: {log_file_path}")
                except (FileNotFoundError, ValueError) as e:
                    print(f"Warning: Could not read config file: {e}")

            # Load logs from the appropriate file
            logs = load_logs(log_file_path)
            logs = filter_and_sort_logs(logs, args)
            # Display logs in a tabular format
            if not logs:
                print("No tasks found.")
            else:
                print_task_table(logs)
                print(f"\nTotal tasks shown: {len(logs)}")

        except Exception as e:
            print(f"Error: {str(e)}")

            # Show stack trace in debug mode
            if hasattr(args, 'debug') and args.debug:
                import traceback
                print("\nDebug information:")
                print(traceback.format_exc())

            sys.exit(1)


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
