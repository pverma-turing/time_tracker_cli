"""
Command-line argument parser setup for the Task Time Tracker application.

This module handles the creation and configuration of the command-line argument parser
for the application. It sets up the main parser and subparsers for each command,
and provides methods to retrieve command instances based on user input.

The module follows a modular approach, separating the parser setup from command
implementation, which makes the codebase more maintainable and extensible.
"""

import argparse
import importlib
from typing import Dict, Optional

from config import AVAILABLE_COMMANDS
from commands import Command
from version import __version__


class TaskTrackerParser:
    """
    Creates and configures the argument parser for the Task Time Tracker CLI.

    This class is responsible for:
    - Setting up the main argparse parser
    - Adding subparsers for each command
    - Providing access to command instances for execution

    The design allows for easily adding new commands to the application by
    simply updating the AVAILABLE_COMMANDS constant in the config module.
    """

    def __init__(self):
        """
        Initialize the parser with all available commands.

        Creates a dictionary mapping command names to their respective Command instances.
        The commands are dynamically loaded based on the AVAILABLE_COMMANDS constant
        from the config module.
        """
        self.commands: Dict[str, Command] = {}

        # Import command classes dynamically from the commands module
        commands_module = importlib.import_module('commands')

        # Create command instances based on the configuration
        for cmd_name, cmd_class_name in AVAILABLE_COMMANDS.items():
            cmd_class = getattr(commands_module, cmd_class_name)
            self.commands[cmd_name] = cmd_class()

    def create_parser(self) -> argparse.ArgumentParser:
        """
        Create and configure the argument parser with all commands and their arguments.

        This method:
        1. Creates the main parser with program name, description, and epilog
        2. Adds global options like --version flag
        3. Sets up subparsers for each command
        4. Configures each command's specific arguments

        Returns:
            argparse.ArgumentParser: A fully configured argument parser ready for processing
                                     command-line arguments.
        """
        # Create main parser with improved description and epilog
        parser = argparse.ArgumentParser(
            prog='ttt',
            description='Task Time Tracker (TTT) - Track time spent on tasks',
            formatter_class=argparse.RawDescriptionHelpFormatter,
            epilog="Use 'ttt <command> --help' to view options for a specific command."
        )

        # Add version argument that will automatically print version and exit when used
        parser.add_argument('--version', action='version',
                           version=f'%(prog)s {__version__}')

        # Create subparsers with improved help formatting
        subparsers = parser.add_subparsers(
            dest='command',
            title='commands',
            description='valid commands',
            metavar='COMMAND'
        )

        # Add each command's subparser with descriptive help text
        for name, command in self.commands.items():
            subparser = subparsers.add_parser(
                name,
                help=command.get_short_description(),  # Short description for top-level help
                description=command.__doc__            # Full description for command-specific help
            )
            command.add_arguments(subparser)

        return parser

    def get_command(self, command_name: str) -> Optional[Command]:
        """
        Get the command instance for the given command name.

        Args:
            command_name: The name of the command to retrieve.

        Returns:
            Optional[Command]: The Command instance if found, None otherwise.
        """
        return self.commands.get(command_name)