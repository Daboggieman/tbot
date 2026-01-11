import argparse
import logging

class BaseCommand:
    """
    Base class for all bot commands.
    """
    def __init__(self, parser: argparse.ArgumentParser):
        self.parser = parser
        self.logger = logging.getLogger(self.__class__.__name__)

    def add_arguments(self):
        """
        Register arguments for this command.
        """
        pass

    def execute(self, args, services):
        """
        Execute the command.
        """
        raise NotImplementedError("Subclasses must implement execute(args, services)")
