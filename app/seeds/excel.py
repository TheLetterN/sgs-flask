# This file is part of SGS-Flask.

# SGS-Flask is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# SGS-Flask is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

# Copyright Swallowtail Garden Seeds, Inc


from openpyxl import load_workbook, Workbook


def populate_row(sheet, row, values):
    """Populate a row in a worksheet with a list of values.

    Attributes:
        sheet (Worksheet): The worksheet to populate a row in.
        row (int): The number of the row to populate.
        values (iterable type): A list of values to populate """
    for i in range(1, len(values) + 1):
        sheet.cell(row=row, column=i).value = values[i - 1]


def set_column_widths(sheet, row, padding=0):
    """Set column widths of sheet using contents of row.

    Attributes:
        sheet (Worksheet): The worksheet to set column widths in.
        row (int): The row to base column widths on.
        padding (int): The amount of extra characters to add to column width.
    """
    for cell in sheet.rows[row - 1]:
        sheet.column_dimensions[cell.column].width = len(cell.value) + padding


def setup_sheet(sheet, values, padding=0):
    """Set up the top header row of the given sheet, and populate w/ values.

    Attributes:
        sheet (Worksheet): The worksheet to set up.
        values (iterable): A list of values to populate top row with.
        padding (int): Number of extra spaces to add to cell widths.
    """
    populate_row(sheet, 1, values)
    set_column_widths(sheet, 1, padding)
    sheet.freeze_panes = sheet['A2']


class SeedsWorkbook(object):
    """Excel workbook containing data from the tables in seeds.models."""
    def __init__(self, filename=None):
        if filename is None:
            self.wb = Workbook()
            self.indexes = self.wb.active
            self.indexes.title = 'Indexes'
            setup_sheet(self.indexes, ('Index', 'Description'), padding=4)
            self.common_names = self.wb.create_sheet(title='CommonNames')
            setup_sheet(self.common_names,
                        ('Indexes',
                         'Common Name',
                         'Subcategory of',
                         'Description',
                         'Planting Instructions',
                         'Synonyms',
                         'Grows With Common Names'),
                        padding=4)
            self.cultivars = self.wb.create_sheet(title='Cultivars')
            setup_sheet(self.cultivars,
                        ('Indexes',
                         'Common Name',
                         'Botanical Name',
                         'Series',
                         'Cultivar Name',
                         'Thumbnail Filename',
                         'Description',
                         'Synonyms',
                         'Grows With Common Names',
                         'Grows With Cultivars',
                         'In Stock',
                         'Inactive'),
                        padding=4)
            self.packets = self.wb.create_sheet(title='Packets')
            setup_sheet(self.packets,
                        ('Cultivar',
                         'SKU',
                         'Price',
                         'Quantity',
                         'Units'),
                        padding=4)
        else:
            self.filename=filename

    def load(self, filename=None):
        """Load file specified by filename, or self.filename if None.

        Attributes:
            filename (str): The name of the file to load.
        """
        if filename is None:
            filename = self.filename
        if filename is None:
            raise ValueError('Please specify a filename.')
        self.wb = load_workbook(filename)
        self.indexes = self.wb.get_sheet_by_name('Indexes')
        self.common_names = self.wb.get_sheet_by_name('CommonNames')
        self.cultivars = self.wb.get_sheet_by_name('Cultivars')
        self.packets = self.wb.get_sheet_by_name('Packets')
            
    def save(self, filename=None):
        """Save to file specified by filename, or self.filename if None.

        Attributes:
            filename (str): The name of the file to save.

        Raises:
            ValueError: If no filename is specified, but self.filename does
                not exist.
        """
        if filename is None:
            filename = self.filename
        if filename is None:
            raise ValueError('Please specify a filename.')
        self.wb.save(filename)
