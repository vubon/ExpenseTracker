import unittest
from unittest.mock import patch
from tabulate import tabulate

from tracker.display import Display


class TestDisplay(unittest.TestCase):
    @patch("builtins.print")
    @patch("tracker.logs_config.logger.info")
    def test_display_summary_no_data(self, mock_logger_info, mock_print):
        """
        Test display_summary when no data is provided.
        """
        Display.display_summary([])
        mock_logger_info.assert_called_once_with("No data to display.")
        mock_print.assert_not_called()

    @patch("builtins.print")
    @patch("tracker.logs_config.logger.info")
    def test_display_summary_with_data(self, mock_logger_info, mock_print):
        """
        Test display_summary with valid data.
        """
        rows = [
            ("groceries", 123.45),
            ("rent", 1500.00),
            ("utilities", 300.67),
        ]

        Display.display_summary(rows)

        # Verify logger is not called
        mock_logger_info.assert_not_called()

        # Verify print output
        total_amount = sum(row[1] for row in rows)
        data = [[row[0].title(), f"{row[1]:,.2f}"] for row in rows]
        data.append(["Total", f"{total_amount:,.2f}"])
        headers = ["Category", "Total Amount"]
        expected_output = tabulate(data, headers=headers, tablefmt="fancy_grid")

        mock_print.assert_called_once_with(expected_output)
