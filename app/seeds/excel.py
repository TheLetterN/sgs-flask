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


from datetime import datetime
from openpyxl import load_workbook, Workbook
from openpyxl.styles import Alignment
from app.seeds.models import Series


def setup_sheet(sheet,
                values,
                padding=0,
                textwidth=32,
                textcols=['Description', 'Planting Instructions']):
    """Set up the top header row of the given sheet, and populate w/ values.

    Attributes:
        sheet (Worksheet): The worksheet to set up.
        values (list): A list of values to populate top row with.
        padding (int): Number of extra spaces to add to cell widths.
        textwidth (int): The width of columns containing large amounts of text.
        textcols (list): Columns expected to contain large amounts of text.
    """
    columns = dict()
    for i, val in enumerate(values):
        cell = sheet.cell(row=1, column=i + 1)
        columns[val] = cell.column
        cell.value = val
        if val in textcols:
            sheet.column_dimensions[cell.column].width = textwidth
        else:
            sheet.column_dimensions[cell.column].width = len(val) + padding
    sheet.freeze_panes = sheet['A2']
    sheet.col_map = columns


class SeedsWorkbook(object):
    """Excel workbook containing data from the tables in seeds.models."""
    def __init__(self, filename=None, load=False):
        self.filename = filename
        if load:
            self.load(filename)
        else:
            self.setup_workbook()

    def setup_workbook(self):
        """Set up a new workbook with default parameters."""
        self.wb = Workbook()
        self.indexes = self.wb.active
        self.indexes.title = 'Indexes'
        setup_sheet(self.indexes,
                    ('Index', 'Description'),
                    padding=4)
        self.common_names = self.wb.create_sheet(title='CommonNames')
        setup_sheet(self.common_names,
                    ('Indexes',
                     'Common Name',
                     'Subcategory of',
                     'Description',
                     'Planting Instructions',
                     'Synonyms',
                     'Grows With Common Names',
                     'Invisible'),
                    padding=4)
        self.botanical_names = self.wb.create_sheet(title='BotanicalNames')
        setup_sheet(self.botanical_names,
                    ('Common Names',
                     'Botanical Name',
                     'Synonyms'),
                    padding=4)
        self.series = self.wb.create_sheet(title='Series')
        setup_sheet(self.series,
                    ('Common Name',
                     'Series',
                     'Position',
                     'Description'),
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
                     'Inactive',
                     'Invisible'),
                    padding=4)
        self.packets = self.wb.create_sheet(title='Packets')
        setup_sheet(self.packets,
                    ('Cultivar',
                     'SKU',
                     'Price',
                     'Quantity',
                     'Units'),
                    padding=4)

    def beautify(self):
        """Turn on text wrap in cells and set row heights in all sheets."""
        a = Alignment(wrap_text=True, vertical='top')
        for sheet in self.wb:
            for row in sheet.rows[1:]:
                for cell in row:
                    cell.alignment = a
                for i in range(2, len(sheet.rows[1:]) + 2):
                    sheet.row_dimensions[i].height = 32

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

    def save(self, filename=None, append_timestamp=False):
        """Save to file specified by filename, or self.filename if None.

        Attributes:
            filename (str): The name of the file to save.
            append_timestamp (bool): Whether or not to append a timestamp to
                filename.

        Raises:
            ValueError: If no filename is specified, but self.filename does
                not exist.
        """
        if filename is None:
            filename = self.filename
        if filename is None:
            raise ValueError('Please specify a filename.')
        if append_timestamp:
            idx = filename.index('.xlsx')
            ts = datetime.utcnow().strftime('%Y_%m_%d_%H_%M_%S_%f_UTC')
            filename = filename[:idx] + '_' + ts + filename[idx:]
        self.beautify()
        self.wb.save(filename)

    def load_indexes(self, indexes):
        """Populate the Indexes sheet with data from a list of Index objects.

        Attributes:
            indexes (list): A list of Index objects from the database models.
        """
        ws = self.indexes
        for i, idx in enumerate(indexes):
            row = str(i + 2)
            ws.cell(ws.col_map['Index'] + row).value = idx.name
            ws.cell(ws.col_map['Description'] + row).value =\
                idx.description

    def load_common_names(self, common_names):
        """Populate the CommonNames sheet with CommonName object data.

        Attributes:
            common_names (list): A list of CommonName objects from db models.
        """
        ws = self.common_names
        for i, cn in enumerate(common_names):
            row = str(i + 2)
            ws.cell(ws.col_map['Indexes'] + row).value =\
                ', '.join([idx.name for idx in cn.indexes])
            ws.cell(ws.col_map['Common Name'] + row).value = cn.name
            if cn.parent:
                ws.cell(ws.col_map['Subcategory of'] + row).value =\
                    cn.parent.name
            ws.cell(ws.col_map['Description'] + row).value =\
                cn.description
            ws.cell(ws.col_map['Planting Instructions'] + row).value =\
                cn.instructions
            ws.cell(ws.col_map['Synonyms'] + row).value =\
                cn.list_synonyms_as_string()
            if cn.gw_common_names:
                gwcns = ', '.join([gwcn.name for gwcn in cn.gw_common_names])
                ws.cell(ws.col_map['Grows With Common Names'] +
                        row).value = gwcns
            if cn.invisible:
                ws.cell(ws.col_map['Invisible'] + row).value = 'True'

    def load_botanical_names(self, botanical_names):
        """Populate the BotanicalNames sheet with BotanicalName objects.

        Attributes:
            botanical_names (list): A list of BotanicalName objects from db.
        """
        ws = self.botanical_names
        for i, bn in enumerate(botanical_names):
            row = str(i + 2)
            ws.cell(ws.col_map['Common Names'] + row).value =\
                ', '.join([cn.name for cn in bn.common_names])
            ws.cell(ws.col_map['Botanical Name'] + row).value = bn.name
            ws.cell(ws.col_map['Synonyms'] + row).value =\
                bn.list_synonyms_as_string()

    def load_series(self, series):
        """Populate the Series shet with Series objects from db.

        Attributes:
            series (list): A list of Series objects from db.
        """
        ws = self.series
        for i, sr in enumerate(series):
            row = str(i + 2)
            ws.cell(ws.col_map['Common Name'] + row).value =\
                sr.common_name.name
            ws.cell(ws.col_map['Series'] + row).value = sr.name
            ws.cell(ws.col_map['Position'] + row).value = 'after cultivar' if\
                sr.position == Series.AFTER_CULTIVAR else 'before cultivar'
            ws.cell(ws.col_map['Description'] + row).value = sr.description

    def load_cultivars(self, cultivars):
        """Populate the Cultivars sheet with Cultivar object data.

        Attributes:
            cultivars (list): A list of Cultivar objects from db models.
        """
        ws = self.cultivars
        for i, cv in enumerate(cultivars):
            row = str(i + 2)
            ws.cell(ws.col_map['Indexes'] + row).value =\
                ', '.join([idx.name for idx in cv.indexes])
            ws.cell(ws.col_map['Common Name'] + row).value =\
                cv.common_name.name
            if cv.botanical_name:
                ws.cell(ws.col_map['Botanical Name'] + row).value =\
                    cv.botanical_name.name
            if cv.series:
                ws.cell(ws.col_map['Series'] + row).value = cv.series.name
            ws.cell(ws.col_map['Cultivar Name'] + row).value = cv.name
            if cv.thumbnail:
                ws.cell(ws.col_map['Thumbnail Filename'] + row).value =\
                    cv.thumbnail.filename
            ws.cell(ws.col_map['Description'] + row).value =\
                cv.description
            if cv.synonyms:
                ws.cell(ws.col_map['Synonyms'] + row).value =\
                    cv.list_synonyms_as_string()
            if cv.gw_common_names:
                ws.cell(ws.col_map['Grows With Common Names'] + row).value =\
                    ', '.join([cn.name for cn in cv.gw_common_names])
            if cv.gw_cultivars:
                ws.cell(ws.col_map['Grows With Cultivars'] + row).value =\
                    ', '.join([cult.name for cult in cv.gw_cultivars])
            if cv.in_stock:
                ws.cell(ws.col_map['In Stock'] + row).value = 'True'
            if cv.dropped:
                ws.cell(ws.col_map['Inactive'] + row).value = 'True'
            if cv.invisible:
                ws.cell(ws.col_map['Invisible'] + row).value = 'True'

    def load_packets(self, packets):
        """Populate the Packets sheet with Packet object data.

        Attributes:
            packets (list): A list of Packet objects from db models.
        """
        ws = self.packets
        for i, pkt in enumerate(packets):
            row = str(i + 2)
            ws.cell(ws.col_map['Cultivar'] + row).value = pkt.cultivar.fullname
            ws.cell(ws.col_map['SKU'] + row).value = pkt.sku
            ws.cell(ws.col_map['Price'] + row).value = pkt.price
            ws.cell(ws.col_map['Quantity'] + row).value =\
                pkt.quantity.str_value
            ws.cell(ws.col_map['Units'] + row).value = pkt.quantity.units
