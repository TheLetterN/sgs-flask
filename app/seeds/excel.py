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
    sheet.col_map = dict()
    for i, val in enumerate(values):
        cell = sheet.cell(row=1, column=i + 1)
        sheet.col_map[val] = cell.column
        cell.value = val
        if val in textcols:
            sheet.column_dimensions[cell.column].width = textwidth
        else:
            sheet.column_dimensions[cell.column].width = len(val) + padding
    sheet.freeze_panes = sheet['A2']


def set_sheet_col_map(sheet):
    """Sets up column map using sheet's header row."""
    if not sheet.rows[0] or any([not cell.value for cell in sheet.rows[0]]):
        raise ValueError('One or more empty cells present in header row '
                         'of worksheet!')
    sheet.col_map = {cell.value: cell.column for cell in sheet.rows[0]}


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
        self.setup_indexes()
        self.setup_common_names()
        self.setup_botanical_names()
        self.setup_series()
        self.setup_cultivars()
        self.setup_packets()

    def setup_indexes(self):
        """Set up Indexes worksheet."""
        if 'Indexes' not in self.wb.sheetnames:
            try:
                self.indexes = self.wb.get_sheet_by_name('Sheet')
                self.indexes.title = 'Indexes'
            except KeyError:
                self.indexes = self.wb.create_sheet(title='Indexes')
            setup_sheet(self.indexes,
                        ('Index', 'Description'),
                        padding=4)
        else:
            raise RuntimeError('A worksheet named \'Indexes\' already exists!')

    def setup_common_names(self):
        """Set up CommonNames worksheet."""
        if 'CommonNames' not in self.wb.sheetnames:
            self.common_names = self.wb.create_sheet(title='CommonNames')
            setup_sheet(self.common_names,
                        ('Index',
                         'Common Name',
                         'Subcategory of',
                         'Description',
                         'Planting Instructions',
                         'Synonyms',
                         'Grows With Common Names',
                         'Grows With Cultivars',
                         'Invisible'),
                        padding=4)
        else:
            raise RuntimeError('A worksheet named \'CommonNames\' already '
                               'exists!')

    def setup_botanical_names(self):
        """Set up BotanicalNames worksheet."""
        if 'BotanicalNames' not in self.wb.sheetnames:
            self.botanical_names = self.wb.create_sheet(title='BotanicalNames')
            setup_sheet(self.botanical_names,
                        ('Common Names',
                         'Botanical Name',
                         'Synonyms'),
                        padding=4)
        else:
            raise RuntimeError('A worksheet named \'BotanicalNames\' already '
                               'exists!')

    def setup_series(self):
        """Set up Series worksheet."""
        if 'Series' not in self.wb.sheetnames:
            self.series = self.wb.create_sheet(title='Series')
            setup_sheet(self.series,
                        ('Common Name',
                         'Series',
                         'Position',
                         'Description'),
                        padding=4)
        else:
            raise RuntimeError('A worksheet named \'Series\' already exists!')

    def setup_cultivars(self):
        """Set up Cultivars worksheet."""
        if 'Cultivars' not in self.wb.sheetnames:
            self.cultivars = self.wb.create_sheet(title='Cultivars')
            setup_sheet(self.cultivars,
                        ('Index',
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
        else:
            raise RuntimeError('A worksheet named \'Cultivars\' already '
                               'exists!')

    def setup_packets(self):
        """Set up Packets worksheet."""
        if 'Packets' not in self.wb.sheetnames:
            self.packets = self.wb.create_sheet(title='Packets')
            setup_sheet(self.packets,
                        ('Cultivar',
                         'SKU',
                         'Price',
                         'Quantity',
                         'Units'),
                        padding=4)
        else:
            raise RuntimeError('A worksheet named \'Cultivars\' already '
                               'exists!')

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
        try:
            self.indexes = self.wb.get_sheet_by_name('Indexes')
            set_sheet_col_map(self.indexes)
        except KeyError as e:
            print('Warning: Indexes sheet was not loaded because: {0}, so a '
                  'new Indexes sheet has been generated instead.'.format(e))
            self.setup_indexes()
        try:
            self.common_names = self.wb.get_sheet_by_name('CommonNames')
            set_sheet_col_map(self.common_names)
        except KeyError as e:
            print('Warning: CommonNames sheet was not loaded because: {0}, so '
                  'a new CommonNames sheet has been generated instead.'
                  .format(e))
            self.setup_common_names()
        try:
            self.botanical_names = self.wb.get_sheet_by_name('BotanicalNames')
            set_sheet_col_map(self.botanical_names)
        except KeyError as e:
            print('Warning: BotanicalNames sheet was not loaded because: {0}, '
                  'so a new BotanicalNames sheet has been generated instead.'
                  .format(e))
            self.setup_botanical_names()
        try:
            self.series = self.wb.get_sheet_by_name('Series')
            set_sheet_col_map(self.series)
        except KeyError as e:
            print('Warning: Series sheet was not loaded because: {0}, so a '
                  'new Series sheet has been generated instead.'.format(e))
            self.setup_series()
        try:
            self.cultivars = self.wb.get_sheet_by_name('Cultivars')
            set_sheet_col_map(self.cultivars)
        except KeyError as e:
                print('Warning: Cultivars sheet was not loaded because: {0}, '
                      'so a new Cultivars sheet has been generated instead.'
                      .format(e))
                self.setup_cultivars()
        try:
            self.packets = self.wb.get_sheet_by_name('Packets')
            set_sheet_col_map(self.packets)
        except KeyError as e:
                print('Warning: Packets sheet was not loaded because: {0}, so '
                      'a new Packets sheet has been generated instead.'
                      .format(e))

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
            ws.cell(ws.col_map['Index'] + row).value = cn.index.name
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
            if cn.gw_cultivars:
                gwcvs = ', '.join(['[' + gwcv.lookup_string() + ']' for gwcv in
                                   cn.gw_cultivars])
                ws.cell(ws.col_map['Grows With Cultivars'] + row).value = gwcvs
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
            ws.cell(ws.col_map['Index'] + row).value = cv.index.name
            if cv.common_name:
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
            ws.cell(ws.col_map['Cultivar'] + row).value =\
                pkt.cultivar.lookup_string()
            ws.cell(ws.col_map['SKU'] + row).value = pkt.sku
            ws.cell(ws.col_map['Price'] + row).value = pkt.price
            ws.cell(ws.col_map['Quantity'] + row).value =\
                pkt.quantity.str_value
            ws.cell(ws.col_map['Units'] + row).value = pkt.quantity.units
