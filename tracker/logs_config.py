"""Configuration for application-wide logging.

This module sets up basic logging configuration using the `logging` module.
It configures a root logger to output messages of INFO level and above to
the console. A logger instance named after this module (`tracker.logs_config`)
is also created for potential specific use, although typically, other modules
should obtain their own loggers using `logging.getLogger(__name__)`.
"""
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
