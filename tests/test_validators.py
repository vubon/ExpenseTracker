import unittest
from argparse import Namespace
from tracker.validators import validate_month_year, validate_args, validate_sender_email


class TestValidateSenderEmail(unittest.TestCase):
    def test_valid_sender_email(self):
        class DummyClass:
            sender_email = "test@example.com"

        @validate_sender_email
        def dummy_function(obj):
            return "Function executed"

        instance = DummyClass()
        self.assertEqual(dummy_function(instance), "Function executed")

    def test_missing_sender_email_attribute(self):
        class DummyClass:
            pass

        @validate_sender_email
        def dummy_function(obj):
            return "Function executed"

        instance = DummyClass()
        with self.assertRaises(ValueError) as context:
            dummy_function(instance)
        self.assertEqual(str(context.exception), "Missing environment variable: ET_SENDER_EMAIL")

    def test_empty_sender_email(self):
        class DummyClass:
            sender_email = ""

        @validate_sender_email
        def dummy_function(obj):
            return "Function executed"

        instance = DummyClass()
        with self.assertRaises(ValueError) as context:
            dummy_function(instance)
        self.assertEqual(str(context.exception), "Missing environment variable: ET_SENDER_EMAIL")

    def test_invalid_first_argument(self):
        @validate_sender_email
        def dummy_function():
            return "Function executed"

        with self.assertRaises(ValueError) as context:
            dummy_function()

        self.assertEqual(str(context.exception), "First argument must be an instance of the class.")


class TestValidateMonthYear(unittest.TestCase):
    def test_validate_month_year_valid_inputs(self):
        @validate_month_year
        def dummy_function(self, month, year):
            return f"Month: {month}, Year: {year}"

        self.assertEqual(dummy_function(self, 1, 2023), "Month: 1, Year: 2023")
        self.assertEqual(dummy_function(self,"January", 2023), "Month: January, Year: 2023")

    def test_validate_month_year_invalid_year(self):
        @validate_month_year
        def dummy_function(self,month, year):
            return f"Month: {month}, Year: {year}"

        with self.assertRaises(ValueError) as context:
            dummy_function(self, 1, 23)
        self.assertEqual(str(context.exception), "Invalid year format: '23'. Year must be a 4-digit string.")

    def test_validate_month_year_invalid_month(self):
        @validate_month_year
        def dummy_function(self, month, year):
            return f"Month: {month}, Year: {year}"

        with self.assertRaises(ValueError) as context:
            dummy_function(self, 13, 2023)
        self.assertEqual(str(context.exception), "Invalid month: '13'. Must be '01'-'12' or full month name.")

        with self.assertRaises(ValueError) as context:
            dummy_function(self,"InvalidMonth", 2023)
        self.assertEqual(str(context.exception), "Invalid month: 'InvalidMonth'. Must be '01'-'12' or full month name.")

    def test_validate_month_year_invalid_month_type(self):
        @validate_month_year
        def dummy_function(self, month, year):
            return f"Month: {month}, Year: {year}"

        with self.assertRaises(ValueError) as context:
            dummy_function(self,[], 2023)
        self.assertEqual(str(context.exception), "Month must be a string. Got <class 'list'> instead.")


class TestValidateArgs(unittest.TestCase):
    def test_validate_args_with_interval(self):
        args = Namespace(interval=30)
        self.assertEqual(validate_args(args), ("continuous", None))

    def test_validate_args_with_month_and_year(self):
        args = Namespace(month=1, year=2023)
        self.assertEqual(validate_args(args), ("monthly", None))

    def test_validate_args_with_interval_and_month(self):
        args = Namespace(interval=30, month=1)
        self.assertEqual(validate_args(args), ("error", "Cannot use --interval with --month/--year together."))

    def test_validate_args_with_no_args(self):
        args = Namespace()
        self.assertEqual(validate_args(args), ("continuous", None))

    def test_validate_args_with_month_only(self):
        args = Namespace(month=1)
        self.assertEqual(validate_args(args), ("error", "Both --month and --year are required together."))

    def test_validate_args_with_year_only(self):
        args = Namespace(year=2023)
        self.assertEqual(validate_args(args), ("error", "Both --month and --year are required together."))


