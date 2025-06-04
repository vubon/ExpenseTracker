from tabulate import tabulate

from tracker.logs_config import logger


class Display:
    """Provides functionality for displaying data in the terminal."""

    @staticmethod
    def display_summary(rows: list[tuple[str, float]]) -> None:
        """Displays a summary of financial data in a tabulated format.

        If no rows are provided, it logs a message and returns. Otherwise,
        it calculates the total amount from the rows, formats the data
        (capitalizing category names and formatting amounts to two decimal
        places with commas), and prints a table to the console using
        the `tabulate` library with a "fancy_grid" style.

        Args:
            rows (list[tuple[str, float]]): A list of tuples, where each
                tuple contains a category name (str) and an amount (float).
                Example: `[("Groceries", 50.75), ("Utilities", 120.00)]`
        """
        if not rows:
            logger.info("No data to display.")
            return

        # Calculate the total amount
        total_amount = sum(row[1] for row in rows)

        # Prepare the data
        data = [[row[0].title(), f"{row[1]:,.2f}"] for row in rows]
        data.append(["Total", f"{total_amount:,.2f}"])

        # Display data
        headers = ["Category", "Total Amount"]
        print(tabulate(data, headers=headers, tablefmt="fancy_grid"))
