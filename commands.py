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
import json
import sys
from abc import ABC, abstractmethod
from typing import List, Dict, Any

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
            date_obj = datetime.datetime.date.fromisoformat(args.date)
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

    def execute(self, args):
        """Execute the delete command with the given arguments."""
        # Check if at least one filter is provided
        if not (args.id or args.category or args.date):
            print("Error: At least one filter (--id, --category, or --date) must be provided.")
            return

        # Get all time entries
        logs = self._get_logs()

        if not logs:
            print("No entries found.")
            return

        # Make a copy of the logs to preserve the original list
        original_logs = logs.copy()

        # Apply filters to identify entries to delete
        if args.id:
            logs = [log for log in logs if str(log['id']) != args.id]

        if args.category:
            logs = [log for log in logs if log['category'] != args.category]

        if args.date:
            logs = [log for log in logs if str(log['date']) != args.date]

        # Calculate how many entries were deleted
        deleted_count = len(original_logs) - len(logs)

        if deleted_count == 0:
            print("No matching entries found to delete.")
            return

        # Handle dry run vs. actual deletion
        if args.dry_run:
            # Create appropriate message based on which filters were used
            if args.id:
                print(f"Entry with ID {args.id} would be deleted.")
            elif args.category and args.date:
                print(
                    f"{deleted_count} {'entry' if deleted_count == 1 else 'entries'} from category '{args.category}' on {args.date} would be deleted.")
            elif args.category:
                print(
                    f"{deleted_count} {'entry' if deleted_count == 1 else 'entries'} from category '{args.category}' would be deleted.")
            elif args.date:
                print(
                    f"{deleted_count} {'entry' if deleted_count == 1 else 'entries'} dated {args.date} would be deleted.")
            else:
                print(f"{deleted_count} {'entry' if deleted_count == 1 else 'entries'} would be deleted.")

            print("No data was modified (dry run mode).")
        else:
            # Perform actual deletion by saving the remaining logs
            self._save_logs(logs)

            # Display confirmation
            print(f"Successfully removed {deleted_count} {'entry' if deleted_count == 1 else 'entries'}.")
        # Display confirmation
        print(f"Successfully removed {deleted_count} {'entry' if deleted_count == 1 else 'entries'}.")

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
