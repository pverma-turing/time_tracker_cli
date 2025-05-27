#!/usr/bin/env python3
"""
Task Time Tracker (TTT) - A command-line tool to track time spent on tasks.

This is the main entry point for the application that parses command-line arguments
and delegates to the appropriate command handlers.
"""

import sys

from parser import TaskTrackerParser


def main():
    """Main entry point for the Task Time Tracker application."""
    # Create the parser
    parser_manager = TaskTrackerParser()
    parser = parser_manager.create_parser()

    try:
        # Parse arguments
        args = parser.parse_args()

        # If no command was provided, show help
        if not args.command:
            parser.print_help()
            return

        # Get the command and execute it
        command = parser_manager.get_command(args.command)
        if command:
            command.execute(args)
        else:
            print(f"Error: Unknown command: {args.command}")
            parser.print_help()
            sys.exit(1)

    except Exception as e:
        # Show error message but avoid displaying the full traceback to end users
        print(f"Error: {str(e)}")
        sys.exit(1)


if __name__ == '__main__':
    main()