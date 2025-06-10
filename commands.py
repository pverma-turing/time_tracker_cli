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
import io
import json
import os
import sys
from datetime import datetime as dt
from abc import ABC, abstractmethod
from collections import defaultdict
from typing import List, Dict, Any
from datetime import datetime as dt
from storage import load_logs
from utils import read_config_file
import csv


def export_summary_to_csv(summary, category=None, csv_filename='summary.csv'):
    """
    Export summary data to a CSV file.

    Args:
        summary: Dictionary with categories as keys and dictionaries of tasks and minutes as values
        category: Optional category used for filtering
        csv_filename: Name of the CSV file to create

    Returns:
        Tuple of (success_flag, message)
    """
    try:
        with open(csv_filename, 'w', newline='') as csvfile:
            # Create CSV writer
            csv_writer = csv.writer(csvfile)

            # Write headers
            if category:
                # If we're filtering by a specific category, we're just showing tasks
                csv_writer.writerow(['task', 'total_minutes'])

                # Sort tasks by time in descending order and write rows
                for task, minutes in sorted(summary[category].items(), key=lambda x: x[1], reverse=True):
                    csv_writer.writerow([task, minutes])
            else:
                # If we're showing all categories, include category and total time
                csv_writer.writerow(['category', 'task', 'total_minutes'])

                # Write category summaries and their tasks
                for category_name, tasks in summary.items():
                    # Sort tasks by time in descending order
                    sorted_tasks = sorted(tasks.items(), key=lambda x: x[1], reverse=True)

                    # If there are no tasks in this category (shouldn't happen), skip
                    if not sorted_tasks:
                        continue

                    # Write each task with its category
                    for task, minutes in sorted_tasks:
                        csv_writer.writerow([category_name, task, minutes])

        return True, f"Summary exported to {csv_filename}"
    except Exception as e:
        return False, f"Error exporting summary to CSV: {str(e)}"


def validate_top_parameter(top):
    """
    Validate the top parameter.

    Args:
        top: The top parameter value to validate

    Returns:
        None if invalid, otherwise the validated integer value
    """
    if top is None:
        return None

    try:
        top_int = int(top)
        if top_int <= 0:
            print(f"Warning: --top value must be positive. Showing all results.")
            return None
        return top_int
    except ValueError:
        print(f"Warning: --top value must be an integer. Showing all results.")
        return None


# Date validation function
def validate_date(date_str):
    """
    Validate and parse a date string in YYYY-MM-DD format.

    Args:
        date_str: Date string to validate

    Returns:
        Parsed date object if valid, None otherwise
    """
    if not date_str:
        return None

    try:
        # Parse the date string (YYYY-MM-DD format)
        parsed_date = datetime.datetime.strptime(date_str, '%Y-%m-%d').date()
        return parsed_date
    except ValueError:
        return None


def summarize_by_category_and_task(logs, category=None, top=None, start_date=None, end_date=None):
    """
    Summarize time spent by category and task.

    Args:
        logs: List of time entry dictionaries
        category: Optional category to filter by
        top: Optional limit to show only top N results
        start_date: Optional start date for filtering (inclusive)
        end_date: Optional end date for filtering (inclusive)

    Returns:
        Dictionary with categories as keys and dictionaries of tasks and minutes as values
    """
    # First, filter logs by date range if specified
    if start_date or end_date:
        filtered_logs = []
        for entry in logs:
            try:
                # Parse the timestamp (assumed to be ISO format)
                entry_date = datetime.datetime.fromisoformat(entry.get('date', '')).date()

                # Check if the entry falls within the date range
                if start_date and entry_date < start_date:
                    continue
                if end_date and entry_date > end_date:
                    continue

                # If we get here, the entry is within the date range
                filtered_logs.append(entry)
            except (ValueError, TypeError):
                # Skip entries with invalid timestamps
                continue

        # Replace the original logs with the filtered ones
        logs = filtered_logs

    # Then filter by category if specified
    if category is not None:
        logs = [entry for entry in logs if entry.get('category') == category]

    summary = {}
    for entry in logs:
        entry_category = entry.get('category', 'general')
        task_name = entry.get('task', 'Unnamed')
        # Convert duration to minutes (assuming duration is stored in hours)
        minutes = int(float(entry.get('duration', 0)) * 60)

        # Initialize category if not exists
        if entry_category not in summary:
            summary[entry_category] = {}

        # Initialize task if not exists
        if task_name not in summary[entry_category]:
            summary[entry_category][task_name] = 0

        # Add minutes to task
        summary[entry_category][task_name] += minutes

    # If we need to limit to top categories
    if top is not None and not category:
        # Calculate total minutes per category
        category_totals = {cat: sum(tasks.values()) for cat, tasks in summary.items()}
        # Sort categories by total time and get top N
        top_categories = sorted(category_totals.items(), key=lambda x: x[1], reverse=True)[:top]
        # Filter summary to include only top categories
        summary = {cat: summary[cat] for cat, _ in top_categories}

    return summary


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


def format_summary_as_json(summary, category=None):
    """
    Format summary data as a structured JSON object.

    Args:
        summary: Dictionary with categories as keys and dictionaries of tasks and minutes as values
        category: Optional category used for filtering

    Returns:
        Dictionary formatted for JSON output
    """
    result = {}

    if category:
        # If we're filtering by a specific category, create a single category object
        result = {
            "category": category,
            "total_minutes": sum(summary[category].values()),
            "tasks": []
        }

        # Sort tasks by minutes in descending order
        sorted_tasks = sorted(summary[category].items(), key=lambda x: x[1], reverse=True)

        # Add task details
        for task_name, minutes in sorted_tasks:
            result["tasks"].append({
                "name": task_name,
                "minutes": minutes
            })
    else:
        # If we're showing all categories, create a list of category objects
        result = {
            "categories": []
        }

        # Calculate total minutes per category for sorting
        category_totals = {cat: sum(tasks.values()) for cat, tasks in summary.items()}

        # Sort categories by total minutes in descending order
        sorted_categories = sorted(summary.items(),
                                   key=lambda x: sum(x[1].values()),
                                   reverse=True)

        # Add category details with their tasks
        for category_name, tasks in sorted_categories:
            category_data = {
                "name": category_name,
                "total_minutes": sum(tasks.values()),
                "tasks": []
            }

            # Sort tasks by minutes in descending order
            sorted_tasks = sorted(tasks.items(), key=lambda x: x[1], reverse=True)

            # Add task details
            for task_name, minutes in sorted_tasks:
                category_data["tasks"].append({
                    "name": task_name,
                    "minutes": minutes
                })

            result["categories"].append(category_data)

    return result


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
            try:
                logs = load_logs(log_file_path)
            except ValueError as e:
                print(f"Error: Could not load logs — file is corrupted.")
                if hasattr(args, 'debug') and args.debug:
                    print(f"Debug details: {str(e)}")
                sys.exit(1)

            # Apply sorting and filtering
            logs = filter_and_sort_logs(logs, args)

            # Collect active filters for display
            active_filters = []
            if hasattr(args, 'task') and args.task:
                active_filters.append(f"task matching '{args.task}'")
            if hasattr(args, 'category') and args.category:
                active_filters.append(f"category '{args.category}'")
            if hasattr(args, 'date') and args.date:
                active_filters.append(f"date '{args.date}'")

            # Display applied filters if any
            if active_filters:
                print(f"Filters applied: {', '.join(active_filters)}")
                print()

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
        parser.add_argument('--category',
                            help='Filter logs by category',
                            type=str,
                            required=False)
        parser.add_argument('--by', choices=['task', 'category'],
                            default='category', help='Group results by task or category')
        parser.add_argument('--top', type=int, help='Show only top N results by time spent')
        parser.add_argument('--csv', action='store_true', help='Export results to summary.csv')
        parser.add_argument('--start-date', help='Filter logs starting from this date (YYYY-MM-DD)')
        parser.add_argument('--end-date', help='Filter logs until this date (YYYY-MM-DD)')
        parser.add_argument('--json', action='store_true',
                            help='Output results as a JSON object instead of formatted text')

    def execute(self, args: argparse.Namespace) -> None:
        """
        Execute the summary command with the given arguments.

        Generate and display a summary report based on the provided filtering and
        grouping options.

        Args:
            args: Parsed command-line arguments including date ranges and grouping.
        """
        logs = load_logs()
        category = args.category if hasattr(args, 'category') else None
        grouping = getattr(args, 'by', 'category')
        export_csv = getattr(args, 'csv', False)
        output_json = getattr(args, 'json', False)
        # Validate and store date range parameters
        start_date = None
        end_date = None
        date_filter_error = None

        if hasattr(args, 'start_date') and args.start_date:
            start_date = validate_date(args.start_date)
            if start_date is None:
                date_filter_error = f"Invalid start date format: '{args.start_date}'. Use YYYY-MM-DD."

        if hasattr(args, 'end_date') and args.end_date and not date_filter_error:
            end_date = validate_date(args.end_date)
            if end_date is None:
                date_filter_error = f"Invalid end date format: '{args.end_date}'. Use YYYY-MM-DD."

        # Check if end_date is before start_date
        if start_date and end_date and end_date < start_date:
            date_filter_error = "End date cannot be earlier than start date."

        # Validate and store the top parameter
        top = None
        if hasattr(args, 'top'):
            top = validate_top_parameter(args.top)
        # If no logs found, show message and exit
        if not logs:
            print("No time entries found.")
            return

        # Build date range string for output
        date_range_str = ""
        if start_date:
            date_range_str += f" from {start_date.isoformat()}"
        if end_date:
            date_range_str += f" to {end_date.isoformat()}"

        # Summarize by category and task, applying filter if provided
        detailed_summary = summarize_by_category_and_task(logs, category, top, start_date, end_date)

        # Print the summary with appropriate heading
        if category:
            print(f"Summary for category '{category}':")
        else:
            print("Summary by category:")

        # Check if we have results
        if not detailed_summary:
            print(f"No entries found{' for the specified category' if category else ''}.")
            return

        # Export to CSV if requested
        if export_csv:
            success, message = export_summary_to_csv(detailed_summary, category)
            print(message)
            if not success:
                # If CSV export fails, still proceed with console output
                print("Falling back to console output.")

        # Print the summary with appropriate heading (unless we're only exporting to CSV)
        if not export_csv or not success:
            if category:
                print(f"Summary for category '{category}'{date_range_str}:")
            else:
                print(f"Summary by category{date_range_str}:")

        # Output as JSON if requested
        if output_json:
            try:
                # Format the summary data as JSON
                json_data = format_summary_as_json(detailed_summary, category)
                # Print the JSON with pretty formatting (indent)
                print(json.dumps(json_data, indent=2))
            except Exception as e:
                print(f"Error generating JSON output: {str(e)}")
                # Fall back to text output
                output_json = False

        # Print the summary with appropriate heading if not outputting JSON
        if not output_json:
            if category:
                print(f"Summary for category '{category}'{date_range_str}:")
            else:
                print(f"Summary by category{date_range_str}:")

        # Display results with nested task details
        for category, tasks in detailed_summary.items():
            # Calculate total minutes for the category
            category_total = sum(tasks.values())
            print(f"\n{category}: {category_total} minutes")

            # Sort tasks by duration in descending order
            sorted_tasks = sorted(tasks.items(), key=lambda x: x[1], reverse=True)

            # Apply top limit to tasks if specified and we're looking at a specific category
            if top is not None and category:
                sorted_tasks = sorted_tasks[:top]

            # Display each task with indentation
            for task_name, minutes in sorted_tasks:
                print(f"  - {task_name}: {minutes} minutes")


class ReportCommand:
    """Command to export time entries to a CSV file."""
    VALID_SORT_OPTIONS = ['date', 'category', 'duration']
    VALID_SORT_ORDERS = ['asc', 'desc']
    VALID_COLUMNS = ['date', 'task', 'duration', 'category', 'description']
    DEFAULT_DELIMITER = ','

    def get_short_description(self) -> str:
        """
        Return a short description for the summary command.

        Returns:
            str: A concise description of the summary command's purpose.
        """
        return "Generate reports of tracked time"

    def add_arguments(self, parser: argparse.ArgumentParser) -> None:
        """
        Add report command-specific arguments to parser.

        Configure the parser with all arguments needed for generating summary reports,
        including date range and grouping options.

        Args:
            parser: The argument parser to add arguments to.
        """
        parser.add_argument('--output', help='Output CSV file name (default: logs_report.csv)')
        parser.add_argument('--start-date', help='Start date for filtering logs (YYYY-MM-DD)')
        parser.add_argument('--end-date', help='End date for filtering logs (YYYY-MM-DD)')
        parser.add_argument('--category', help='Filter logs by category')
        parser.add_argument('--sort-by', choices=['date', 'category', 'duration'],
                            default='date', help='Sort logs by field (default: date)')
        parser.add_argument('--sort-order', choices=['asc', 'desc'],
                            default='desc', help='Sort order: ascending or descending (default: desc)')
        parser.add_argument('--columns',
                            help='Comma-separated list of columns to include (default: all columns)')
        parser.add_argument('--min-duration', type=int, help='Minimum task duration in minutes to include')
        parser.add_argument('--limit', type=int, help='Limit to top N entries based on current sort order')
        parser.add_argument('--no-header', action='store_true',
                                   help='Omit header row in CSV output (useful for appending to existing files)')
        parser.add_argument('--delimiter',
                                   help='Specify custom delimiter character for CSV output (default: ,)')

    def execute(self, args):
        """Execute the report command with the given arguments."""
        # Get all time entries
        logs = self._get_logs()

        if not logs:
            print("No logs found.")
            return

        # Apply filters if specified
        try:
            filtered_logs = self._apply_filters(logs, args)

            # Apply sorting
            sorted_logs = self._sort_logs(filtered_logs, args)

            # Apply limit if specified
            limited_logs = self._apply_limit(sorted_logs, args)

            # Parse and validate requested columns
            try:
                columns = self._parse_columns(args)
            except ValueError as e:
                print(f"Error with column selection: {str(e)}")
                print("Please specify valid column names.")
                return

            # Get delimiter
            try:
                delimiter = self._parse_delimiter(args)
            except ValueError as e:
                print(f"Error with delimiter: {str(e)}")
                print("Please specify a single character as delimiter.")
                return

            # Determine output filename
            output_file = args.output if args.output else "logs_report.csv"

            # Check if header should be included
            include_header = not (hasattr(args, 'no_header') and args.no_header)

            # Export to CSV
            try:
                self._export_to_csv(limited_logs, output_file, columns, include_header, delimiter)

                # Prepare feedback message
                message = f"Report saved to {output_file}."
                if not include_header:
                    message += " (Header row omitted)"

                if delimiter != self.DEFAULT_DELIMITER:
                    message += f" (Using '{delimiter}' as delimiter)"

                if len(filtered_logs) < len(logs):
                    message += f" ({len(filtered_logs)} of {len(logs)} entries matched filters)"

                # Add limit information if applicable
                if hasattr(args, 'limit') and args.limit is not None and len(limited_logs) < len(filtered_logs):
                    message += f" (Limited to top {len(limited_logs)} entries)"

                print(message)

            except IOError as e:
                print(f"Failed to write to output file: {str(e)}")

                # Provide additional guidance based on common issues
                if "Permission denied" in str(e):
                    print("Check that you have write permission to the directory and the file is not in use.")
                elif "No such file or directory" in str(e):
                    print("The directory for the output file does not exist. Please create it first.")

        except ValueError as e:
            print(f"Error: {str(e)}")

    def _parse_delimiter(self, args):
        """Parse and validate the delimiter argument."""
        # Use default delimiter if not specified
        if not hasattr(args, 'delimiter') or not args.delimiter:
            return self.DEFAULT_DELIMITER

        # Validate the delimiter
        if len(args.delimiter) != 1:
            raise ValueError("Delimiter must be a single character")

        return args.delimiter

    def _get_logs(self):
        """Retrieve all time entries from storage."""
        # This implementation should use the same storage mechanism as other commands
        try:
            from storage import load_logs
            logs = load_logs()

            if not logs:
                # This distinguishes between "no file" and "empty file"
                # Implementation might need to be adjusted based on how load_logs behaves
                # For example, if load_logs returns None for missing files and [] for empty files
                if logs is None:
                    print("Log file not found.")
                else:
                    print("Log file exists but contains no entries.")

            return logs

        except (ImportError, ModuleNotFoundError):
            print("Error loading storage module. Check your installation.")
            return []
        except Exception as e:
            print(f"Error loading logs: {str(e)}")
            return []

    def _apply_filters(self, logs, args):
        """Apply filters based on command arguments."""
        filtered_logs = logs
        filter_applied = False
        filters_applied = []

        # Apply date range filters if specified
        if args.start_date:
            try:
                start_date = self._validate_date(args.start_date)
                filtered_logs = [log for log in filtered_logs if self._date_to_datetime(log['date']) >= start_date]
                filter_applied = True
                filters_applied.append(f"start_date={args.start_date}")
            except ValueError as e:
                raise ValueError(f"Invalid start date: {str(e)}")

        if args.end_date:
            try:
                end_date = self._validate_date(args.end_date)
                filtered_logs = [log for log in filtered_logs if self._date_to_datetime(log['date']) <= end_date]
                filter_applied = True
                filters_applied.append(f"end_date={args.end_date}")
            except ValueError as e:
                raise ValueError(f"Invalid end date: {str(e)}")

        # Apply category filter if specified
        if args.category:
            filtered_logs = [log for log in filtered_logs if log.get('category', '') == args.category]
            filter_applied = True
            filters_applied.append(f"category={args.category}")

        # Apply minimum duration filter if specified
        if hasattr(args, 'min_duration') and args.min_duration is not None:
            try:
                min_duration = self._validate_min_duration(args.min_duration)
                # Convert min_duration from minutes to hours for comparison with log.duration
                min_duration_hours = min_duration / 60.0
                filtered_logs = [log for log in filtered_logs if float(log['duration']) >= min_duration_hours]
                filter_applied = True
                filters_applied.append(f"min_duration={args.min_duration} minutes")
            except ValueError as e:
                raise ValueError(f"Invalid minimum duration: {str(e)}")

        # Log filter usage information
        if filter_applied:
            print(f"Applied filters: {', '.join(filters_applied)}")

        return filtered_logs

    def _apply_limit(self, logs, args):
        """Apply limit to the sorted logs if specified."""
        if not hasattr(args, 'limit') or args.limit is None:
            return logs

        try:
            limit = self._validate_limit(args.limit)
            return logs[:limit]
        except ValueError as e:
            raise ValueError(f"Invalid limit: {str(e)}")

    def _validate_limit(self, limit):
        """Validate limit value."""
        if not isinstance(limit, int):
            raise ValueError("Limit must be an integer")

        if limit <= 0:
            raise ValueError("Limit must be a positive integer")

        return limit

    def _validate_min_duration(self, min_duration):
        """Validate minimum duration value."""
        if not isinstance(min_duration, int):
            raise ValueError("Minimum duration must be an integer")

        if min_duration < 0:
            raise ValueError("Minimum duration cannot be negative")

        return min_duration

    def _sort_logs(self, logs, args):
        """Sort logs based on the provided sort-by parameter."""
        sort_by = args.sort_by if hasattr(args, 'sort_by') and args.sort_by else 'date'

        if sort_by not in self.VALID_SORT_OPTIONS:
            raise ValueError(
                f"Invalid sort option: '{sort_by}'. Valid options are: {', '.join(self.VALID_SORT_OPTIONS)}")

        # Get sort order and validate
        sort_order = self._get_sort_order(args)
        reverse = (sort_order == 'desc')

        if sort_by == 'date':
            return sorted(logs, key=lambda log: self._date_to_datetime(log['date']), reverse=reverse)
        elif sort_by == 'category':
            # Sort by category, placing None/empty categories at the end
            return sorted(logs, key=lambda log: ('category' not in log or log['category'] is None,
                                                 log.get('category', '') or ''), reverse=reverse)
        elif sort_by == 'duration':
            # Sort by duration in descending order (higher duration first)
            return sorted(logs, key=lambda log: float(log['duration']), reverse=reverse)

        # Default fallback to date sorting (shouldn't reach here due to validation)
        return sorted(logs, key=lambda log: self._date_to_datetime(log['date']))

    def _parse_columns(self, args):
        """Parse and validate the columns argument."""
        # Use default columns if not specified
        if not hasattr(args, 'columns') or not args.columns:
            return self.VALID_COLUMNS

        # Parse the comma-separated list
        requested_columns = [col.strip().lower() for col in args.columns.split(',')]

        # Validate the requested columns
        unknown_columns = [col for col in requested_columns if col not in self.VALID_COLUMNS]
        if unknown_columns:
            raise ValueError(
                f"Unknown column(s): {', '.join(unknown_columns)}. Valid columns are: {', '.join(self.VALID_COLUMNS)}")

        return requested_columns

    def _get_sort_order(self, args):
        """Get and validate the sort order."""
        sort_order = getattr(args, 'sort_order', 'desc')

        if sort_order not in self.VALID_SORT_ORDERS:
            raise ValueError(
                f"Invalid sort order: '{sort_order}'. Valid options are: {', '.join(self.VALID_SORT_ORDERS)}")

        return sort_order

    def _validate_date(self, date_str):
        """Validate and parse date string in YYYY-MM-DD format."""
        try:
            return datetime.datetime.strptime(date_str, "%Y-%m-%d")
        except ValueError:
            raise ValueError(f"Date must be in YYYY-MM-DD format, got '{date_str}'")

    def _date_to_datetime(self, date_str):
        """Convert date string to datetime object for comparison."""
        try:
            return datetime.datetime.strptime(date_str, "%Y-%m-%d")
        except ValueError:
            # In case the log date is in a different format, handle gracefully
            # This is a fallback and should be aligned with the actual date format used in the app
            return datetime.datetime.strptime("1970-01-01", "%Y-%m-%d")  # Use a default date in the past

    def _export_to_csv(self, logs, output_file, columns, include_header=True, delimiter=','):
        """Export time entries to a CSV file with the specified columns."""
        try:
            with open(output_file, 'w', newline='') as csvfile:
                writer = csv.writer(csvfile, delimiter=delimiter)

                # Write header row with selected columns if header is requested
                if include_header:
                    writer.writerow(columns)

                # Write data rows with only the selected columns
                for entry in logs:
                    row = []
                    for col in columns:
                        if col == 'date':
                            row.append(entry['date'])
                        elif col == 'task':
                            row.append(entry['task'])
                        elif col == 'duration':
                            row.append(entry['duration'])
                        elif col == 'category':
                            row.append(entry.get('category', ''))
                        elif col == 'description':
                            row.append(entry.get('description', ''))
                    writer.writerow(row)
        except IOError as e:
            raise IOError(f"Failed to write CSV file: {str(e)}")


class DeleteCommand(Command):
    """Command to delete time entries based on specified criteria."""

    def get_short_description(self) -> str:
        """
        Return a short description for the summary command.

        Returns:
            str: A concise description of the summary command's purpose.
        """
        return "Delete logs"

    def add_arguments(self, parser: argparse.ArgumentParser) -> None:
        """
        Add report command-specific arguments to parser.

        Configure the parser with all arguments needed for generating summary reports,
        including date range and grouping options.

        Args:
            parser: The argument parser to add arguments to.
        """
        parser.add_argument('--id', help='ID of the specific log entry to delete')
        parser.add_argument('--category', help='Delete all entries within a given category')
        parser.add_argument('--date', help='Delete all entries from a specific date (YYYY-MM-DD format)')
        parser.add_argument('--dry-run', action='store_true',
                                  help='Simulate deletion without actually removing entries')
        parser.add_argument('--preview', action='store_true',
                                   help='Display a detailed table of entries matching filter criteria (no deletion performed)')
        parser.add_argument('--start-date',
                                   help='Delete entries from this date onward (YYYY-MM-DD format, inclusive)')
        parser.add_argument('--end-date', help='Delete entries up to this date (YYYY-MM-DD format, inclusive)')
        parser.add_argument('--reason', help='Record the reason for deletion (for documentation purposes)')
        parser.add_argument('--all', action='store_true',
                                   help='Delete all entries (cannot be combined with other filters)')
        parser.add_argument('--keyword',
                                   help='Delete entries containing this keyword in the task (case-insensitive)')

    def execute(self, args):
        """Execute the delete command with the given arguments."""
        # Check if --all is combined with other filters
        if args.all and (args.id or args.category or args.date or args.start_date or args.end_date):
            print("Error: --all cannot be combined with other filters.")
            return

        # Check for invalid combinations of --keyword with --id or --all
        if args.keyword and (args.id or args.all):
            print("Error: --keyword cannot be combined with --id or --all.")
            return

        # Check if at least one filter is provided or --all
        if not (
                args.id or args.category or args.date or args.start_date or args.end_date or args.keyword or args.all):
            print(
                "Error: At least one filter (--id, --category, --date, --start-date, --end-date, --keyword) must be provided, or use --all to delete all entries.")
            return

        # Get all time entries
        logs = self._get_logs()

        if not logs:
            print("No entries found.")
            return
        entries_to_delete = []

        if args.all:
            entries_to_delete = logs.copy()
        else:
            # Make a copy of the logs
            # Make a copy of the logs to preserve the original list
            original_logs = logs.copy()


            # Check date range filters
            for log in original_logs:
                should_delete = True
                # Check ID filter
                if args.id and str(log['id']) != args.id:
                    should_delete = False

                # Check category filter
                if args.category and log['category'] != args.category:
                    should_delete = False

                # Check exact date filter
                if args.date and str(log['date']) != args.date:
                    should_delete = False

                # Check date range filters
                if args.start_date or args.end_date:
                    log_date = self._parse_date(str(log['date']))

                if args.start_date or args.end_date:
                    log_date = self._parse_date(str(log['date']))

                    if args.start_date:
                        start_date = self._parse_date(args.start_date)
                        if log_date < start_date:
                            should_delete = False

                    if args.end_date:
                        end_date = self._parse_date(args.end_date)
                        if log_date > end_date:
                            should_delete = False
                # Check keyword filter (case-insensitive match in task field)
                if args.keyword and args.keyword.lower() not in log['task'].lower():
                    should_delete = False

                if should_delete:
                    entries_to_delete.append(log)

        # Calculate how many entries were deleted
        deleted_count = len(entries_to_delete)

        if deleted_count == 0:
            if args.keyword:
                print(f"No matching entries found for keyword '{args.keyword}'. Nothing was deleted.")
            elif args.start_date or args.end_date:
                print("No matching entries found for the specified date range. Nothing was deleted.")
            else:
                print("No matching entries found. Nothing was deleted.")
            return

        # Handle preview mode - takes precedence over dry run and normal delete
        if args.preview:
            self._preview_entries(entries_to_delete)
            return

        # Create a description of what's being filtered
        filter_description = self._create_filter_description(args)

        if args.dry_run:
            if args.all:
                print(f"All {deleted_count} entries would be deleted.")
            else:
                filter_description = self._create_filter_description(args)
                print(
                    f"{deleted_count} {'entry' if deleted_count == 1 else 'entries'} {filter_description} would be deleted.")

            if args.reason:
                print(f"Reason: {args.reason}")
            print("No data was modified (dry run mode).")
        else:
            # Display confirmation message
            if args.all:
                print(f"You are about to delete all entries.")
            else:
                filter_description = self._create_filter_description(args)
                print(
                    f"{deleted_count} {'entry' if deleted_count == 1 else 'entries'} {filter_description} will be deleted.")

            if args.reason:
                print(f"Reason: {args.reason}")

            # Prompt for confirmation
            confirmation = input(
                f"You are about to delete {deleted_count} {'entry' if deleted_count == 1 else 'entries'}. Do you want to proceed? (y/n): ")

            if confirmation.lower() == 'y':
                # Identify entries to keep (entries that don't match filter criteria)
                remaining_logs = [log for log in logs if log not in entries_to_delete]

                # Perform actual deletion by saving the remaining logs
                self._save_logs(remaining_logs)

                # Generate the summary message based on what was deleted
                summary_message = self._create_summary_message(args, deleted_count, filter_description)
                print(summary_message)
            else:
                if args.all:
                    print("Deletion of all entries canceled by user.")
                else:
                    print("Deletion cancelled by user.")

    def _create_summary_message(self, args, deleted_count, filter_description):
        """Create a detailed summary message for the deletion operation."""
        # Base message with count and appropriate pluralization
        message = f"Deleted {deleted_count} {'entry' if deleted_count == 1 else 'entries'}"

        # Add filter information if applicable
        if args.all:
            message = "All entries deleted successfully"
        elif filter_description:
            message += f" {filter_description}"

        # Add reason if provided
        if args.reason:
            message += f". Reason: {args.reason}"
        else:
            message += "."

        return message

    def _preview_entries(self, entries_to_delete):
        """Display a preview of entries that would be deleted in a tabular format."""
        if not entries_to_delete:
            print("No matching entries found for preview.")
            return

        print(f"Previewing {len(entries_to_delete)} entries that match your criteria. No changes will be made.")

        # Create header and formatting for table
        header = ["ID", "Date", "Task", "Duration", "Category"]

        # Determine max width for each column based on content
        id_width = max(len("ID"), max(len(str(idx)) for idx, entry in enumerate(entries_to_delete)) if entries_to_delete else 0)
        date_width = max(len("Date"),
                         max(len(str(entry['date'])) for entry in entries_to_delete) if entries_to_delete else 0)
        task_width = max(len("Task"), max(len(entry['task']) for entry in entries_to_delete) if entries_to_delete else 0)
        duration_width = max(len("Duration"),
                             max(len(str(entry['duration'])) for entry in entries_to_delete) if entries_to_delete else 0)
        category_width = max(len("Category"), max(
            len(entry['category']) if entry['category'] else 0 for entry in entries_to_delete) if entries_to_delete else 0)

        # Create format string for table rows
        format_str = f"| {{:{id_width}}} | {{:{date_width}}} | {{:{task_width}}} | {{:{duration_width}}} | {{:{category_width}}} |"

        # Print header
        header_str = format_str.format(*header)
        separator = "-" * len(header_str)
        print(separator)
        print(header_str)
        print(separator)

        # Print each entry
        for idx, entry in enumerate(entries_to_delete):
            print(format_str.format(
                str(idx),
                str(entry['date']),
                entry['task'],
                str(entry['duration']),
                entry.get('category', '')
            ))

        print(separator)

    def _create_filter_description(self, args):
        """Create a descriptive text of the filters being applied."""
        descriptions = []

        if args.id:
            descriptions.append(f"with ID {args.id}")

        if args.category:
            descriptions.append(f"from category '{args.category}'")

        if args.date:
            descriptions.append(f"dated {args.date}")

        if args.start_date and args.end_date:
            descriptions.append(f"within date range {args.start_date} to {args.end_date}")
        elif args.start_date:
            descriptions.append(f"from {args.start_date} onward")
        elif args.end_date:
            descriptions.append(f"up to {args.end_date}")

        if args.keyword:
            descriptions.append(f"containing keyword '{args.keyword}'")

        if not descriptions:
            return ""

        return " ".join(descriptions)

    def _parse_date(self, date_str):
        """Parse a date string in YYYY-MM-DD format."""
        from datetime import datetime
        try:
            return datetime.strptime(date_str, "%Y-%m-%d").date()
        except ValueError:
            # Return a default date in case of parsing error
            # In a real implementation, this should probably raise an error
            return datetime.min.date()

    def _get_logs(self):
        """Retrieve all time entries from the storage."""
        # In a real implementation, this would load from a database or file
        # This should be replaced with actual log loading code
        # For example, by using a data storage service or manager

        from storage import load_logs
        logs = load_logs()
        if not logs:
            return []  # Replace with actual implementation
        return logs

    def _save_logs(self, logs):
        """Save the remaining logs back to storage."""
        # This should use the same data storage mechanism as other commands
        # For example, if using JSON file storage:
        try:
            from storage import save_logs
            save_logs(logs)
        except Exception as e:
            print(f"Error saving logs: {e}")


class EditCommand(Command):
    """Command to edit an existing time entry."""

    def get_short_description(self) -> str:
        """
        Return a short description for the summary command.

        Returns:
            str: A concise description of the summary command's purpose.
        """
        return "Edit logs"

    def add_arguments(self, parser: argparse.ArgumentParser) -> None:
        """
        Add report command-specific arguments to parser.

        Configure the parser with all arguments needed for generating summary reports,
        including date range and grouping options.

        Args:
            parser: The argument parser to add arguments to.
        """
        filter_group = parser.add_argument_group('entry selection')
        filter_group.add_argument('--id', type=int, help='ID of specific entry to edit')
        filter_group.add_argument('--category', help='Edit all entries with this category')
        filter_group.add_argument('--date', help='Edit all entries on this date (YYYY-MM-DD)')

        # Update fields
        update_group = parser.add_argument_group('fields to update')
        update_group.add_argument('--task', help='New task description')
        update_group.add_argument('--duration', type=int, help='New duration in minutes')
        update_group.add_argument('--new-category', dest='new_category',
                                  help='New category (use this to update the category)')
        update_group.add_argument('--new-date', dest='new_date',
                                  help='New date in YYYY-MM-DD format')
        update_group.add_argument('--rename-category', dest='rename_category',
                                  help='Rename a category across multiple entries (use with --category)')

        # Batch import
        batch_group = parser.add_argument_group('batch operations')
        batch_group.add_argument('--import-csv', metavar='FILE',
                                 help='Import edits from a CSV file with id column and update fields')

        # Mode flags
        mode_group = parser.add_argument_group('operation mode')
        mode_group.add_argument('--dry-run', action='store_true',
                                help='Simulate the update without modifying data')
        mode_group.add_argument('--preview', action='store_true',
                                help='Show a detailed preview of changes without modifying data')
        mode_group.add_argument('--interactive', action='store_true',
                                help='Enter interactive mode for guided editing (only for single entry)')
        mode_group.add_argument('--reason', help='Document the reason for making this edit')

    def execute(self, args):
        """Execute the edit command with the given arguments."""
        # Validate arguments
        self._validate_arguments(args)

        # Handle CSV import if requested
        if args.import_csv is not None:
            self._handle_csv_import(args)
            return

        # Handle category rename operation if requested
        if args.rename_category is not None:
            self._handle_category_rename(args)
            return

        # Get all time entries
        logs = self._get_logs()

        # Find entries to edit based on filters
        entries_to_edit = self._find_entries_to_edit(logs, args)

        # Handle case when no entries found
        if not entries_to_edit:
            if args.preview:
                print("No entries found for the given filters.")
            else:
                self._print_no_entries_message(args)
            return

        # If preview mode is enabled, show the detailed preview and exit
        if args.preview:
            self._show_preview(entries_to_edit, args)
            return

        # Multi-entry mode vs single-entry mode
        if args.id is not None:
            # Single entry edit mode
            self._handle_single_entry_edit(entries_to_edit[0], args, logs)
        else:
            # Multi-entry edit mode
            self._handle_multi_entry_edit(entries_to_edit, args, logs)

    def _validate_arguments(self, args):
        """Validate command arguments for consistency."""
        # CSV import specific validation
        if args.import_csv is not None:
            # Check if any other filter or update flags are used with import-csv
            other_flags = []
            if args.id is not None:
                other_flags.append("--id")
            if args.category is not None:
                other_flags.append("--category")
            if args.date is not None:
                other_flags.append("--date")
            if args.task is not None:
                other_flags.append("--task")
            if args.duration is not None:
                other_flags.append("--duration")
            if args.new_category is not None:
                other_flags.append("--new-category")
            if args.new_date is not None:
                other_flags.append("--new-date")
            if args.rename_category is not None:
                other_flags.append("--rename-category")

            if other_flags:
                raise ValueError(
                    f"--import-csv cannot be used with other update or filter flags: {', '.join(other_flags)}.")

            # Check if the CSV file exists
            if not os.path.exists(args.import_csv):
                raise ValueError(f"CSV file not found: {args.import_csv}")

            # We can return early since we've validated the import-csv operation
            return

        # Category rename specific validation
        if args.rename_category is not None:
            if args.category is None:
                raise ValueError("--rename-category can only be used with --category.")

            # Check if any other update or filter flags are used with rename-category
            invalid_combinations = []
            if args.id is not None:
                invalid_combinations.append("--id")
            if args.date is not None:
                invalid_combinations.append("--date")
            if args.task is not None:
                invalid_combinations.append("--task")
            if args.duration is not None:
                invalid_combinations.append("--duration")
            if args.new_category is not None:
                invalid_combinations.append("--new-category")
            if args.new_date is not None:
                invalid_combinations.append("--new-date")

            if invalid_combinations:
                raise ValueError(f"--rename-category cannot be combined with {', '.join(invalid_combinations)}.")

            # We can return early since we've validated the rename-category operation
            return

        # Standard validation for other operations
        # Check if both ID and category/date filters are provided
        if args.id is not None and (args.category is not None or args.date is not None):
            raise ValueError(
                "Cannot combine --id with --category or --date. Use either --id for a single entry or --category/--date for multiple entries.")

        # Check if at least one filter is provided
        if args.id is None and args.category is None and args.date is None:
            raise ValueError("You must provide at least one filter: --id, --category, or --date.")

        # Check if at least one update field is provided
        update_fields = [args.task, args.duration, args.new_category, args.new_date]
        if all(field is None for field in update_fields):
            raise ValueError(
                "At least one field (--task, --duration, --new-category, or --new-date) must be specified for editing.")

        # Interactive mode can only be used with --id
        if args.interactive and args.id is None:
            raise ValueError("Interactive mode (--interactive) can only be used when editing a single entry with --id.")

        # Preview cannot be combined with interactive mode
        if args.preview and args.interactive:
            raise ValueError("--preview cannot be used with --interactive.")

        # Validate date format if provided
        if args.date is not None:
            try:
                dt.strptime(args.date, "%Y-%m-%d")
            except ValueError:
                raise ValueError("Invalid date format for --date. Please use YYYY-MM-DD format.")

        if args.new_date is not None:
            try:
                dt.strptime(args.new_date, "%Y-%m-%d")
            except ValueError:
                raise ValueError("Invalid date format for --new-date. Please use YYYY-MM-DD format.")

    def _handle_csv_import(self, args):
        """Process a CSV file and apply edits to entries."""
        csv_file = args.import_csv

        try:
            # Get all logs
            logs = self._get_logs()

            # Track results
            successful_updates = 0
            skipped_entries = 0
            skipped_ids = []

            # Prepare for preview if needed
            preview_changes = []

            # Open and process the CSV file
            with open(csv_file, 'r', newline='') as csvfile:
                # Attempt to detect dialect/format
                try:
                    dialect = csv.Sniffer().sniff(csvfile.read(1024))
                    csvfile.seek(0)
                except csv.Error:
                    dialect = 'excel'  # Default to standard CSV format
                    csvfile.seek(0)

                reader = csv.DictReader(csvfile, dialect=dialect)

                # Validate headers
                headers = reader.fieldnames
                if not headers:
                    raise ValueError("CSV file is empty or has no headers")

                # Ensure id column exists
                if 'id' not in headers:
                    raise ValueError("CSV file must contain an 'id' column")

                # Validate that at least one editable field exists
                editable_fields = ['task', 'duration', 'category', 'date']
                if not any(field in headers for field in editable_fields):
                    raise ValueError(
                        "CSV file must contain at least one editable field (task, duration, category, date)")

                # Process each row
                for row_num, row in enumerate(reader, start=2):  # Start at 2 to account for header row
                    try:
                        # Get the ID and ensure it's valid
                        try:
                            entry_id = int(row['id'])
                        except (ValueError, TypeError):
                            print(f"Warning: Skipping row {row_num} - Invalid ID format: {row.get('id', 'missing')}")
                            skipped_entries += 1
                            continue

                        # Find the entry with this ID
                        try:
                            entry_index = next(i for i, log in enumerate(logs) if i + 1 == entry_id)
                            entry = logs[entry_index]
                        except StopIteration:
                            print(f"Warning: Skipping row {row_num} - No entry found with ID: {entry_id}")
                            skipped_entries += 1
                            skipped_ids.append(entry_id)
                            continue

                        # Prepare updates for this entry
                        updates = {}
                        changes = []

                        # Process each editable field
                        if 'task' in headers and row['task']:
                            updates['task'] = row['task']
                            changes.append(f"task from '{entry['task']}' to '{row['task']}'")

                        if 'duration' in headers and row['duration']:
                            try:
                                duration = int(row['duration'])
                                if duration <= 0:
                                    print(
                                        f"Warning: Row {row_num} - Invalid duration (must be positive): {row['duration']}")
                                    continue
                                updates['duration'] = duration
                                changes.append(f"duration from {entry['duration']} to {duration}")
                            except (ValueError, TypeError):
                                print(f"Warning: Row {row_num} - Invalid duration format: {row['duration']}")
                                continue

                        if 'category' in headers and row['category']:
                            updates['category'] = row['category']
                            old_category = entry.get('category', "(none)")
                            changes.append(f"category from '{old_category}' to '{row['category']}'")

                        if 'date' in headers and row['date']:
                            try:
                                # Validate date format
                                dt.strptime(row['date'], "%Y-%m-%d")
                                updates['date'] = row['date']
                                changes.append(f"date from {entry['date']} to {row['date']}")
                            except ValueError:
                                print(f"Warning: Row {row_num} - Invalid date format: {row['date']}")
                                continue

                        # If no valid updates found, skip this row
                        if not updates:
                            print(f"Warning: Skipping row {row_num} - No valid updates specified")
                            skipped_entries += 1
                            continue

                        # If in preview or dry-run mode, just store changes
                        if args.preview or args.dry_run:
                            preview_changes.append((entry_id, entry, updates, changes))
                        else:
                            # Apply updates
                            self._apply_updates_to_entry(entry, updates)
                            successful_updates += 1

                    except Exception as e:
                        print(f"Warning: Error processing row {row_num}: {str(e)}")
                        skipped_entries += 1
                        continue

            # Handle preview mode
            if args.preview:
                print(f"Previewing changes from CSV import ({len(preview_changes)} entries):")
                for entry_id, entry, updates, _ in preview_changes:
                    print(f"Entry {entry_id}:")
                    if 'task' in updates:
                        print(f"  Task: \"{entry['task']}\" → \"{updates['task']}\"")
                    if 'duration' in updates:
                        print(f"  Duration: {entry['duration']} → {updates['duration']}")
                    if 'category' in updates:
                        old_category = entry.get('category',"(none)")
                        print(f"  Category: \"{old_category}\" → \"{updates['category']}\"")
                    if 'date' in updates:
                        print(f"  Date: {entry['date']} → {updates['date']}")
                print("No changes will be made (preview mode).")
                return

            # Handle dry run mode
            if args.dry_run:
                print(f"This would update {len(preview_changes)} entries and skip {skipped_entries} entries.")
                if skipped_ids:
                    print(f"Skipped IDs: {', '.join(map(str, skipped_ids))}")
                print("No changes will be saved (dry-run mode).")
                return

            # Save changes
            if successful_updates > 0:
                self._save_logs(logs)

            # Print summary
            print(f"CSV import completed: {successful_updates} entries updated, {skipped_entries} entries skipped.")
            if skipped_ids:
                print(f"Skipped IDs: {', '.join(map(str, skipped_ids))}")

        except Exception as e:
            # Handle any errors in CSV processing
            raise ValueError(f"Error processing CSV file: {str(e)}")

    def _handle_category_rename(self, args):
        """Handle renaming a category across multiple entries."""
        old_category = args.category
        new_category = args.rename_category

        # Get all time entries
        logs = self._get_logs()

        # Find entries with the old category
        matching_entries = [log for log in logs if log['category'] == old_category]
        entry_count = len(matching_entries)

        # Handle case when no entries match
        if entry_count == 0:
            print(f"No entries found with category '{old_category}'.")
            return

        # Show summary of what will be changed
        print(f"Found {entry_count} entries with category '{old_category}'.")
        message = f"Will rename category from '{old_category}' to '{new_category}'"
        if args.reason:
            message += f" (Reason: {args.reason})"
        print(message)

        # If it's a dry run or preview, just show what would happen and exit
        if args.dry_run:
            print(f"This would rename the category for {entry_count} entries. No changes will be saved (dry-run mode).")
            return

        if args.preview:
            print(f"Previewing category rename for {entry_count} entries:")
            for i, entry in enumerate(matching_entries):
                print(f"Entry {i + 1}:")
                print(f"  Category: \"{entry['category']}\" → \"{new_category}\"")
            print("No changes will be made (preview mode).")
            return

        # Ask for confirmation
        confirm = input(
            f"Rename category '{old_category}' to '{new_category}' for {entry_count} entries? (y/n): ").strip().lower()
        if confirm != 'y':
            print("Operation canceled.")
            return

        # Apply category rename to all matching entries
        for entry in matching_entries:
            entry['category'] = new_category

        # Save the updated logs
        self._save_logs(logs)

        # Print success message
        message = f"Renamed category '{old_category}' to '{new_category}' for {entry_count} entries."
        if args.reason:
            message += f" Reason: {args.reason}"
        print(message)

    def _find_entries_to_edit(self, logs, args):
        """Find entries that match the given filters."""
        if args.id is not None:
            # Find entry by ID
            try:
                entry = next(log for i, log in enumerate(logs) if i + 1 == args.id)
                return [entry]
            except StopIteration:
                return []
        else:
            # Find entries by category and/or date
            matching_entries = logs

            if args.category is not None:
                matching_entries = [log for log in matching_entries
                                    if log['category'] == args.category]

            if args.date is not None:
                matching_entries = [log for log in matching_entries
                                    if log['date'] == args.date]

            return matching_entries

    def _print_no_entries_message(self, args):
        """Print appropriate message when no entries match the filters."""
        if args.id is not None:
            print(f"No entry found with ID {args.id}.")
        else:
            conditions = []
            if args.category is not None:
                conditions.append(f"category '{args.category}'")
            if args.date is not None:
                conditions.append(f"date '{args.date}'")

            print(f"No entries found matching {' and '.join(conditions)}.")

    def _show_preview(self, entries, args):
        """Show a detailed preview of changes that would be applied."""
        entry_count = len(entries)

        # Collect updates to apply
        updates = {}
        if args.task is not None:
            updates['task'] = args.task
        if args.duration is not None:
            updates['duration'] = args.duration
        if args.new_category is not None:
            updates['category'] = args.new_category
        if args.new_date is not None:
            updates['date'] = args.new_date

        # Display preview header
        if entry_count == 1:
            print(f"Previewing changes to 1 entry:")
        else:
            print(f"Previewing changes to {entry_count} entries:")

        # Display changes for each entry
        for i, entry in enumerate(entries):
            # For multi-entry preview, show entry numbers/IDs
            if entry_count > 1:
                print(f"Entry {i + 1}:")
            else:
                print(f"Entry {args.id}:")

            # Show each field that would change
            changes_shown = False

            if 'task' in updates:
                print(f"  Task: \"{entry['task']}\" → \"{updates['task']}\"")
                changes_shown = True

            if 'duration' in updates:
                print(f"  Duration: {entry['duration']} → {updates['duration']}")
                changes_shown = True

            if 'category' in updates:
                old_category = entry.get('category',"(none)")
                print(f"  Category: \"{old_category}\" → \"{updates['category']}\"")
                changes_shown = True

            if 'date' in updates:
                print(f"  Date: {entry['date']} → {updates['date']}")
                changes_shown = True

            # If no changes would be made to this entry, indicate that
            if not changes_shown:
                print("  No changes would be applied to this entry.")

        # Reason display if provided
        if args.reason:
            print(f"Reason for changes: {args.reason}")

        # Final message
        print("No changes will be made (preview mode).")

    def _handle_single_entry_edit(self, entry, args, logs):
        """Handle editing of a single entry."""
        # Check if explicitly provided update fields exist
        update_fields_provided = any(field is not None for field in
                                     [args.task, args.duration, args.new_category, args.new_date])

        # Enter interactive mode if requested and no specific update fields were provided
        if args.interactive and not update_fields_provided:
            changes = self._run_interactive_mode(entry, args.dry_run, args.reason)
            if not changes:  # User canceled the operation
                return
        else:
            # Regular update mode (non-interactive)
            updates = {}
            changes = []

            # Collect changes for task
            if args.task is not None:
                updates['task'] = args.task
                changes.append(f"task changed from '{entry['task']}' to '{args.task}'")

            # Collect changes for duration
            if args.duration is not None:
                updates['duration'] = args.duration
                changes.append(f"duration changed from {entry['duration']} to {args.duration} minutes")

            # Collect changes for category
            if args.new_category is not None:
                updates['category'] = args.new_category
                old_category = entry.get('category', "(none)")
                changes.append(f"category changed from '{old_category}' to '{args.new_category}'")

            # Collect changes for date
            if args.new_date is not None:
                updates['date'] = args.new_date
                changes.append(f"date changed from {entry['date']} to {args.new_date}")

            # If it's a dry run, just display the changes without updating
            if args.dry_run:
                message = f"You are about to update entry {entry['id']}: {', '.join(changes)}. No changes will be saved (dry-run mode)."
                if args.reason:
                    message += f" Reason: {args.reason}"
                print(message)
                return

            # Apply changes
            self._apply_updates_to_entry(entry, updates)

        # If we got here and no changes were collected, there's nothing to do
        if not changes:
            print("No changes were made.")
            return

        # Save the updated logs
        if not args.dry_run:
            self._save_logs(logs)
            # Print summary of changes
            message = f"Updated entry {entry.id}: {', '.join(changes)}."
            if args.reason:
                message += f" Reason: {args.reason}"
            print(message)

    def _handle_multi_entry_edit(self, entries, args, logs):
        """Handle editing of multiple entries."""
        entry_count = len(entries)

        # Collect updates to apply
        updates = {}
        if args.task is not None:
            updates['task'] = args.task
        if args.duration is not None:
            updates['duration'] = args.duration
        if args.new_category is not None:
            updates['category'] = args.new_category
        if args.new_date is not None:
            updates['date'] = args.new_date

        # Prepare summary of changes for display
        changes_summary = []
        if 'task' in updates:
            changes_summary.append(f"task to '{updates['task']}'")
        if 'duration' in updates:
            changes_summary.append(f"duration to {updates['duration']} minutes")
        if 'category' in updates:
            changes_summary.append(f"category to '{updates['category']}'")
        if 'date' in updates:
            changes_summary.append(f"date to '{updates['date']}'")

        # Show what will be changed
        print(f"Found {entry_count} entries matching the criteria.")
        message = f"The following fields will be updated: {', '.join(changes_summary)}"
        if args.reason:
            message += f" (Reason: {args.reason})"
        print(message)

        # If it's a dry run, just show what would happen
        if args.dry_run:
            print(f"This would update {entry_count} entries. No changes will be saved (dry-run mode).")
            return

        # Ask for confirmation
        confirm = input(f"Update {entry_count} entries? (y/n): ").strip().lower()
        if confirm != 'y':
            print("Operation canceled.")
            return

        # Apply updates to all matching entries
        for entry in entries:
            self._apply_updates_to_entry(entry, updates)

        # Save the updated logs
        self._save_logs(logs)

        # Print summary
        message = f"Successfully updated {entry_count} entries."
        if args.reason:
            message += f" Reason: {args.reason}"
        print(message)

    def _apply_updates_to_entry(self, entry, updates):
        """Apply the given updates to an entry."""
        if 'task' in updates:
            entry['task'] = updates['task']
        if 'duration' in updates:
            entry['duration'] = updates['duration']
        if 'category' in updates:
            entry['category'] = updates['category']
        if 'date' in updates:
            entry['date'] = updates['date']

    def _run_interactive_mode(self, entry, dry_run=False, reason=None):
        """Run interactive mode for editing an entry."""
        print(f"\nInteractive edit mode for entry {entry.id}")
        if reason:
            print(f"Reason for edit: {reason}")
        print(f"Current values:")
        print(f"  Task: {entry['task']}")
        print(f"  Duration: {entry['duration']} minutes")
        print(f"  Category: {entry.get('category', '(none)')}")
        print(f"  Date: {entry['date']}")
        print("\nEnter new values (leave blank to keep current value)")

        # Collect changes
        changes = []
        updates = {}

        # Task prompt
        new_task = input(f"Task [{entry['task']}]: ").strip()
        if new_task:
            updates['task'] = new_task
            changes.append(f"task changed from '{entry['task']}' to '{new_task}'")

        # Duration prompt
        while True:
            new_duration = input(f"Duration in minutes [{entry['duration']}]: ").strip()
            if not new_duration:
                break
            try:
                new_duration = int(new_duration)
                if new_duration <= 0:
                    print("Duration must be a positive number.")
                    continue
                updates['duration'] = new_duration
                changes.append(f"duration changed from {entry['duration']} to {new_duration} minutes")
                break
            except ValueError:
                print("Please enter a valid number for duration.")

        # Category prompt
        new_category = input(f"Category [{entry.get('category', '(none)')}]: ").strip()
        if new_category:
            updates['category'] = new_category
            old_category = entry.get('category', '(none)')
            changes.append(f"category changed from '{old_category}' to '{new_category}'")

        # Date prompt
        while True:
            new_date = input(f"Date (YYYY-MM-DD) [{entry['date']}]: ").strip()
            if not new_date:
                break
            try:
                dt.strptime(new_date, "%Y-%m-%d")
                updates['date'] = new_date
                changes.append(f"date changed from {entry['date']} to {new_date}")
                break
            except ValueError:
                print("Invalid date format. Please use YYYY-MM-DD format.")

        # If no changes were made
        if not changes:
            print("No changes were specified.")
            return []

        # Ask for confirmation
        print("\nSummary of changes:")
        for change in changes:
            print(f"- {change}")

        if reason:
            print(f"Reason: {reason}")

        if dry_run:
            print("\nNo changes will be saved (dry-run mode).")
            return changes

        confirm = input("\nApply these changes? (y/n): ").strip().lower()
        if confirm != 'y':
            print("Operation canceled.")
            return []

        # Apply the changes
        self._apply_updates_to_entry(entry, updates)
        return changes

    def _get_logs(self):
        """Retrieve all time entries from the storage."""
        # In a real implementation, this would load from a database or file
        # This should be replaced with actual log loading code
        # For example, by using a data storage service or manager

        from storage import load_logs
        logs = load_logs()
        if not logs:
            return []  # Replace with actual implementation
        return logs

    def _save_logs(self, logs):
        """Save the remaining logs back to storage."""
        # This should use the same data storage mechanism as other commands
        # For example, if using JSON file storage:
        try:
            from storage import save_logs
            save_logs(logs)
        except Exception as e:
            print(f"Error saving logs: {e}")


class TagCommand(Command):
    """Command to add tags to a specific log entry."""

    def get_short_description(self) -> str:
        """
        Return a short description for the summary command.

        Returns:
            str: A concise description of the summary command's purpose.
        """
        return "Tag logs"

    def add_arguments(self, parser: argparse.ArgumentParser) -> None:
        """Add command-specific arguments to parser."""
        parser.add_argument('--id', required=True, type=int, help='ID of the entry to tag')
        parser.add_argument('--add', help='Comma-separated list of tags to add (e.g., work,urgent)')
        parser.add_argument('--remove', help='Comma-separated list of tags to remove (e.g., work,urgent)')
        parser.add_argument('--list', action='store_true', help='List all tags for the specified entry')
        parser.add_argument('--clear', action='store_true', help='Remove all tags from the specified entry')
        parser.add_argument('--all', action='store_true', help='List all unique tags across all entries')

    def execute(self, args):
        """Execute the tag command with the given arguments."""
        # Count the operation flags
        flag_count = sum([bool(args.add), bool(args.remove), bool(args.list),
                          bool(args.clear), bool(args.all)])

        # Validate flag combinations
        if flag_count > 1:
            print("Error: The --add, --remove, --list, --clear, and --all flags cannot be used together.")
            return

        if flag_count == 0:
            print("Please provide one of the following flags: --add, --remove, --list, --clear, or --all.")
            return

        # Handle the --all flag (which doesn't need an entry ID)
        if args.all:
            self._handle_all_tags()
            return

        # For all other operations, we need an entry ID
        if not args.id:
            print("Error: The --id flag is required for this operation.")
            return

        # Get the log entry by ID
        entry = self._get_log_by_id(args.id)

        if not entry:
            print(f"No entry found with ID {args.id}")
            return

        # Initialize tags list if it doesn't exist
        if 'tags' not in entry:
            entry['tags'] = []

        # Delegate to the appropriate operation handler
        if args.list:
            self._handle_list(entry, args.id)
        elif args.clear:
            self._handle_clear(entry, args.id)
        elif args.add:
            self._handle_add(entry, args.id, args.add)
        elif args.remove:
            self._handle_remove(entry, args.id, args.remove)
    def _handle_all_tags(self):
        """Handle the --all flag by displaying all unique tags across all entries."""
        # Get all log entries
        all_entries = self._get_logs()

        # Collect all unique tags
        unique_tags = set()
        for entry in all_entries:
            if entry.get('tags'):
                unique_tags.update(entry['tags'])

        # Display the tags sorted alphabetically
        if unique_tags:
            sorted_tags = sorted(unique_tags)
            tags_string = ", ".join(sorted_tags)
            print(f"All tags: {tags_string}")
        else:
            print("No tags found.")

    def _handle_list(self, entry, entry_id):
        """Handle the list operation."""
        if not entry['tags']:
            print(f"No tags found for entry {entry_id}.")
        else:
            tags_string = ", ".join(entry['tags'])
            total_tags = len(entry['tags'])
            print(f"Tags for entry {entry_id} (total {total_tags}): {tags_string}")

    def _handle_clear(self, entry, entry_id):
        """Handle the clear operation."""
        if not entry['tags']:
            print(f"No tags to clear for entry {entry_id}.")
            return

        # Clear the tags
        entry['tags'] = []

        # Save the updated entry
        self._save_entry(entry)

        # Show confirmation and summary message
        print(f"Cleared all tags from entry {entry_id}. Total tags now: 0.")

    def _handle_add(self, entry, entry_id, add_arg):
        """Handle the add operation."""
        # Parse the comma-separated tags
        new_tags = [tag.strip() for tag in add_arg.split(',')]

        # Add tags to the entry (without duplicates)
        added_tags = self._add_tags_to_entry(entry, new_tags)

        # Save the updated entry
        self._save_entry(entry)

        # Show confirmation message
        if added_tags:
            print(f"Added tags {added_tags} to entry {entry_id}.")
            # Show summary message
            total_tags = len(entry['tags'])
            print(f"Total tags now: {total_tags}.")
        else:
            print(f"No new tags added to entry {entry_id}. All tags already exist.")
            total_tags = len(entry['tags'])
            print(f"Total tags: {total_tags}.")

    def _handle_remove(self, entry, entry_id, remove_arg):
        """Handle the remove operation."""
        # Parse the comma-separated tags
        tags_to_remove = [tag.strip() for tag in remove_arg.split(',')]

        # Remove tags from the entry
        removed_tags = self._remove_tags_from_entry(entry, tags_to_remove)

        if not removed_tags:
            print("No matching tags found to remove.")
            return

        # Save the updated entry
        self._save_entry(entry)

        # Show confirmation message and summary
        print(f"Removed tags {removed_tags} from entry {entry_id}.")
        # Show summary message
        total_tags = len(entry['tags'])
        print(f"Total tags now: {total_tags}.")
    def _get_log_by_id(self, entry_id):
        """Retrieve a log entry by its ID."""
        # This would be replaced with actual retrieval logic
        # For example, by using a data storage service or manager
        # This is just a placeholder
        from storage import load_logs
        logs = load_logs()
        if not logs:
            return None
        for log in logs:
            if log["id"] == int(entry_id):
                return log
        return None

    def _add_tags_to_entry(self, entry, new_tags):
        """Add tags to an entry without duplicating existing ones."""
        # Initialize tags list if it doesn't exist
        if 'tags' not in entry:
            entry['tags'] = []

        # Add only new tags (avoiding duplicates)
        added_tags = []
        for tag in new_tags:
            if tag not in entry['tags']:
                entry['tags'].append(tag)
                added_tags.append(tag)

        return added_tags

    def _remove_tags_from_entry(self, entry, tags_to_remove):
        """Remove tags from an entry and return the list of removed tags."""
        # Keep track of which tags were actually removed
        removed_tags = []

        for tag in tags_to_remove:
            if tag in entry['tags']:
                entry['tags'].remove(tag)
                removed_tags.append(tag)

        return removed_tags

    def _get_logs(self):
        """Retrieve all time entries from the storage."""
        # In a real implementation, this would load from a database or file
        # This should be replaced with actual log loading code
        # For example, by using a data storage service or manager

        from storage import load_logs
        logs = load_logs()
        if not logs:
            return []  # Replace with actual implementation
        return logs

    def _save_logs(self, logs):
        """Save the remaining logs back to storage."""
        # This should use the same data storage mechanism as other commands
        # For example, if using JSON file storage:
        try:
            from storage import save_logs
            save_logs(logs)
        except Exception as e:
            print(f"Error saving logs: {e}")

    def _save_entry(self, entry):
        """Save the updated entry back to storage."""
        # This would be replaced with actual save logic
        # For example, by using a data storage service or manager
        # This is just a placeholder
        logs = load_logs()
        if not logs:
            self._save_logs([entry])
        else:
            updated_logs = []
            for log in logs:
                if log['id'] == entry['id']:
                    updated_logs.append(entry)
                else:
                    updated_logs.append(log)
            self._save_logs(updated_logs)


class AnalyticsCommand(Command):
    """Command to calculate and display total time spent per category."""

    def add_arguments(self, parser: argparse.ArgumentParser) -> None:
        parser.add_argument('--from', dest='from_date',
                                      help='Start date for filtering (YYYY-MM-DD format)')
        parser.add_argument('--to', dest='to_date',
                                      help='End date for filtering (YYYY-MM-DD format)')
        parser.add_argument('--top', type=int,
                                     help='Show only top N categories by time spent')
        parser.add_argument('--daily', action='store_true',
                                      help='Show breakdown of time spent per day instead of per category')
        parser.add_argument('--category', action='append',  # Changed to action='append'
                                      help='Filter results to include entries from the specified category (can be used multiple times)')
        parser.add_argument('--format',
                                      choices=['text', 'json'],
                                      default='text',
                                      help='Output format (text or json)')
        parser.add_argument('--save',
                            metavar='FILEPATH',
                            help='Save the output to a file instead of displaying it')

    def execute(self, args):
        """Execute the analytics command."""
        # Validate date format if provided
        from_date = None
        to_date = None

        # Parse and validate from_date if provided
        if hasattr(args, 'from_date') and args.from_date:
            try:
                from_date = dt.strptime(args.from_date, '%Y-%m-%d').date()
            except ValueError:
                self._output_error("Invalid date format for --from. Please use YYYY-MM-DD format.", args)
                return

        # Parse and validate to_date if provided
        if hasattr(args, 'to_date') and args.to_date:
            try:
                to_date = dt.strptime(args.to_date, '%Y-%m-%d').date()
            except ValueError:
                self._output_error("Invalid date format for --to. Please use YYYY-MM-DD format.", args)
                return

        # Check if date range is valid (from_date <= to_date)
        if from_date and to_date and from_date > to_date:
            self._output_error(f"Start date ({args.from_date}) is after end date ({args.to_date}).", args)
            return

        # Validate top N parameter if provided
        top_n = None
        if hasattr(args, 'top') and args.top is not None:
            if args.top <= 0:
                self._output_error("--top must be a positive integer.", args)
                return
            top_n = args.top

        # Get category filters if provided (may be multiple or None)
        category_filters = None
        if hasattr(args, 'category') and args.category:
            category_filters = args.category

        # Check if daily breakdown is requested
        daily_breakdown = hasattr(args, 'daily') and args.daily

        # If daily breakdown is enabled, ignore top_n (as specified in requirements)
        if daily_breakdown:
            top_n = None

        # Determine output format
        output_format = getattr(args, 'format', 'text')

        # Check if file output is requested
        save_filepath = getattr(args, 'save', None)

        # Validate combination of format and save
        if save_filepath and output_format != 'text':
            self._output_error("--save can only be used with text format, not with --format json", args)
            return

        # Get all time entries
        logs = self._get_logs()

        if not logs:
            self._output_error("No log entries found.", args)
            return

        # Filter logs by date range if specified
        filtered_logs = self._filter_logs_by_date_range(logs, from_date, to_date)

        if not filtered_logs:
            self._output_error("No log entries found in the specified date range.", args)
            return

        # Filter logs by categories if specified
        if category_filters:
            filtered_logs = self._filter_logs_by_categories(filtered_logs, category_filters)

            if not filtered_logs:
                self._output_error("No entries found for the specified categories.", args)
                return

        # Process logs based on breakdown type
        if daily_breakdown:
            # Calculate time spent per day
            daily_times = self._calculate_time_per_day(filtered_logs)

            # Handle output based on format and destination
            if output_format == 'json':
                if save_filepath:
                    self._save_daily_json_to_file(daily_times, save_filepath)
                else:
                    self._output_daily_json(daily_times)
            else:  # text format
                if save_filepath:
                    self._save_daily_text_to_file(daily_times, category_filters, save_filepath)
                else:
                    self._display_daily_text(daily_times, category_filters)
        else:
            # Calculate time spent per category
            category_times = self._calculate_time_per_category(filtered_logs)

            # Apply top_n limit if specified
            if top_n is not None:
                category_times = self._apply_top_n_limit(category_times, top_n)

            # Handle output based on format and destination
            if output_format == 'json':
                if save_filepath:
                    self._save_category_json_to_file(category_times, save_filepath)
                else:
                    self._output_category_json(category_times)
            else:  # text format
                if save_filepath:
                    self._save_category_text_to_file(category_times, category_filters, save_filepath)
                else:
                    self._display_category_text(category_times, category_filters)

    def _output_error(self, message, args):
        """Output an error message in the appropriate format.

        Args:
            message: The error message to display
            args: Command arguments that may specify output format
        """
        if hasattr(args, 'format') and args.format == 'json':
            error_json = {
                "error": message
            }
            print(json.dumps(error_json, indent=2))
        else:
            print(f"Error: {message}")

    def _apply_top_n_limit(self, time_dict, top_n):
        """Apply a top N limit to a dictionary of times.

        Args:
            time_dict: Dictionary with keys and time values
            top_n: Maximum number of entries to keep (by highest time)

        Returns:
            Filtered dictionary with at most top_n entries
        """
        # Sort items by time spent (descending)
        sorted_items = sorted(time_dict.items(),
                              key=lambda x: x[1],
                              reverse=True)

        # Apply the limit if necessary
        if top_n is not None and top_n < len(sorted_items):
            sorted_items = sorted_items[:top_n]

        # Convert back to dictionary
        return dict(sorted_items)

    def _format_time(self, hours):
        """Format time in hours as 'Xh Ym' format.

        Args:
            hours: Time in decimal hours

        Returns:
            Formatted time string
        """
        total_hours = int(hours)
        total_minutes = int((hours - total_hours) * 60)

        return f"{total_hours}h {total_minutes}m"

    def _filter_logs_by_date_range(self, logs, from_date, to_date):
        """Filter logs to include only those within the specified date range.

        Args:
            logs: List of time entry objects
            from_date: Start date for filtering (inclusive), or None for no start limit
            to_date: End date for filtering (inclusive), or None for no end limit

        Returns:
            Filtered list of time entry objects
        """
        if not from_date and not to_date:
            return logs  # No filtering needed

        filtered_logs = []

        for entry in logs:
            # Parse the entry date from string (assuming entry.date is in YYYY-MM-DD format)
            # Actual implementation will depend on how dates are stored in your TimeEntry class
            try:
                entry_date = dt.strptime(entry['date'], '%Y-%m-%d').date()
            except (ValueError, AttributeError):
                # Skip entries with invalid dates
                continue

            # Apply date range filtering
            if from_date and entry_date < from_date:
                continue  # Skip entries before from_date
            if to_date and entry_date > to_date:
                continue  # Skip entries after to_date

            filtered_logs.append(entry)

        return filtered_logs

    def _filter_logs_by_categories(self, logs, categories):
        """Filter logs to include only those matching any of the specified categories.

        Args:
            logs: List of time entry objects
            categories: List of category names to filter by

        Returns:
            Filtered list of time entry objects
        """
        if not categories:
            return logs  # No category filtering needed

        filtered_logs = []

        # Convert all category filters to lowercase for case-insensitive matching
        lowercase_categories = [cat.lower() for cat in categories]

        for entry in logs:
            # Get the entry category (or empty string if None)
            entry_category = entry.get("category", "")

            # Check if the entry's category matches any of the filters
            if entry_category.lower() in lowercase_categories:
                filtered_logs.append(entry)

        return filtered_logs

    def _calculate_time_per_category(self, logs):
        """Calculate the total time spent per category across all log entries.

        Args:
            logs: List of time entry objects

        Returns:
            Dictionary with categories as keys and total time (in hours) as values
        """
        category_times = defaultdict(float)

        for entry in logs:
            # Get the category (or 'uncategorized' if None)
            category = entry.get('category', 'uncategorized')

            # Add the duration to the category total
            category_times[category] += float(entry['duration'])

        # Round each category's time to the nearest 15 minutes (0.25 hours)
        rounded_times = {}
        for category, total_time in category_times.items():
            # Round to nearest 0.25 (15 minutes)
            rounded_time = round(total_time * 4) / 4
            rounded_times[category] = rounded_time

        return rounded_times

    def _calculate_time_per_day(self, logs):
        """Calculate the total time spent per day across all log entries.

        Args:
            logs: List of time entry objects

        Returns:
            Dictionary with dates (as strings) as keys and total time (in hours) as values
        """
        daily_times = defaultdict(float)

        for entry in logs:
            # Use the entry's date as the key (assuming it's in YYYY-MM-DD format)
            date_key = entry['date']

            # Add the duration to the daily total
            daily_times[date_key] += float(entry['duration'])

        # Round each day's time to the nearest 15 minutes (0.25 hours)
        rounded_times = {}
        for date_key, total_time in daily_times.items():
            # Round to nearest 0.25 (15 minutes)
            rounded_time = round(total_time * 4) / 4
            rounded_times[date_key] = rounded_time

        return rounded_times

    def _format_category_header(self, category_filters):
        """Format the header for category filtering.

        Args:
            category_filters: List of category names or None

        Returns:
            Formatted header string
        """
        if not category_filters:
            return ""

        if len(category_filters) == 1:
            return f" for category '{category_filters[0]}'"
        else:
            categories_str = "', '".join(category_filters)
            return f" for categories '{categories_str}'"

    def _display_category_text(self, category_times, category_filters=None):
        """Display the total time spent per category in plain text format.

        Args:
            category_times: Dictionary with categories as keys and total times as values
            category_filters: Optional list of category names that were used for filtering
        """
        # Generate the appropriate header based on category filters
        header_suffix = self._format_category_header(category_filters)
        print(f"Time spent per category{header_suffix}:")

        if not category_times:
            print("No log entries found.")
            return

        # Sort categories by time spent (descending)
        sorted_categories = sorted(category_times.items(),
                                   key=lambda x: x[1],
                                   reverse=True)

        for category, hours in sorted_categories:
            # Format and print time
            time_str = self._format_time(hours)
            print(f"{category}: {time_str}")

    def _display_daily_text(self, daily_times, category_filters=None):
        """Display the total time spent per day in plain text format.

        Args:
            daily_times: Dictionary with dates as keys and total times as values
            category_filters: Optional list of category names that were used for filtering
        """
        # Generate the appropriate header based on category filters
        header_suffix = self._format_category_header(category_filters)
        print(f"Time spent per day{header_suffix}:")

        if not daily_times:
            print("No log entries found.")
            return

        # Sort days chronologically (ascending by date)
        sorted_days = sorted(daily_times.items(), key=lambda x: x[0])

        for date_str, hours in sorted_days:
            # Format and print time
            time_str = self._format_time(hours)
            print(f"{date_str}: {time_str}")

    def _output_category_json(self, category_times):
        """Output the total time spent per category in JSON format.

        Args:
            category_times: Dictionary with categories as keys and total times as values
        """
        # Create a data dictionary with formatted time values
        data = {}
        for category, hours in category_times.items():
            data[category] = self._format_time(hours)

        # Create the JSON structure
        result = {
            "summary_type": "category",
            "data": data
        }

        # Output the JSON
        print(json.dumps(result, indent=2))

    def _output_daily_json(self, daily_times):
        """Output the total time spent per day in JSON format.

        Args:
            daily_times: Dictionary with dates as keys and total times as values
        """
        # Create a data dictionary with formatted time values
        # Sort days chronologically
        sorted_days = sorted(daily_times.items())

        data = {}
        for date_str, hours in sorted_days:
            data[date_str] = self._format_time(hours)

        # Create the JSON structure
        result = {
            "summary_type": "daily",
            "data": data
        }

        # Output the JSON
        print(json.dumps(result, indent=2))

    def _generate_category_text(self, category_times, category_filters=None):
        """Generate the total time spent per category as plain text.

        Args:
            category_times: Dictionary with categories as keys and total times as values
            category_filters: Optional list of category names that were used for filtering

        Returns:
            String containing the formatted text output
        """
        # Use StringIO to capture the output
        output = io.StringIO()

        # Generate the appropriate header based on category filters
        header_suffix = self._format_category_header(category_filters)
        print(f"Time spent per category{header_suffix}:", file=output)

        if not category_times:
            print("No log entries found.", file=output)
            return output.getvalue()

        # Sort categories by time spent (descending)
        sorted_categories = sorted(category_times.items(),
                                   key=lambda x: x[1],
                                   reverse=True)

        for category, hours in sorted_categories:
            # Format and print time
            time_str = self._format_time(hours)
            print(f"{category}: {time_str}", file=output)

        return output.getvalue()

    def _generate_daily_text(self, daily_times, category_filters=None):
        """Generate the total time spent per day as plain text.

        Args:
            daily_times: Dictionary with dates as keys and total times as values
            category_filters: Optional list of category names that were used for filtering

        Returns:
            String containing the formatted text output
        """
        # Use StringIO to capture the output
        output = io.StringIO()

        # Generate the appropriate header based on category filters
        header_suffix = self._format_category_header(category_filters)
        print(f"Time spent per day{header_suffix}:", file=output)

        if not daily_times:
            print("No log entries found.", file=output)
            return output.getvalue()

        # Sort days chronologically (ascending by date)
        sorted_days = sorted(daily_times.items(), key=lambda x: x[0])

        for date_str, hours in sorted_days:
            # Format and print time
            time_str = self._format_time(hours)
            print(f"{date_str}: {time_str}", file=output)

        return output.getvalue()

    def _save_category_text_to_file(self, category_times, category_filters, filepath):
        """Save the total time spent per category as plain text to a file.

        Args:
            category_times: Dictionary with categories as keys and total times as values
            category_filters: Optional list of category names that were used for filtering
            filepath: Path to the file where the output should be saved
        """
        # Generate the text output
        text_output = self._generate_category_text(category_times, category_filters)

        # Write to file
        try:
            with open(filepath, 'w') as f:
                f.write(text_output)
            print(f"Analytics report saved to {filepath}")
        except Exception as e:
            self._output_error(f"Could not write to file {filepath}: {str(e)}",
                               type('Args', (), {'save': filepath, 'format': 'text'}))

    def _save_daily_text_to_file(self, daily_times, category_filters, filepath):
        """Save the total time spent per day as plain text to a file.

        Args:
            daily_times: Dictionary with dates as keys and total times as values
            category_filters: Optional list of category names that were used for filtering
            filepath: Path to the file where the output should be saved
        """
        # Generate the text output
        text_output = self._generate_daily_text(daily_times, category_filters)

        # Write to file
        try:
            with open(filepath, 'w') as f:
                f.write(text_output)
            print(f"Analytics report saved to {filepath}")
        except Exception as e:
            self._output_error(f"Could not write to file {filepath}: {str(e)}",
                               type('Args', (), {'save': filepath, 'format': 'text'}))

    def _create_category_json(self, category_times):
        """Create a JSON structure for category data.

        Args:
            category_times: Dictionary with categories as keys and total times as values

        Returns:
            Dictionary with the JSON structure
        """
        # Create a data dictionary with formatted time values
        data = {}
        for category, hours in category_times.items():
            data[category] = self._format_time(hours)

        # Create the JSON structure
        return {
            "summary_type": "category",
            "data": data
        }

    def _create_daily_json(self, daily_times):
        """Create a JSON structure for daily data.

        Args:
            daily_times: Dictionary with dates as keys and total times as values

        Returns:
            Dictionary with the JSON structure
        """
        # Create a data dictionary with formatted time values
        # Sort days chronologically
        sorted_days = sorted(daily_times.items())

        data = {}
        for date_str, hours in sorted_days:
            data[date_str] = self._format_time(hours)

        # Create the JSON structure
        return {
            "summary_type": "daily",
            "data": data
        }

    def _output_category_json(self, category_times):
        """Output the total time spent per category in JSON format to the console.

        Args:
            category_times: Dictionary with categories as keys and total times as values
        """
        # Create the JSON structure
        result = self._create_category_json(category_times)

        # Output the JSON
        print(json.dumps(result, indent=2))

    def _output_daily_json(self, daily_times):
        """Output the total time spent per day in JSON format to the console.

        Args:
            daily_times: Dictionary with dates as keys and total times as values
        """
        # Create the JSON structure
        result = self._create_daily_json(daily_times)

        # Output the JSON
        print(json.dumps(result, indent=2))

    def _save_category_json_to_file(self, category_times, filepath):
        """Save the total time spent per category in JSON format to a file.

        Args:
            category_times: Dictionary with categories as keys and total times as values
            filepath: Path to the file where the output should be saved
        """
        # Create the JSON structure
        result = self._create_category_json(category_times)

        # Write to file
        try:
            with open(filepath, 'w') as f:
                json.dump(result, f, indent=2)
            print(f"Analytics report saved to {filepath}")
        except Exception as e:
            self._output_error(f"Could not write to file {filepath}: {str(e)}",
                               type('Args', (), {'save': filepath, 'format': 'json'}))

    def _save_daily_json_to_file(self, daily_times, filepath):
        """Save the total time spent per day in JSON format to a file.

        Args:
            daily_times: Dictionary with dates as keys and total times as values
            filepath: Path to the file where the output should be saved
        """
        # Create the JSON structure
        result = self._create_daily_json(daily_times)

        # Write to file
        try:
            with open(filepath, 'w') as f:
                json.dump(result, f, indent=2)
            print(f"Analytics report saved to {filepath}")
        except Exception as e:
            self._output_error(f"Could not write to file {filepath}: {str(e)}",
                               type('Args', (), {'save': filepath, 'format': 'json'}))

    def _get_logs(self):
        """Retrieve all time entries from the storage."""
        # In a real implementation, this would load from a database or file
        # This should be replaced with actual log loading code
        # For example, by using a data storage service or manager

        from storage import load_logs
        logs = load_logs()
        if not logs:
            return []  # Replace with actual implementation
        return logs
