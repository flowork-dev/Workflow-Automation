#######################################################################
# WEBSITE https://flowork.cloud
# File NAME : C:\FLOWORK\flowork-core\formatters\csv_formatter\formatter.py JUMLAH BARIS 24 
#######################################################################

import csv
import io
class CsvFormatter:
    """A formatter for handling CSV data."""
    def parse(self, data_string: str) -> list:
        """Parses a CSV string into a list of dictionaries."""
        reader = csv.DictReader(io.StringIO(data_string))
        return [row for row in reader]
    def stringify(self, data_list: list) -> str:
        """Converts a list of dictionaries into a CSV string."""
        if not data_list:
            return ""
        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=data_list[0].keys())
        writer.writeheader()
        writer.writerows(data_list)
        return output.getvalue()
