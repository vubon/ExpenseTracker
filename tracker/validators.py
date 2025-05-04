import functools
import calendar


def validate_sender_email(func):
    """
      A decorator to validate the presence of a `sender_email` attribute in the first argument of the wrapped function.

      This decorator ensures that:
      - The first argument passed to the function is an instance of a class.
      - The instance has a `sender_email` attribute with a non-empty value.

      Args:
          func (callable): The function to be wrapped by the decorator.

      Returns:
          callable: The wrapped function with validation applied to the `sender_email` attribute.

      Raises:
          ValueError: If the first argument is not an instance of a class or if the `sender_email` attribute is missing or empty.

      Notes:
          - The `sender_email` attribute is expected to be present in the first argument of the wrapped function.
          - If the validation fails, a `ValueError` is raised with an appropriate error message.
    """
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        instance = args[0] if args else None
        if instance is None or not hasattr(instance, "__class__"):
            raise ValueError("First argument must be an instance of the class.")

        sender_email = instance.sender_email if hasattr(instance, 'sender_email') else None
        if not sender_email:
            raise ValueError("Missing environment variable: ET_SENDER_EMAIL")
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
        # Get month and year from kwargs or args
        month = kwargs.get('month') or (args[1] if len(args) > 0 else None)
        year = kwargs.get('year') or (args[2] if len(args) > 1 else None)

        # Validate year
        if not isinstance(year, int)  or len(str(year)) != 4:
            raise ValueError(f"Invalid year format: '{year}'. Year must be a 4-digit string.")

        # Validate month
        valid_months = [i for i in range(1, 13)]
        valid_month_names = [m.lower() for m in calendar.month_name if m]

        if isinstance(month, int):
            if month not in valid_months:
                raise ValueError(f"Invalid month: '{month}'. Must be '01'-'12' or full month name.")
        elif isinstance(month, str):
            if month.lower() not in valid_month_names:
                raise ValueError(f"Invalid month: '{month}'. Must be '01'-'12' or full month name.")
        else:
            raise ValueError(f"Month must be a string. Got {type(month)} instead.")

        return func(*args, **kwargs)

    return wrapper


def validate_args(args) -> tuple:
    """
        Validates the combination of arguments provided to the function.

        Args:
            args: An object containing the following attributes:
                - interval (bool): Indicates if the interval mode is enabled.
                - month (str or None): The month value, expected as a string.
                - year (str or None): The year value, expected as a string.

        Returns:
            tuple: A tuple containing:
                - str: The validation result, which can be one of:
                    - "error": Indicates an invalid combination of arguments.
                    - "continuous": Indicates the interval mode is valid.
                    - "monthly": Indicates the month and year combination is valid.
                - str or None: An error message if the result is "error", otherwise None.

        Raises:
            ValueError: If the arguments do not meet the required conditions.

        Notes:
            - The function ensures that `--interval` cannot be used together with `--month` or `--year`.
            - If `--interval` is provided, it returns "continuous".
            - If both `--month` and `--year` are provided, it returns "monthly".
            - If neither condition is met, it returns an error with an appropriate message.
    """

    has_interval = 'interval' in args
    has_month = 'month' in args
    has_year = 'year' in args

    if has_interval and (has_month or has_year):
        return "error", "Cannot use --interval with --month/--year together."
    elif has_interval:
        return "continuous", None
    elif has_month and has_year:
        return "monthly", None
    else:
        return "continuous", None
