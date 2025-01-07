from tabulate import tabulate

from tracker.logs_config import logger


class Display:
    """
    Handles the display of email data in the terminal.
    """

    @staticmethod
    def display_summary(rows) -> None:
        """
        Display a summary of all processed emails.
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
