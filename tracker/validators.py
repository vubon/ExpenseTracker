"""Decorators and functions for validating inputs.

This module provides a set of decorators and utility functions to ensure
that data passed to various parts of the application (e.g., command-line
arguments, function parameters, instance attributes) meets specific criteria.
"""
import functools
import calendar


def validate_sender_email(func: callable) -> callable:
    """Decorator to validate the `sender_email` attribute of an instance.

    This decorator is intended to be used on methods of a class where the
    first argument (`args[0]`) is the instance of the class (`self`).
    It checks if the instance has a `sender_email` attribute and if that
    attribute is non-empty.

    Args:
        func (callable): The function to be decorated.

    Returns:
        callable: The wrapped function with sender email validation.

    Raises:
        ValueError: If the first argument is not a class instance, or if
            the `sender_email` attribute is missing or empty.
    """
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        instance = args[0] if args else None
        if instance is None or not hasattr(instance, "__class__"):
            raise ValueError("Decorator usage error: `validate_sender_email` must be applied to an instance method where the instance possesses a `sender_email` attribute.")

        sender_email = instance.sender_email if hasattr(instance, 'sender_email') else None
        if not sender_email:
            raise ValueError("Configuration error: The sender email is not set. Please ensure the `ET_SENDER_EMAIL` environment variable is correctly configured.")
        return func(*args, **kwargs)
    return wrapper


def validate_month_year(func):
    """
       A decorator to validate the `month` and `year` arguments passed to a function.

       This decorator ensures that:
       - The `year` argument is a 4-digit integer.
       - The `month` argument is either an integer between 1 and 12 or a valid full month name (case-insensitive).

       Args:
           func (callable): The function to be wrapped by the decorator.

       Returns:
           callable: The wrapped function with validation applied to its `month` and `year` arguments.

       Raises:
           ValueError: If the `month` or `year` arguments are invalid.

       Notes:
           - The `month` and `year` arguments can be passed as keyword arguments (`kwargs`) or positional arguments (`args`).
           - If the validation fails, a `ValueError` is raised with an appropriate error message.
    """
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        # Assumes the instance is the first argument, typically 'self'
        # For ExpenseTracker, month is args[1] and year is args[2] if passed positionally
        # For run_monthly_summary, month is args[0] and year is args[1] (after self if it were a method)
        # This decorator is designed for methods like ExpenseTracker.get_monthly_summary

        month = None
        year = None

        if 'month' in kwargs and 'year' in kwargs:
            month = kwargs['month']
            year = kwargs['year']
        elif len(args) >= 3: # self, month, year
            month = args[1]
            year = args[2]
        elif len(args) == 2 and isinstance(args[0], int) and isinstance(args[1], int): # module level function: month, year
             month = args[0]
             year = args[1]
        else:
            # Try to get from instance if it's a method and not passed directly
            instance = args[0] if args and hasattr(args[0], "__class__") else None
            if instance:
                 month = getattr(instance, 'month', None)
                 year = getattr(instance, 'year', None)

        if month is None or year is None:
            # This error message can remain generic as it's a precondition for the specific validations below.
            raise ValueError("Month and year arguments must be provided either positionally or as keywords.")

        # Validate year
        if not isinstance(year, int) or len(str(year)) != 4:
            raise ValueError(f"Invalid year: '{year}'. Year must be a 4-digit integer (e.g., 2023).")

        # Validate month
        valid_months_int = list(range(1, 13))
        valid_month_names_str = [m.lower() for m in calendar.month_name if m]

        if isinstance(month, int):
            if month not in valid_months_int:
                raise ValueError(f"Invalid month: '{month}'. Must be an integer between 1 and 12.")
        elif isinstance(month, str):
            if month.lower() not in valid_month_names_str:
                raise ValueError(f"Invalid month name: '{month}'. Please use a full, case-insensitive month name (e.g., 'January', 'February').")
        else:
            raise ValueError(f"Invalid month type: '{type(month).__name__}'. Month must be an integer (1-12) or a string (full month name).")

        return func(*args, **kwargs)

    return wrapper


def validate_args(args: object) -> tuple[str, str | None]:
    """Validates command-line argument combinations for the expense tracker.

    This function checks if the provided arguments for continuous mode
    (using `--interval`) and monthly summary mode (using `--month` and `--year`)
    are used correctly and not in conflicting ways.

    Args:
        args: An object (typically `argparse.Namespace`) containing parsed
            command-line arguments. Expected attributes include `interval`,
            `month`, and `year`, which may or may not be present depending
            on user input.

    Returns:
        tuple[str, str | None]: A tuple where the first element is a string
            indicating the determined mode ("continuous", "monthly", or "error"),
            and the second element is an error message string if the mode is
            "error", otherwise None.
    """
    has_interval = hasattr(args, 'interval')
    has_month = hasattr(args, 'month')
    has_year = 'year' in args

    if has_interval and (has_month or has_year):
        return "error", "Cannot use --interval with --month/--year together."
    elif has_interval:
        return "continuous", None
    elif has_month and has_year:
        return "monthly", None
    else:
        return "continuous", None
