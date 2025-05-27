#!/usr/bin/env python3
"""
Task Time Tracker (TTT) - A command-line tool to track time spent on tasks.

This module serves as the main entry point for the TTT application. It handles:
- Command-line argument parsing
- Command execution
- Error handling
- User feedback

The module follows a command-pattern approach, where different commands
are dispatched based on user input.
"""

import sys
from typing import List, Optional

from config import AVAILABLE_COMMANDS
from parser import TaskTrackerParser


def display_command_error(parser, command: Optional[str] = None, available_commands: List[str] = None) -> None:
    """
    Display an error message for invalid or missing commands.

    This utility function presents a user-friendly error message when the user
    provides an invalid command or no command at all. It lists available commands
    and shows the help text.

    Args:
        parser: The argument parser object to display help information.
        command: The invalid command that was provided, if any.
        available_commands: List of valid commands that can be used.

    Returns:
        None. The function exits the program with a non-zero status code.
    """
    if command:
        print(f"Error: Invalid command '{command}'.")
    else:
        print("Error: No command specified.")

    if available_commands:
        print(f"Available commands are: {', '.join(available_commands)}")

    # Display help text
    parser.print_help()
    sys.exit(1)


def main():
    """
    Main entry point for the Task Time Tracker application.

    This function:
    1. Sets up the command-line argument parser
    2. Processes user input
    3. Dispatches to the appropriate command handler
    4. Handles errors gracefully

    Returns:
        None. The function either completes successfully or exits with an error code.
    """
    # Create the parser
    parser_manager = TaskTrackerParser()
    parser = parser_manager.create_parser()

    # Get the list of available commands from the parser (which gets them from config)
    available_commands = list(parser_manager.commands.keys())

    try:
        # Parse arguments
        args = parser.parse_args()

        # If no command was provided, show error and help
        if not args.command:
            display_command_error(parser, None, available_commands)

        # Get the command and execute it
        command = parser_manager.get_command(args.command)
        if command:
            command.execute(args)
        else:
            display_command_error(parser, args.command, available_commands)

    except Exception as e:
        # Show error message but avoid displaying the full traceback to end users
        print(f"Error: {str(e)}")
        sys.exit(1)


if __name__ == '__main__':
    main()