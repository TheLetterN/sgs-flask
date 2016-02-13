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


import json
from datetime import datetime
from openpyxl import load_workbook, Workbook
from openpyxl.styles import Alignment
from app import db, dbify
from app.seeds.models import (
    BotanicalName,
    CommonName,
    Cultivar,
    Image,
    Index,
    Packet,
    Quantity,
    save_indexes_to_json,
    Series,
    USDInt
)


def beautify(sheet, height=42):
    """Wrap text in cells, set row heights, and freeze header row."""
    a = Alignment(wrap_text=True, vertical='top')
    for row in sheet.rows[1:]:
        for cell in row:
            cell.alignment = a
        for i in range(2, len(sheet.rows[1:]) + 2):
            sheet.row_dimensions[i].height = height
    sheet.freeze_panes = sheet['A2']


def cell_to_bool(value):
    """Convert the contents of a cell into a boolean value.

    Args:
        value: A string indicating True or False, or None.

    Returns:
        bool: True if value exists & does not contain 'f' (false) or 'n' (no).
            Since 'f' and 'n' are not present in 'true' or 'yes', we will
            assume truthiness in the absence of those characters. If value is
            not truthy or contains 'f' or 'n', False will be returned.
    """
    if value:
        value = value.lower()
        if 'f' not in value and 'n' not in value:
            return True
    return False


def clean_dict(d):
    """Run dbify() on any values that need it.

    d (dict): The dict to clean.
    """
    return {k: dbify(v) if k == 'Index' or
            k == 'Common Name' or
            k == 'Series' or
            k == 'Cultivar Name' else
            v for (k, v) in d.items()}


def get_cell(sheet, column_header, row):
    """Get a cell given its column header name and row #."""
    return sheet.cell(sheet.col_map[column_header] + str(row))

    
def setup_sheet(sheet,
                values,
                padding=0,
                textwidth=32,
                textcols=['Description', 'Planting Instructions']):
    """Set up the top header row of the given sheet, and populate w/ values.

    Args:
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
                        padding=6)
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
                         'Grows With Common Names (JSON)',
                         'Grows With Cultivars (JSON)',
                         'Invisible'),
                        padding=6)
        else:
            raise RuntimeError('A worksheet named \'CommonNames\' already '
                               'exists!')

    def setup_botanical_names(self):
        """Set up BotanicalNames worksheet."""
        if 'BotanicalNames' not in self.wb.sheetnames:
            self.botanical_names = self.wb.create_sheet(title='BotanicalNames')
            setup_sheet(self.botanical_names,
                        ('Common Names (JSON)',
                         'Botanical Name',
                         'Synonyms'),
                        padding=6)
        else:
            raise RuntimeError('A worksheet named \'BotanicalNames\' already '
                               'exists!')

    def setup_series(self):
        """Set up Series worksheet."""
        if 'Series' not in self.wb.sheetnames:
            self.series = self.wb.create_sheet(title='Series')
            setup_sheet(self.series,
                        ('Common Name (JSON)',
                         'Series',
                         'Position',
                         'Description'),
                        padding=6)
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
                         'Grows With Common Names (JSON)',
                         'Grows With Cultivars (JSON)',
                         'New For',
                         'In Stock',
                         'Active',
                         'Invisible'),
                        padding=6)
        else:
            raise RuntimeError('A worksheet named \'Cultivars\' already '
                               'exists!')

    def setup_packets(self):
        """Set up Packets worksheet."""
        if 'Packets' not in self.wb.sheetnames:
            self.packets = self.wb.create_sheet(title='Packets')
            setup_sheet(self.packets,
                        ('Cultivar (JSON)',
                         'SKU',
                         'Price',
                         'Quantity',
                         'Units'),
                        padding=6)
        else:
            raise RuntimeError('A worksheet named \'Cultivars\' already '
                               'exists!')

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

        beautify(self.indexes)
        beautify(self.common_names)
        beautify(self.botanical_names)
        beautify(self.series)
        beautify(self.cultivars)
        beautify(self.packets, height=84)

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
            ws.cell(
                ws.col_map['Description'] + row
            ).value = idx.description

    def dump_indexes(self):
        """Dump Indexes from the Indexes sheet to the database."""
        ws = self.indexes
        commit_to_db = False
        for i in range(2, len(ws.rows) + 1):
            edited = False
            row = str(i)
            name = dbify(ws.cell(ws.col_map['Index'] + row).value)
            desc = ws.cell(ws.col_map['Description'] + row).value
            idx = Index.query.filter(Index.name == name).one_or_none()

            if idx:
                print('The index \'{0}\' already exists in the database.'
                      .format(idx.name))
                if idx.description != desc:
                    edited = True
                    idx.description = desc
                    print('The description for \'{0}\' has been changed to: '
                          '{1}'.format(idx.name, idx.description))
                    idx.description = desc
            else:
                edited = True
                idx = Index(name=name, description=desc)
                print('New index \'{0}\' has been added with the description: '
                      '{1}'.format(idx.name, idx.description))
                db.session.add(idx)
            if edited:
                commit_to_db = True
                print('The index \'{0}\' has been edited/added.'
                      .format(idx.name))
                save_indexes_to_json()
                db.session.flush()
            else:
                print('No changes were made to the index \'{0}\'.'
                      .format(idx.name))
        if commit_to_db:
            db.session.commit()

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
                ws.cell(
                    ws.col_map['Subcategory of'] + row
                ).value = cn.parent.name
            ws.cell(
                ws.col_map['Description'] + row
            ).value = cn.description
            ws.cell(
                ws.col_map['Planting Instructions'] + row
            ).value = cn.instructions
            ws.cell(
                ws.col_map['Synonyms'] + row
            ).value = cn.get_synonyms_string() if cn.synonyms else None
            if cn.gw_common_names:
                ws.cell(
                    ws.col_map['Grows With Common Names (JSON)'] + row
                ).value = json.dumps([gwcn.lookup_dict() for gwcn in
                                      cn.gw_common_names])
            if cn.gw_cultivars:
                gwcvs = json.dumps([cv.lookup_dict() for cv in
                                    cn.gw_cultivars])
                ws.cell(
                    ws.col_map['Grows With Cultivars (JSON)'] + row
                ).value = gwcvs
            if cn.invisible:
                ws.cell(
                    ws.col_map['Invisible'] + row
                ).value = 'True'

    def dump_common_names(self):
        """Dump contents of CommonNames sheet into database."""
        ws = self.common_names
        commit_to_db = False
        for i in range(2, len(ws.rows) + 1):
            row = str(i)
            edited = False
            index = dbify(ws.cell(ws.col_map['Index'] + row).value)
            name = dbify(ws.cell(ws.col_map['Common Name'] + row).value)
            parent = dbify(ws.cell(ws.col_map['Subcategory of'] + row).value)
            desc = ws.cell(ws.col_map['Description'] + row).value or None
            instructions = ws.cell(
                ws.col_map['Planting Instructions'] + row
            ).value or None
            synonyms = ws.cell(ws.col_map['Synonyms'] + row).value or None
            gwcn_json = ws.cell(
                ws.col_map['Grows With Common Names (JSON)'] + row
            ).value
            gwcn_dicts = [clean_dict(d) for d in json.loads(gwcn_json)] if\
                gwcn_json else None
            gwcv_json = ws.cell(
                ws.col_map['Grows With Cultivars (JSON)'] + row
            ).value
            gwcv_dicts = [clean_dict(d) for d in json.loads(gwcv_json)] if\
                gwcv_json else None
            invisible = ws.cell(ws.col_map['Invisible'] + row).value
            invisible = True if invisible else False

            cn = CommonName.query\
                .join(Index, Index.id == CommonName.index_id)\
                .filter(CommonName._name == name, Index._name == index)\
                .one_or_none()
            if cn:
                print('The common name \'{0}\' already exists under the index '
                      '\'{1}\'.'.format(cn.name, cn.index.name))
            else:
                edited = True
                cn = CommonName(name=name)
                db.session.add(cn)
                idx = Index.query.filter(Index.name == index).one_or_none()
                if not idx:
                    idx = Index(name=index)
                    print('The index \'{0}\' does not exist in the database, '
                          'so it has been created and added.'.format(index))
                cn.index = idx
                db.session.add(cn)
            if parent:
                if not cn.parent or cn.parent.name != parent:
                    edited = True
                    pcn = CommonName.query\
                        .join(Index, Index.id == CommonName.index_id)\
                        .filter(CommonName._name == parent,
                                Index.name == idx.name)\
                        .one_or_none()
                    if pcn:
                        print('Parent for \'{0}\' set to: {1}'
                              .format(cn.name, pcn.name))
                        cn.parent = pcn
                    else:
                        cn.parent = CommonName(name=parent)
                        cn.parent.invisible = True
                        print('The parent common name \'{0}\' of \'{1}\' '
                              'does not yet exist in the database, so it '
                              'has been added and set to invisible. If it '
                              'exists further down the CommonNames sheet, '
                              'the rest of its values will be filled in, '
                              'and it will be set to visible.'
                              .format(parent, cn.name))
            if desc != cn.description:
                edited = True
                cn.description = desc
                print('The description for \'{0}\' has been set to: {1}'
                      .format(cn.name, cn.description))
            if instructions != cn.instructions:
                edited = True
                cn.instructions = instructions
                print('The planting instructions for \'{0}\' have been set '
                      'to: {1}'
                      .format(cn.name, cn.instructions))
            cn_syns = cn.get_synonyms_string()
            if synonyms != cn_syns and any([cn_syns, synonyms]):
                edited = True
                cn.set_synonyms_string(synonyms)
                if synonyms:
                    print('The synonyms for \'{0}\' have been set to: {1}'
                          .format(cn.name, cn.get_synonyms_string()))
                else:
                    print('The synonyms for \'{0}\' have been cleared.'
                          .format(cn.name))
            current_gwcns = []
            if gwcn_dicts:
                for gwcn_dict in gwcn_dicts:
                    gwcn = CommonName.from_lookup_dict(gwcn_dict)
                    if not gwcn:
                        edited = True
                        gwcn = CommonName(name=gwcn_dict['Common Name'])
                        gwcn.invisible = True
                        db.session.add(gwcn)
                        idx = Index.query\
                            .filter(Index._name == gwcn_dict['Index'])\
                            .one_or_none()
                        if not idx:
                            idx = Index(name=gwcn_dict['Index'])
                            db.session.add(idx)
                            print('The index \'{0}\' needed for the '
                                  'common name \'{1}\' does not exist in '
                                  'the database, so it has been created '
                                  'and added'
                                  .format(idx.name,
                                          gwcn_dict['Common Name']))
                        gwcn.index = idx
                        print('The common name \'{0}\' in Grows With '
                              'Common Names for \'{1}\' does not yet '
                              'exist, so it has been added and set to '
                              'invisible. If it exists further down the '
                              'CommonNames sheet, the rest of its values '
                              'will be filled in and it will be set to '
                              'visible.'
                              .format(gwcn_dict['Common Name'], cn.name))
                    current_gwcns.append(gwcn)
                    if gwcn not in cn.gw_common_names:
                        edited = True
                        cn.gw_common_names.append(gwcn)
                        print('The common name \'{0}\' has been added to '
                              'Grows With Common Names for the common '
                              ' name \'{1}\'.'
                              .format(gwcn.name, cn.name))
            for gwcn in list(cn.gw_common_names):
                if gwcn not in current_gwcns:
                    edited = True
                    print('The common name \'{0}\' has been removed from '
                          'grows with for the commo name \'{1}\'.'
                          .format(gwcn.name, cn.name))
                    cn.gw_common_names.remove(gwcn)
            current_gwcvs = []
            if gwcv_dicts:
                for gwcv_dict in gwcv_dicts:
                    gwcv = Cultivar.from_lookup_dict(gwcv_dict)
                    if not gwcv:
                        edited = True
                        gwcv = Cultivar(name=gwcv_dict['Cultivar Name'])
                        gwcv.invisible = True
                        idx = Index.query\
                            .filter(Index.name == gwcv_dict['Index'])\
                            .one_or_none()
                        if not idx:
                            idx = Index(name=gwcv_dict['Index'])
                            db.session.add(idx)
                            print('The index \'{0}\' needed for the Grows '
                                  'With Cultivar {1} does not yet exist '
                                  'in the database, so it has been created '
                                  'and added.'.format(idx.name, gwcv_dict))
                        comnam = CommonName.query\
                            .filter(CommonName._name ==
                                    gwcv_dict['Common Name'],
                                    CommonName.index_id == idx.id)\
                            .one_or_none()
                        if not comnam:
                            comnam = CommonName(name=gwcv_dict['Common Name'])
                            db.session.add(comnam)
                            comnam.index = idx
                            gwcv.common_name = comnam
                            print('The common name \'{0}\' needed for the '
                                  'Grows With Cultivar {1} does not yet exist '
                                  'in the database, so it has been created '
                                  'and added.'.format(comnam.name, gwcv_dict))
                        if gwcv_dict['Series']:
                            sr = Series.query\
                                .filter(Series.name == gwcv_dict['Series'],
                                        Series.common_name_id == comnam.id)\
                                .one_or_none()
                            if not sr:
                                sr = Series(name=gwcv_dict['Series'])
                                db.session.add(sr)
                                sr.common_name = comnam
                                gwcv.series = sr
                                print('The series \'{0}\' needed for the '
                                      'Grows With Cultivar {1} does not yet '
                                      'exist in the database, so it has been '
                                      'created and added.'
                                      .format(sr.name, gwcv_dict))
                        gwcv.set_slug()
                    current_gwcvs.append(gwcv)
                    if gwcv not in cn.gw_cultivars:
                        edited = True
                        cn.gw_cultivars.append(gwcv)
                        print('The cultivar \'{0}\' has been added to Grows '
                              'With Cultivars for the common name \'{1}\'.'
                              .format(gwcv.fullname, cn.name))
            for gwcv in list(cn.gw_cultivars):
                if gwcv not in current_gwcvs:
                    edited = True
                    print('The cultivar \'{0}\' has been removed from '
                          'grows with for the common name \'{1}\'.'
                          .format(gwcv.fullname, cn.name))
                    cn.gw_cultivars.remove(gwcv)
            if invisible and not cn.invisible:
                edited = True
                cn.invisible = True
                print('The common name \'{0}\' will not be shown on '
                      'auto-generated pages.'.format(cn.name))
            elif cn.invisible:
                edited = True
                cn.invisible = False
                print('The common name \'{0}\' will now be visible on '
                      'auto-generated pages.'.format(cn.name))
            if edited:
                db.session.flush()
                commit_to_db = True
                print('The common name \'{0}\' has been edited/added.'
                      .format(cn.name))
            else:
                print('No changes were made to the common name \'{0}\'.'
                      .format(cn.name))
        if commit_to_db:
            db.session.commit()

    def load_botanical_names(self, botanical_names):
        """Populate the BotanicalNames sheet with BotanicalName objects.

        Attributes:
            botanical_names (list): A list of BotanicalName objects from db.
        """
        ws = self.botanical_names
        for i, bn in enumerate(botanical_names):
            row = str(i + 2)
            ws.cell(
                ws.col_map['Common Names (JSON)'] + row
            ).value = json.dumps([cn.lookup_dict() for cn in bn.common_names])
            ws.cell(ws.col_map['Botanical Name'] + row).value = bn.name
            ws.cell(
                ws.col_map['Synonyms'] + row
            ).value = bn.get_synonyms_string() if bn.synonyms else None

    def dump_botanical_names(self):
        """Dump botanical name data from spreadsheet to the database."""
        ws = self.botanical_names
        commit_to_db = False
        for i in range(2, len(ws.rows) + 1):
            row = str(i)
            edited = False
            cn_json = ws.cell(
                ws.col_map['Common Names (JSON)'] + row
            ).value
            cn_dicts = [clean_dict(d) for d in json.loads(cn_json)]
            botanical_name = ws.cell(
                ws.col_map['Botanical Name'] + row
            ).value
            if not BotanicalName.validate(botanical_name):
                raise ValueError('The botanical name \'{0}\' in cell \'{1}\' '
                                 'of the BotanicalNames spreadsheet does not '
                                 'appear to be valid. Please fix it and try '
                                 'again.'.format(botanical_name,
                                                 ws.cell(ws.col_map['Botanical Name'] + row).coordinate))
            synonyms = ws.cell(
                ws.col_map['Synonyms'] + row
            ).value
            if not synonyms:
                synonyms = None

            bn = BotanicalName.query\
                .filter(BotanicalName.name == botanical_name)\
                .one_or_none()
            if bn:
                print('The botanical name \'{0}\' already exists in the '
                      'database.'.format(bn.name))
            else:
                edited = True
                bn = BotanicalName(name=botanical_name)
                db.session.add(bn)
            current_cns = []
            for cn_d in cn_dicts:
                cn = CommonName.from_lookup_dict(cn_d)
                if not cn:
                    edited = True
                    cn = CommonName(name=cn_d['Common Name'])
                    cn.invisible = True
                    db.session.add(cn)
                    print('The common name \'{0}\' does not yet exist, so '
                          'it has been added to the database and set to not '
                          'show in auto-generated pages.'.format(cn.name))
                    idx = Index.query.filter(Index._name == cn_d['Index'])\
                        .one_or_none()
                    if not idx:
                        idx = Index(name=cn_d['Index'])
                        db.session.add(idx)
                        print('The index \'{0}\' needed for the common name '
                              '\'{1}\' does not exist, so it has been created.'
                              .format(idx.name, cn.name))
                    cn.index = idx
                current_cns.append(cn)
                if cn not in bn.common_names:
                    edited = True
                    bn.common_names.append(cn)
                    print('Adding common name \'{0}\' to common names for the '
                          'botanical name \'{1}\'.'.format(cn.name, bn.name))
            for cn in list(bn.common_names):
                if cn not in current_cns:
                    edited = True
                    bn.common_names.remove(cn)
                    print('The common name \'{0}\' has been removed from the '
                          'botanical name \'{1}\'.'.format(cn.name, bn.name))
            bn_syns = bn.get_synonyms_string()
            if bn_syns != synonyms and any([bn_syns, synonyms]):
                edited = True
                bn.set_synonyms_string(synonyms)
                if synonyms:
                    print('Synonyms for \'{0}\' set to: {1}'
                          .format(bn.name, synonyms))
                else:
                    print('Synonyms for \'{0}\' have been cleared.'
                          .format(bn.name))
            if edited:
                print('The botanical name \'{0}\' has been edited/added.'
                      .format(bn.name))
                db.session.flush()
                commit_to_db = True
            else:
                print('No changes were made to the botanical name \'{0}\'.'
                      .format(bn.name))
        if commit_to_db:
            db.session.commit()

    def load_series(self, series):
        """Populate the Series shet with Series objects from db.

        Attributes:
            series (list): A list of Series objects from db.
        """
        ws = self.series
        for i, sr in enumerate(series):
            row = str(i + 2)
            ws.cell(
                ws.col_map['Common Name (JSON)'] + row
            ).value = json.dumps(sr.common_name.lookup_dict())
            ws.cell(ws.col_map['Series'] + row).value = sr.name
            ws.cell(
                ws.col_map['Position'] + row
            ).value = 'after cultivar' if\
                sr.position == Series.AFTER_CULTIVAR else 'before cultivar'
            ws.cell(ws.col_map['Description'] + row).value = sr.description

    def dump_series(self):
        """Dump data from the Series sheet into the database."""
        ws = self.series
        commit_to_db = False
        for i in range(2, len(ws.rows) + 1):
            row = str(i)
            edited = False
            cn_json = ws.cell(ws.col_map['Common Name (JSON)'] + row).value
            cn_dict = clean_dict(json.loads(cn_json))
            series = dbify(ws.cell(ws.col_map['Series'] + row).value)
            position = ws.cell(ws.col_map['Position'] + row).value
            description = ws.cell(ws.col_map['Description'] + row).value

            sr = Series.query\
                .join(CommonName, CommonName.id == Series.common_name_id)\
                .join(Index, Index.id == CommonName.index_id)\
                .one_or_none()
            if sr:
                print('The series \'{0}\' already exists in the database.'
                      .format(sr.fullname))
            else:
                edited = True
                sr = Series(name=series)
                db.session.add(sr)
            cn = CommonName.from_lookup_dict(cn_dict)
            if not cn:
                edited = True
                cn = CommonName(name=cn_dict['Common Name'])
                cn.invisible = True
                print('The common name \'{0}\' needed for the series \'{1}\' '
                      'does not exist in the database, so it has been created,'
                      'and set to not be shown in auto-generated pages.'
                      .format(cn.name, sr.name))
                idx = Index.query.filter(Index._name == cn_dict['Index'])\
                    .one_or_none()
                if not idx:
                    idx = Index(name=cn_dict['Index'])
                    print('The index \'{0}\' needed for the common name '
                          '\'{1}\' does not exist in the database, so it has '
                          'been created.'.format(idx.name, cn.name))
                cn.index = idx
            if sr.common_name != cn:
                edited = True
                sr.common_name = cn
                print('The common name \'{0}\' has been set for the series '
                      '\'{1}\'.'.format(cn.name, sr.name))
            if 'after' in position.lower() and\
                    sr.position != Series.AFTER_CULTIVAR:
                edited = True
                print('The series name \'{0}\' will be shown after cultivars '
                      'in the series.'.format(sr.name))
                sr.position = Series.AFTER_CULTIVAR
            elif sr.position != Series.BEFORE_CULTIVAR:
                edited = True
                print('The series name \'{0}\' will be shown before cultivars '
                      'in the series.'.format(sr.name))
                sr.position = Series.BEFORE_CULTIVAR
            if sr.description != description and\
                    any([sr.description, description]):
                edited = True
                sr.description = description
                print('Description for \'{0}\' has been set to: {1}'
                      .format(sr.name, sr.description))
            if edited:
                db.session.flush()
                commit_to_db = True
                print('The series \'{0}\' has been edited/added.'
                      .format(sr.name))
            else:
                print('No changes have been made to the series \'{0}\'.'
                      .format(sr.name))
        if commit_to_db:
            db.session.commit()

    def load_cultivars(self, cultivars):
        """Populate the Cultivars sheet with Cultivar object data.

        Attributes:
            cultivars (list): A list of Cultivar objects from db models.
        """
        ws = self.cultivars
        for i, cv in enumerate(cultivars):
            row = str(i + 2)
            if cv.common_name:
                ws.cell(
                    ws.col_map['Index'] + row
                ).value = cv.common_name.index.name if cv.common_name.index\
                    else None
                ws.cell(
                    ws.col_map['Common Name'] + row
                ).value = cv.common_name.name
            if cv.botanical_name:
                ws.cell(
                    ws.col_map['Botanical Name'] + row
                ).value = cv.botanical_name.name
            if cv.series:
                ws.cell(
                    ws.col_map['Series'] + row
                ).value = cv.series.name
            ws.cell(ws.col_map['Cultivar Name'] + row).value = cv.name
            if cv.thumbnail:
                ws.cell(
                    ws.col_map['Thumbnail Filename'] + row
                ).value = cv.thumbnail.filename
            ws.cell(
                ws.col_map['Description'] + row
            ).value = cv.description
            if cv.synonyms:
                ws.cell(
                    ws.col_map['Synonyms'] + row
                ).value = cv.get_synonyms_string()
            if cv.gw_common_names:
                ws.cell(
                    ws.col_map['Grows With Common Names (JSON)'] + row
                ).value = json.dumps([cn.lookup_dict() for cn in
                                      cv.gw_common_names])
            if cv.gw_cultivars:
                ws.cell(
                    ws.col_map['Grows With Cultivars (JSON)'] + row
                ).value = json.dumps([cv.lookup_dict() for cv in
                                      cv.gw_cultivars])
            if cv.new_for:
                ws.cell(ws.col_map['New For'] + row).value = cv.new_for
            if cv.in_stock:
                ws.cell(ws.col_map['In Stock'] + row).value = 'True'
            if cv.active:
                ws.cell(ws.col_map['Active'] + row).value = 'True'
            if cv.invisible:
                ws.cell(ws.col_map['Invisible'] + row).value = 'True'

    def dump_cultivars(self):
        """Dump cultivar sheet data to database."""
        ws = self.cultivars
        commit_to_db = False
        for i in range(2, len(ws.rows) + 1):
            row = str(i)
            edited = False
            index = dbify(ws.cell(ws.col_map['Index'] + row).value)
            common_name = dbify(ws.cell(ws.col_map['Common Name'] + row).value)
            botanical_name = ws.cell(
                ws.col_map['Botanical Name'] + row
            ).value or None
            series = dbify(ws.cell(ws.col_map['Series'] + row).value)
            cultivar = dbify(ws.cell(ws.col_map['Cultivar Name'] + row).value)
            thumbnail = ws.cell(ws.col_map['Thumbnail Filename'] + row).value
            description = ws.cell(ws.col_map['Description'] + row).value
            synonyms = ws.cell(ws.col_map['Synonyms'] + row).value or None
            gwcn_json = ws.cell(
                ws.col_map['Grows With Common Names (JSON)'] + row
            ).value
            gwcn_dicts = [clean_dict(d) for d in json.loads(gwcn_json)] if\
                gwcn_json else None
            gwcv_json = ws.cell(
                ws.col_map['Grows With Cultivars (JSON)'] + row
            ).value
            gwcv_dicts = [clean_dict(d) for d in json.loads(gwcv_json)] if\
                gwcv_json else None
            new_for = ws.cell(ws.col_map['New For'] + row).value
            new_for = int(new_for) if new_for else None
            in_stock = ws.cell(ws.col_map['In Stock'] + row).value
            in_stock = cell_to_bool(in_stock)
            active = ws.cell(ws.col_map['Active'] + row).value
            active = cell_to_bool(active)
            invisible = ws.cell(ws.col_map['Invisible'] + row).value
            invisible = cell_to_bool(invisible)

            cv = Cultivar.lookup(name=cultivar,
                                 series=series,
                                 common_name=common_name,
                                 index=index)
            if cv:
                print('The cultivar \'{0}\' already exists in the database.'
                      .format(cv.fullname))
            else:
                edited = True
                cv = Cultivar(name=cultivar)
                print('Adding new cultivar named \'{0}\'.')
                db.session.add(cv)
            cn = CommonName.query\
                .join(Index, Index.id == CommonName.index_id)\
                .filter(CommonName._name == common_name, Index._name == index)\
                .one_or_none()
            if not cn:
                cn = CommonName(name=common_name)
                print('The common name \'{0}\' needed for the cultivar '
                      '\'{1}\' does not exist yet, so it has been added.'
                      .format(cn.name, cv.name))
                idx = Index.query.filter(Index.name == index).one_or_none()
                if not idx:
                    idx = Index(name=index)
                    print('The index \'{0}\' needed for the common name '
                          '\'{1}\' does not yet exist, so it has been added.'
                          .format(idx.name, cn.name))
                cn.index = idx
            if cv.common_name is not cn:
                edited = True
                cv.common_name = cn
                print('The common name for the cultivar \'{0}\' has been set '
                      'to \'{1}\'.'.format(cv.fullname, cn.name))
            if botanical_name:
                bn = BotanicalName.query\
                    .filter(BotanicalName.name == botanical_name)\
                    .one_or_none()
                if not bn:
                    try:
                        bn = BotanicalName(name=botanical_name)
                        edited = True
                    except ValueError:
                        print('The botanical name \'{0}\' could not be '
                              'created because it doesn\'t appear to be a '
                              'valid botanical name.'
                              .format(botanical_name))
                if cn not in bn.common_names:
                    edited = True
                    bn.common_names.append(cn)
                    print('The common name \'{0}\' has been added to the '
                          'common names for the botanical name \'{1}\'.'
                          .format(cn.name, bn.name))
            if cv.botanical_name is not bn:
                edited = True
                cv.botanical_name = bn
                print('The botanical name \'{0}\' has been added to the '
                      'cultivar \'{1}\'.'.format(bn.name, cv.fullname))
            if series:
                sr = Series.query\
                    .filter(Series.name == series,
                            Series.common_name_id == cn.id)\
                    .one_or_none()
                if not sr:
                    edited = True
                    sr = Series(name=series)
                    sr.common_name = cn
                    print('The series \'{0}\' does not yet exist, so it has '
                          'been added.'.format(sr.name))
                if cv.series != sr and any([cv.series, sr]):
                    edited = True
                    cv.series = sr
                    print('The series \'{0}\' has been added to the cultivar '
                          '\'{1}\'.'.format(sr.name, cv.fullname))
            if thumbnail:
                if not cv.thumbnail or cv.thumbnail.filename != thumbnail:
                    tn = Image.query\
                        .filter(Image.filename == thumbnail)\
                        .one_or_none()
                    if not tn:
                        tn = Image(filename=thumbnail)
                    if tn.exists():
                        edited = True
                        cv.thumbnail = tn
                        print('The thumbnail filename for the cultivar '
                              '\'{0}\' has been set to: \'{1}\', and the '
                              'image file \'{1}\' exists.'
                              .format(cv.fullname, tn.filename))
                    else:
                        print('The thumbnail filename \'{0}\' does not point '
                              'to an existing file, so it has not been added. '
                              .format(tn.filename))
            elif cv.thumbnail:
                edited = True
                print('The thumbnail for the cultivar \'{0}\' has been unset. '
                      'The database entry has been moved to the cultivar\'s '
                      'images, and the image file has not been altered.'
                      .format(cv.fullname))
                tn = cv.thumbnail
                cv.thumbnail = None
                cv.images.append(tn)
            if description and description != cv.description:
                edited = True
                cv.description = description
                print('Description for the cultivar \'{0}\' has been set to: '
                      '{1}'.format(cv.fullname, cv.description))
            elif not description and cv.description:
                edited = True
                cv.description = None
                print('The description for the cultivar \'{0}\' has been '
                      'cleared.'.format(cv.fullname))
            cv_syns = cv.get_synonyms_string()
            if synonyms and synonyms != cv_syns:
                edited = True
                cv.set_synonyms_string(synonyms)
                print('Synonyms for \'{0}\' have been set to: {1}'
                      .format(cv.fullname, cv.get_synonyms_string()))
            elif cv_syns and not synonyms:
                edited = True
                cv.set_synonyms_string(None)
                print('Synonyms for \'{0}\' have been cleared.'
                      .format(cv.fullname))
            current_gwcns = []
            if gwcn_dicts:
                for gwcn_dict in gwcn_dicts:
                    gwcn = CommonName.from_lookup_dict(gwcn_dict)
                    if not gwcn:
                        edited = True
                        gwcn = CommonName(name=gwcn_dict['Common Name'])
                        print('The common name \'{0}\' needed for grows with '
                              'for the cultivar \'{1}\' does not yet exist, '
                              'so it has been created.'
                              .format(gwcn.name, cv.fullname))
                        idx = Index.query\
                            .filter(Index._name == gwcn_dict['Index'])\
                            .one_or_none()
                        if not idx:
                            idx = Index(name=gwcn_dict['Index'])
                            print('The index \'{0}\' needed for the common '
                                  'name \'{1}\' does not yet exist, so it has '
                                  'been created.'.format(idx.name, gwcn.name))
                        if gwcn.index != idx:
                            gwcn.index = idx
                            print('The index \'{0}\' has been set for the '
                                  'common name \'{1}\'.'
                                  .filter(idx.name, gwcn.name))
                    current_gwcns.append(gwcn)
                    if gwcn not in cv.gw_common_names:
                        edited = True
                        print('The common name \'{0}\' has been added to '
                              'grows with for the cultivar \'{1}\'.'
                              .format(gwcn.name, cv.fullname))
            for gwcn in list(cv.gw_common_names):
                if gwcn not in current_gwcns:
                    edited = True
                    print('The common name \'{0}\' has been removed from '
                          'grows with for the cultivar \'{1}\'.'
                          .format(gwcn.name, cv.fullname))
            current_gwcvs = []
            if gwcv_dicts:
                for gwcv_dict in gwcv_dicts:
                    gwcv = Cultivar.from_lookup_dict(gwcv_dict)
                    if not gwcv:
                        edited = True
                        gwcv = Cultivar(name=gwcv_dict['Cultivar Name'])
                        print('The cultivar named \'{0}\' does not yet exist, '
                              'so it has been created.'.format(cv.name))
                        cn_name = gwcv_dict['Common Name']
                        cn_index = gwcv_dict['Index']
                        cn = CommonName.query\
                            .join(Index, Index.id == CommonName.index_id)\
                            .filter(CommonName._name == cn_name,
                                    Index._name == cn_index)\
                            .one_or_none()
                        if not cn:
                            cn = CommonName(name=cn_name)
                            print('The common name \'{0}\' does not yet '
                                  'exist, so it has been created.'
                                  .format(cn.name))
                            idx = Index.query\
                                .filter(Index._name == cn_index)\
                                .one_or_none()
                            if not idx:
                                idx = Index(name=cn_index)
                                print('The index \'{0}\' does not yet exist, '
                                      'so it has been created.'
                                      .format(idx.name))
                            cn.index = idx
                        gwcv.common_name = cn
                        if gwcv_dict['Series']:
                            sr = Series.query\
                                .filter(Series.name == gwcv_dict['Series'],
                                        Series.common_name_id == cn.id)\
                                .one_or_none()
                            if not sr:
                                sr = Series(name=gwcv_dict['Series'])
                                print('The series \'{0}\' does not yet exist, '
                                      'so it has been created.'
                                      .format(sr.name))
                                sr.common_name = cn
                            gwcv.series = sr
                    current_gwcvs.append(gwcv)
                    gwcv.set_slug()
                    if gwcv not in cv.gw_cultivars:
                        edited = True
                        cv.gw_cultivars.append(gwcv)
                        print('The cultivar \'{0}\' has been added to grows '
                              'with for the cultivar \'{1}\'.'
                              .format(gwcv.fullname, cv.fullname))
            for gwcv in list(cv.gw_cultivars):
                if gwcv not in current_gwcvs:
                    edited = True
                    cv.gw_cultivars.remove(gwcv)
                    print('The cultivar \'{0}\' has been removed from '
                          'grows with for the cultivar \'{1}\'.'
                          .format(gwcv.fullname, cv.fullname))
            if new_for and new_for != cv.new_for:
                edited = True
                cv.new_for = new_for
                print('The cultivar \'{0}\' has been set as new for {1}.'
                      .format(cv.fullname, cv.new_for))
            elif not new_for and cv.new_for:
                edited = True
                cv.new_for = None
                print('The cultivar \'{0}\' is no longer set as new for '
                      'any year.'.format(cv.fullname))
            if in_stock and not cv.in_stock:
                edited = True
                cv.in_stock = True
                print('The cultivar \'{0}\' is in stock.'
                      .format(cv.fullname))
            elif cv.in_stock and not in_stock:
                edited = True
                cv.in_stock = False
                print('The cultivar \'{0}\' is out of stock.'
                      .format(cv.fullname))
            if active and not cv.active:
                edited = True
                cv.active = True
                print('The cultivar \'{0}\' is now active.'
                      .format(cv.fullname))
            elif cv.active and not active:
                edited = True
                cv.active = False
                print('The cultivar \'{0}\' is no longer active.'
                      .format(cv.fullname))
            if invisible and not cv.invisible:
                edited = True
                cv.invisible = True
                print('The cultivar \'{0}\' will not be shown on auto-'
                      'generated pages.'.format(cv.fullname))
            elif cv.invisible and not invisible:
                edited = True
                cv.invisible = False
                print('The cultivar \'{0}\' will be shown on auto-'
                      'generated pages.'.format(cv.fullname))
            if edited:
                cv.set_slug()
                db.session.flush()
                commit_to_db = True
                print('The cultivar \'{0}\' has been edited/added.'
                      .format(cv.fullname))
            else:
                print('No changes have been made to the cultivar \'{0}\'.'
                      .format(cv.fullname))
        if commit_to_db:
            db.session.commit()

    def load_packets(self, packets):
        """Populate the Packets sheet with Packet object data.

        Attributes:
            packets (list): A list of Packet objects from db models.
        """
        ws = self.packets
        for i, pkt in enumerate(packets):
            row = str(i + 2)
            ws.cell(
                ws.col_map['Cultivar (JSON)'] + row
            ).value = json.dumps(pkt.cultivar.lookup_dict())
            ws.cell(ws.col_map['SKU'] + row).value = pkt.sku
            ws.cell(ws.col_map['Price'] + row).value = pkt.price
            ws.cell(
                ws.col_map['Quantity'] + row
            ).value = pkt.quantity.str_value
            ws.cell(ws.col_map['Units'] + row).value = pkt.quantity.units

    def dump_packets(self):
        """Dump Packets sheet to database."""
        ws = self.packets
        commit_to_db = False
        for i in range(2, len(ws.rows) + 1):
            row = str(i)
            edited = False
            cv_json = ws.cell(ws.col_map['Cultivar (JSON)'] + row).value
            cv_dict = clean_dict(json.loads(cv_json))
            sku = ws.cell(ws.col_map['SKU'] + row).value
            price_str = ws.cell(ws.col_map['Price'] + row).value
            price = USDInt.usd_to_decimal(price_str)
            quantity = ws.cell(ws.col_map['Quantity'] + row).value
            units = ws.cell(ws.col_map['Units'] + row).value

            pkt = Packet.query.filter(Packet.sku == sku).one_or_none()
            if pkt:
                print('The packet \'{0}\' already exists in the database.'
                      .format(pkt.info))
            else:
                edited = True
                pkt = Packet(sku=sku)
                db.session.add(pkt)
                print('New packet created with the sku \'{0}\'.'
                      .format(pkt.sku))
            cv = Cultivar.from_lookup_dict(cv_dict)
            if not cv:
                edited = True
                cv = Cultivar(name=cv_dict['Cultivar Name'])
                print('The cultivar with the name \'{0}\' needed for the '
                      'packet with the sku \'{1}\' does not yet exist, so it '
                      'has been created.'.format(cv.name, pkt.sku))
                cn_name = cv_dict['Common Name']
                idx_name = cv_dict['Index']
                cn = CommonName.query\
                    .join(Index, Index.id == CommonName.index_id)\
                    .filter(CommonName._name == cn_name,
                            Index._name == idx_name)\
                    .one_or_none()
                if not cn:
                    cn = CommonName(name=cn_name)
                    print('The common name \'{0}\' needed for the cultivar '
                          '\'{1}\' does not exist, so it has been created.'
                          .format(cn.name, cv.fullname))
                    idx = Index.query\
                        .filter(Index._name == idx_name)\
                        .one_or_none()
                    if not idx:
                        idx = Index(name=idx_name)
                        print('The index \'{0}\' needed for the common name '
                              '\'{1}\' does not yet exist, so it has been '
                              'created.'.format(idx.name, cn.name))
                    if cn.index is not idx:
                        cn.index = idx
                        print('Setting the index for the common name \'{0}\' '
                              'to: \'{1}\'.'.format(cn.name, idx.name))
                if cv.common_name is not cn:
                    cv.common_name = cn
                    print('Setting the common name for the cultivar \'{0}\' '
                          'to \'{1}\'.'.format(cv.fullname, cn.name))
                if cv_dict['Series']:
                    sr = Series.query\
                        .filter(Series.name == cv_dict['Series'],
                                Series.common_name_id == cn.id)\
                        .one_or_none()
                    if not sr:
                        sr = Series(name=cv_dict['Series'])
                        print('The series \'{0}\' needed for the cultivar '
                              '\'{1}\' does not yet exist, so it has been '
                              'created.'.format(sr.name, cv.name))
                        sr.common_name = cn
                    if cv.series is not sr:
                        cv.series = sr
                        print('The series for the cultivar \'{0}\' has been '
                              'set to: \'{1}\'.'.format(cv.fullname, sr.name))
            if pkt.cultivar is not cv:
                edited = True
                pkt.cultivar = cv
                print('Setting the cultivar for the packet with sku '
                      '\'{0}\' to \'{1}\'.'.format(pkt.sku, cv.fullname))
            qty = Quantity.query\
                .filter(Quantity.value == Quantity.for_cmp(quantity),
                        Quantity.units == units)\
                .one_or_none()
            if not qty:
                edited = True
                qty = Quantity(value=quantity, units=units)
                print('The quantity \'{0} {1}\' needed for the packet with '
                      'sku \'{2}\' does not yet exist, so it has been '
                      'created.'.format(qty.str_value, qty.units, pkt.sku))
            if pkt.quantity is not qty:
                edited = True
                oldqty = pkt.quantity
                pkt.quantity = qty
                if oldqty and not oldqty.packets:
                    print('The quantity \'{0} {1}\' no longer has any packets '
                          'associated with it, so it has been deleted from '
                          'the database.'
                          .format(oldqty.str_value, oldqty.units))
                    db.session.delete(oldqty)
                print('The quantity for the packet with sku \'{0}\' has been '
                      'set to \'{1} {2}\'.'
                      .format(pkt.sku, qty.str_value, qty.units))
            if pkt.price != price:
                edited = True
                pkt.price = price
                print('The price for the packet with sku \'{0}\' has been set '
                      'to: \'${1}\'.'.format(pkt.sku, pkt.price))
            if edited:
                db.session.flush()
                commit_to_db = True
                print('The packet \'{0}\' has been edited/added.'
                      .format(pkt.info))
            else:
                print('No changes were made to the packet \'{0}\'.'
                      .format(pkt.info))
        if commit_to_db:
            db.session.commit()

    def dump_all(self):
        """Dump all worksheets into the database."""
        self.dump_indexes()
        self.dump_common_names()
        self.dump_botanical_names()
        self.dump_series()
        self.dump_cultivars()
        self.dump_packets()
