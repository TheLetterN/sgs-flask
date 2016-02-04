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
    Index,
    save_indexes_to_json,
    Series
)


def beautify(sheet, height=42):
    """Turn on text wrap in cells and set row heights in all sheets."""
    a = Alignment(wrap_text=True, vertical='top')
    for row in sheet.rows[1:]:
        for cell in row:
            cell.alignment = a
        for i in range(2, len(sheet.rows[1:]) + 2):
            sheet.row_dimensions[i].height = height


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
            ws.cell(ws.col_map['Description'] + row).value =\
                idx.description

    def dump_indexes(self):
        """Dump Indexes from the Indexes sheet to the database."""
        ws = self.indexes
        edited = False
        for i in range(2, len(ws.rows) + 1):
            name = dbify(ws.cell(ws.col_map['Index'] + str(i)).value)
            desc = ws.cell(ws.col_map['Description'] + str(i)).value
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
            save_indexes_to_json()
            db.session.commit()
        else:
            print('The spreadsheet values for the index \'{0}\' do not differ '
                  'from the version in the database, so no changes to it were '
                  'made'.format(idx.name))

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
                cn.get_synonyms_string() if cn.synonyms else None
            if cn.gw_common_names:
                ws.cell(ws.col_map['Grows With Common Names (JSON)'] + row)\
                    .value = json.dumps([gwcn.lookup_dict() for gwcn in
                                         cn.gw_common_names])
            if cn.gw_cultivars:
                gwcvs = json.dumps([cv.lookup_dict() for cv in
                                    cn.gw_cultivars])
                ws.cell(ws.col_map['Grows With Cultivars (JSON)'] + row)\
                    .value = gwcvs
            if cn.invisible:
                ws.cell(ws.col_map['Invisible'] + row).value = 'True'

    def dump_common_names(self):
        """Dump contents of CommonNames sheet into database."""
        ws = self.common_names
        edited = False
        for i in range(2, len(ws.rows) + 1):
            row = str(i)
            index = dbify(ws.cell(ws.col_map['Index'] + row).value)
            name = dbify(ws.cell(ws.col_map['Common Name'] + row).value)
            parent = ws.cell(ws.col_map['Subcategory of'] + row).value
            parent = dbify(parent) if parent else None
            desc = ws.cell(ws.col_map['Description'] + row).value
            desc = desc if desc else None
            instructions = ws.cell(ws.col_map['Planting Instructions'] + row)\
                .value
            instructions = instructions if instructions else None
            synonyms = ws.cell(ws.col_map['Synonyms'] + row).value
            synonyms = synonyms if synonyms else None
            gwcns = ws.cell(ws.col_map['Grows With Common Names (JSON)'] +
                            row).value
            gwcns = gwcns if gwcns else None
            gwcvs = ws.cell(ws.col_map['Grows With Cultivars (JSON)'] + row)\
                .value
            gwcvs = gwcvs if gwcvs else None
            invisible = ws.cell(ws.col_map['Invisible'] + row).value
            invisible = True if invisible else False
            cn = CommonName.query.join(Index, Index.id == CommonName.index_id)\
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
                              .filter(cn.name, pcn.name))
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
            cn_syns = cn_syns if cn_syns else None
            if synonyms != cn_syns:
                edited = True
                cn.set_synonyms_string(synonyms)
                print('The synonyms for \'{0}\' have been set to: {1}'
                      .format(cn.name, cn.get_synonyms_string()))
            if gwcns:
                gwcn_dicts = json.loads(gwcns)
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
                    if gwcn not in cn.gw_common_names:
                        edited = True
                        cn.gw_common_names.append(gwcn)
                        print('The common name \'{0}\' has been added to '
                              'Grows With Common Names for the common '
                              ' name \'{1}\'.'
                              .format(gwcn.name, cn.name))
            if gwcvs:
                gwcv_dicts = json.loads(gwcvs)
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
                    if gwcv not in cn.gw_cultivars:
                        edited = True
                        cn.gw_cultivars.append(gwcv)
                        print('The cultivar \'{0}\' has been added to Grows '
                              'With Cultivars for the common name \'{1}\'.'
                              .format(gwcv.fullname, cn.name))
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
                db.session.commit()
                print('The common name \'{0}\' has been edited/added.'
                      .format(cn.name))
            else:
                print('No changes were made to the common name \'{0}\'.'
                      .format(cn.name))

    def load_botanical_names(self, botanical_names):
        """Populate the BotanicalNames sheet with BotanicalName objects.

        Attributes:
            botanical_names (list): A list of BotanicalName objects from db.
        """
        ws = self.botanical_names
        for i, bn in enumerate(botanical_names):
            row = str(i + 2)
            ws.cell(ws.col_map['Common Names (JSON)'] + row).value =\
                json.dumps([cn.lookup_dict() for cn in bn.common_names])
            ws.cell(ws.col_map['Botanical Name'] + row).value = bn.name
            ws.cell(ws.col_map['Synonyms'] + row).value =\
                bn.get_synonyms_string() if bn.synonyms else None

    def dump_botanical_names(self):
        """Dump botanical name data from spreadsheet to the database."""
        ws = self.botanical_names
        edited = False
        for i in range(2, len(ws.rows) + 1):
            row = str(i)
            common_names = ws.cell(ws.col_map['Common Names (JSON)'] + row)\
                .value
            botanical_name = ws.cell(ws.col_map['Botanical Name'] + row).value
            synonyms = ws.cell(ws.col_map['Synonyms'] + row).value
            synonyms = synonyms if synonyms else ''
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
            cn_dicts = json.loads(common_names)
            for cn_d in cn_dicts:
                cn = CommonName.from_lookup_dict(cn_d)
                if not cn:
                    edited = True
                    cn = CommonName(name=cn_d['Common Name'])
                    cn.invisible = True
                    db.session.add(cn)
                    print('The common name \'{0}\' does not yet exist, so '
                          'it has been added to the database and set to not '
                          'show in auto-generated pages.'.filter(cn.name))
                    idx = Index.query.filter(Index._name == cn_d['Index'])\
                        .one_or_none()
                    if not idx:
                        idx = Index(name=cn_d['Index'])
                        db.session.add(idx)
                        print('The index \'{0}\' needed for the common name '
                              '\'{1}\' does not exist, so it has been created.'
                              .filter(idx.name, cn.name))
                    cn.index = idx
                if cn not in bn.common_names:
                    edited = True
                    bn.common_names.append(cn)
                    print('Adding common name \'{0}\' to common names for the '
                          'botanical name \'{1}\'.'.format(cn.name, bn.name))
            if bn.get_synonyms_string() != synonyms:
                edited = True
                if synonyms:
                    bn.set_synonyms_string(synonyms)
                    print('Synonyms for \'{0}\' set to: {1}'
                          .format(bn.name, synonyms))
                else:
                    bn.set_synonyms_string(None)
                    print('Synonyms for \'{0}\' have been cleared.'
                          .format(bn.name))
            if edited:
                print('The botanical name \'{0}\' has been edited/added.'
                      .format(bn.name))
                db.session.commit()
            else:
                print('No changes were made to the botanical name \'{0}\'.'
                      .format(bn.name))

    def load_series(self, series):
        """Populate the Series shet with Series objects from db.

        Attributes:
            series (list): A list of Series objects from db.
        """
        ws = self.series
        for i, sr in enumerate(series):
            row = str(i + 2)
            ws.cell(ws.col_map['Common Name (JSON)'] + row).value =\
                json.dumps(sr.common_name.lookup_dict())
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
            if cv.common_name:
                ws.cell(ws.col_map['Index'] + row).value =\
                    cv.common_name.index.name if cv.common_name.index else None
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
                    cv.get_synonyms_string()
            if cv.gw_common_names:
                ws.cell(ws.col_map['Grows With Common Names (JSON)'] + row).value =\
                    json.dumps([cn.lookup_dict() for cn in cv.gw_common_names])
            if cv.gw_cultivars:
                ws.cell(ws.col_map['Grows With Cultivars (JSON)'] + row).value =\
                    json.dumps([cv.lookup_dict() for cv in cv.gw_cultivars])
            if cv.new_for:
                ws.cell(ws.col_map['New For'] + row).value = cv.new_for
            if cv.in_stock:
                ws.cell(ws.col_map['In Stock'] + row).value = 'True'
            if cv.active:
                ws.cell(ws.col_map['Active'] + row).value = 'True'
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
            ws.cell(ws.col_map['Cultivar (JSON)'] + row).value =\
                json.dumps(pkt.cultivar.lookup_dict())
            ws.cell(ws.col_map['SKU'] + row).value = pkt.sku
            ws.cell(ws.col_map['Price'] + row).value = pkt.price
            ws.cell(ws.col_map['Quantity'] + row).value =\
                pkt.quantity.str_value
            ws.cell(ws.col_map['Units'] + row).value = pkt.quantity.units
