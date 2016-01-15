import pytest
from unittest import mock
from openpyxl import Workbook
from app.seeds.excel import SeedsWorkbook, set_sheet_col_map, setup_sheet
from app.seeds.models import CommonName, Cultivar, Index, Series


class TestHelperFunctions:
    """Test module-level functions in the Excel module."""
    def test_setup_sheet_column_headers(self):
        """Set up worksheet with a header row containing column titles."""
        wb = Workbook()
        ws = wb.active
        values = ['One', 'Two', 'Three', 'Four']
        setup_sheet(ws, values)
        assert ws['A1'].value == 'One'
        assert ws['B1'].value == 'Two'
        assert ws['C1'].value == 'Three'
        assert ws['D1'].value == 'Four'

    def test_setup_sheet_freezes_panes(self):
        """Freeze panes from 'A2' up to create header row."""
        wb = Workbook()
        ws = wb.active
        values = ['One', 'Two', 'Three', 'Four']
        setup_sheet(ws, values)
        assert ws.freeze_panes == 'A2'

    def test_setup_sheet_sets_column_widths(self):
        """Column widths should be set based on title length and padding."""
        wb = Workbook()
        ws = wb.active
        values = ['One', 'Two', 'Three', 'Four']
        setup_sheet(ws, values)
        assert ws.column_dimensions['A'].width == len('One')
        assert ws.column_dimensions['B'].width == len('Two')
        assert ws.column_dimensions['C'].width == len('Three')
        assert ws.column_dimensions['D'].width == len('Four')

    def test_setup_sheet_sets_column_widths_with_padding(self):
        """Column widths should add padding if specified."""
        wb = Workbook()
        ws = wb.active
        values = ['One', 'Two', 'Three', 'Four']
        setup_sheet(ws, values, padding=6)
        assert ws.column_dimensions['A'].width == len('One') + 6
        assert ws.column_dimensions['B'].width == len('Two') + 6
        assert ws.column_dimensions['C'].width == len('Three') + 6
        assert ws.column_dimensions['D'].width == len('Four') + 6

    def test_setup_sheet_sets_column_widths_with_text_columns(self):
        """Set columns matching values in textcols to texwidth."""
        wb = Workbook()
        ws = wb.active
        values = ['One', 'Two', 'Three', 'Four']
        setup_sheet(ws,
                    values,
                    padding=6,
                    textwidth=42,
                    textcols=['Two', 'Four'])
        assert ws.column_dimensions['A'].width == len('One') + 6
        assert ws.column_dimensions['B'].width == 42
        assert ws.column_dimensions['C'].width == len('Three') + 6
        assert ws.column_dimensions['D'].width == 42

    def test_setup_sheet_sets_col_map(self):
        """Add column information to sheet.col_map when setting up."""
        wb = Workbook()
        ws = wb.active
        values = ['One', 'Two', 'Three', 'Four']
        setup_sheet(ws, values)
        assert ws.col_map['One'] == 'A'
        assert ws.col_map['Two'] == 'B'
        assert ws.col_map['Three'] == 'C'
        assert ws.col_map['Four'] == 'D'

    def test_set_sheet_col_map(self):
        """Create a map of columns using data from first row of sheet."""
        wb = Workbook()
        ws = wb.active
        ws['A1'].value = 'One'
        ws['B1'].value = 'Two'
        ws['C1'].value = 'Three'
        ws['D1'].value = 'Four'
        set_sheet_col_map(ws)
        assert ws.col_map['One'] == 'A'
        assert ws.col_map['Two'] == 'B'
        assert ws.col_map['Three'] == 'C'
        assert ws.col_map['Four'] == 'D'

    def test_set_sheet_col_map_no_values(self):
        """Raise a ValueError if top row of sheet contains any empty cells."""
        wb = Workbook()
        ws = wb.active
        with pytest.raises(ValueError):
            set_sheet_col_map(ws)
        ws['A1'].value = 'One'
        ws['B1'].value = 'Two'
        ws['C1'].value = None
        ws['D1'].value = 'Three'
        with pytest.raises(ValueError):
            set_sheet_col_map(ws)


class TestSeedsWorkbook:
    """Test methods of the SeedWorkbook class in the excel module."""
    @mock.patch('app.seeds.excel.SeedsWorkbook.setup_workbook')
    def test_init_no_parameters(self, mock_setup):
        """If no parameters are given at init, run setup_workbook."""
        swb = SeedsWorkbook()
        assert not swb.filename
        assert mock_setup.called

    @mock.patch('app.seeds.excel.SeedsWorkbook.load')
    @mock.patch('app.seeds.excel.SeedsWorkbook.setup_workbook')
    def test_init_with_filename(self, mock_setup, mock_load):
        """Set self.filename, but don't load anythying if filename given."""
        swb = SeedsWorkbook(filename='foo.xlsx')
        assert swb.filename == 'foo.xlsx'
        assert mock_setup.called
        assert not mock_load.called

    @mock.patch('app.seeds.excel.SeedsWorkbook.load')
    @mock.patch('app.seeds.excel.SeedsWorkbook.setup_workbook')
    def test_init_with_filename_and_load(self, mock_setup, mock_load):
        """Set self.filename and load file if load is set to True.

        Do not run setup_workbook.
        """
        swb = SeedsWorkbook(filename='foo.xlsx', load=True)
        assert swb.filename == 'foo.xlsx'
        assert mock_load.called
        assert not mock_setup.called

    def test_setup_indexes(self):
        """Create worksheet named 'Indexes' and setup header row."""
        swb = SeedsWorkbook()
        swb.wb = Workbook()  # Clear anything done by __init__
        swb.setup_indexes()
        assert swb.indexes
        assert swb.indexes.title == 'Indexes'
        assert swb.indexes['A1'].value == 'Index'
        assert swb.indexes['B1'].value == 'Description'

    def test_setup_indexes_overwrites_sheet(self):
        """If a worksheet with the default name 'Sheet' exists, use it."""
        swb = SeedsWorkbook()
        swb.wb = Workbook()
        assert 'Sheet' in swb.wb.sheetnames
        assert 'Indexes' not in swb.wb.sheetnames
        swb.setup_indexes()
        assert 'Sheet' not in swb.wb.sheetnames
        assert 'Indexes' in swb.wb.sheetnames

    def test_setup_indexes_creates_sheet_if_no_sheet_present(self):
        """If no sheet named 'Sheet' is present, create new worksheet."""
        swb = SeedsWorkbook()
        swb.wb = Workbook()
        swb.wb.get_sheet_by_name('Sheet').title = 'Stuff'
        assert 'Sheet' not in swb.wb.sheetnames
        assert 'Indexes' not in swb.wb.sheetnames
        swb.setup_indexes()
        assert 'Indexes' in swb.wb.sheetnames
        assert 'Stuff' in swb.wb.sheetnames

    def test_setup_indexes_already_exists(self):
        """Raise RuntimeError an Indexes sheet already exists."""
        swb = SeedsWorkbook()
        swb.wb = Workbook()
        swb.wb.get_sheet_by_name('Sheet').title = 'Indexes'
        with pytest.raises(RuntimeError):
            swb.setup_indexes()

    def test_setup_common_names(self):
        """Create worksheet named 'CommonNames' and setup header row."""
        swb = SeedsWorkbook()
        swb.wb = Workbook()
        swb.setup_common_names()
        assert swb.common_names
        assert swb.common_names.title == 'CommonNames'
        ws = swb.common_names
        assert ws['A1'].value == 'Index'
        assert ws['B1'].value == 'Common Name'
        assert ws['C1'].value == 'Subcategory of'
        assert ws['D1'].value == 'Description'
        assert ws['E1'].value == 'Planting Instructions'
        assert ws['F1'].value == 'Synonyms'
        assert ws['G1'].value == 'Grows With Common Names'
        assert ws['H1'].value == 'Grows With Cultivars'
        assert ws['I1'].value == 'Invisible'

    def test_setup_common_names_already_exists(self):
        """Raise RuntimeError if CommonNames sheet already exists."""
        swb = SeedsWorkbook()
        swb.wb = Workbook()
        swb.wb.active.title = 'CommonNames'
        with pytest.raises(RuntimeError):
            swb.setup_common_names()

    def test_setup_botanical_names(self):
        """Create worksheet named 'BotanicalNames' and setup header row."""
        swb = SeedsWorkbook()
        swb.wb = Workbook()
        swb.setup_botanical_names()
        assert swb.botanical_names
        assert swb.botanical_names.title == 'BotanicalNames'
        ws = swb.botanical_names
        assert ws['A1'].value == 'Common Names'
        assert ws['B1'].value == 'Botanical Name'
        assert ws['C1'].value == 'Synonyms'

    def test_setup_botanical_names_already_exists(self):
        """Raise RuntimeError if BotanicalNames sheet already exists."""
        swb = SeedsWorkbook()
        swb.wb = Workbook()
        swb.wb.active.title = 'BotanicalNames'
        with pytest.raises(RuntimeError):
            swb.setup_botanical_names()

    def test_setup_series(self):
        """Create worksheet named 'Series' and setup header row."""
        swb = SeedsWorkbook()
        swb.wb = Workbook()
        swb.setup_series()
        assert swb.series
        assert swb.series.title == 'Series'
        ws = swb.series
        assert ws['A1'].value == 'Common Name'
        assert ws['B1'].value == 'Series'
        assert ws['C1'].value == 'Position'
        assert ws['D1'].value == 'Description'

    def test_setup_series_already_exists(self):
        """Raise RuntimeError if Series sheet already exists."""
        swb = SeedsWorkbook()
        swb.wb = Workbook()
        swb.wb.active.title = 'Series'
        with pytest.raises(RuntimeError):
            swb.setup_series()

    def test_setup_cultivars(self):
        """Create worksheet named 'Cultivars' and setup header row."""
        swb = SeedsWorkbook()
        swb.wb = Workbook()
        swb.setup_cultivars()
        assert swb.cultivars
        assert swb.cultivars.title == 'Cultivars'
        ws = swb.cultivars
        assert ws['A1'].value == 'Index'
        assert ws['B1'].value == 'Common Name'
        assert ws['C1'].value == 'Botanical Name'
        assert ws['D1'].value == 'Series'
        assert ws['E1'].value == 'Cultivar Name'
        assert ws['F1'].value == 'Thumbnail Filename'
        assert ws['G1'].value == 'Description'
        assert ws['H1'].value == 'Synonyms'
        assert ws['I1'].value == 'Grows With Common Names'
        assert ws['J1'].value == 'Grows With Cultivars'
        assert ws['K1'].value == 'In Stock'
        assert ws['L1'].value == 'Inactive'
        assert ws['M1'].value == 'Invisible'

    def test_setup_cultivars_already_exists(self):
        """Raise RuntimeError if Cultivars sheet exists."""
        swb = SeedsWorkbook()
        swb.wb = Workbook()
        swb.wb.active.title = 'Cultivars'
        with pytest.raises(RuntimeError):
            swb.setup_cultivars()

    def test_setup_packets(self):
        """Create worksheet named 'Packets' and setup header row."""
        swb = SeedsWorkbook()
        swb.wb = Workbook()
        swb.setup_packets()
        assert swb.packets
        assert swb.packets.title == 'Packets'
        ws = swb.packets
        assert ws['A1'].value == 'Cultivar'
        assert ws['B1'].value == 'SKU'
        assert ws['C1'].value == 'Price'
        assert ws['D1'].value == 'Quantity'
        assert ws['E1'].value == 'Units'

    def test_setup_packets_already_exists(self):
        """Raise RuntimeError if Packets sheet exists."""
        swb = SeedsWorkbook()
        swb.wb = Workbook()
        swb.wb.active.title = 'Packets'
        with pytest.raises(RuntimeError):
            swb.setup_packets()

    @mock.patch('app.seeds.excel.SeedsWorkbook.setup_packets')
    @mock.patch('app.seeds.excel.SeedsWorkbook.setup_cultivars')
    @mock.patch('app.seeds.excel.SeedsWorkbook.setup_series')
    @mock.patch('app.seeds.excel.SeedsWorkbook.setup_botanical_names')
    @mock.patch('app.seeds.excel.SeedsWorkbook.setup_common_names')
    @mock.patch('app.seeds.excel.SeedsWorkbook.setup_indexes')
    def test_setup_workbook(self, m_idxs, m_cns, m_bns, m_srs, m_cvs, m_pkts):
        """Create workbook and run all sheet setups."""
        swb = SeedsWorkbook()
        swb.wb = None
        swb.setup_workbook()
        assert swb.wb
        assert m_idxs.called
        assert m_cns.called
        assert m_bns.called
        assert m_srs.called
        assert m_cvs.called
        assert m_pkts.called

    @mock.patch('app.seeds.excel.load_workbook')
    def test_load_uses_self_filename(self, m_lw):
        """load should use self.filename if no filename is specified."""
        swb = SeedsWorkbook('foo.xlsx')
        swb.wb = None
        swb.setup_workbook()  # Just in case __init__ doesn't do this.
        loaded = swb.wb
        swb.wb = None
        assert swb.filename == 'foo.xlsx'
        m_lw.return_value = loaded
        swb.load()
        m_lw.assert_called_with('foo.xlsx')

    @mock.patch('app.seeds.excel.load_workbook')
    def test_load_no_filename(self, m_lw):
        """Raise ValueError if no filename specified or in self.filename."""
        swb = SeedsWorkbook()
        with pytest.raises(ValueError):
            swb.load()
        assert not m_lw.called

    @mock.patch('app.seeds.excel.set_sheet_col_map')
    @mock.patch('app.seeds.excel.load_workbook')
    def test_load_valid_sheet(self, m_lw, m_sscm):
        """Set worksheets to local variables and set their col_maps."""
        swb = SeedsWorkbook()
        swb.wb = None
        swb.setup_workbook()
        loaded = swb.wb
        swb.wb = None
        m_lw.return_value = loaded
        swb.load('foo.xlsx')
        assert swb.indexes is loaded['Indexes']
        assert swb.common_names is loaded['CommonNames']
        assert swb.botanical_names is loaded['BotanicalNames']
        assert swb.series is loaded['Series']
        assert swb.cultivars is loaded['Cultivars']
        assert swb.packets is loaded['Packets']
        m_lw.assert_called_with('foo.xlsx')
        m_sscm.assert_any_call(swb.indexes)
        m_sscm.assert_any_call(swb.common_names)
        m_sscm.assert_any_call(swb.botanical_names)
        m_sscm.assert_any_call(swb.series)
        m_sscm.assert_any_call(swb.cultivars)
        m_sscm.assert_any_call(swb.packets)

    @mock.patch('app.seeds.excel.SeedsWorkbook.setup_packets')
    @mock.patch('app.seeds.excel.SeedsWorkbook.setup_cultivars')
    @mock.patch('app.seeds.excel.SeedsWorkbook.setup_series')
    @mock.patch('app.seeds.excel.SeedsWorkbook.setup_botanical_names')
    @mock.patch('app.seeds.excel.SeedsWorkbook.setup_common_names')
    @mock.patch('app.seeds.excel.SeedsWorkbook.setup_indexes')
    @mock.patch('app.seeds.excel.load_workbook')
    def test_load_bad_sheet(self, m_lw, m_si, m_scn, m_sbn, m_ss, m_scv, m_sp):
        """Set up blank worksheets where sheets are missing."""
        swb = SeedsWorkbook()
        swb.wb = None
        swb.setup_workbook()
        loaded = Workbook()
        loaded.active.title = 'Stuff'
        assert len(loaded.sheetnames) == 1
        swb.wb = None
        m_lw.return_value = loaded
        swb.load('foo.xlsx')
        m_lw.assert_called_with('foo.xlsx')
        assert m_si.called
        assert m_scn.called
        assert m_sbn.called
        assert m_ss.called
        assert m_scv.called
        assert m_sp.called

    @mock.patch('app.seeds.excel.Workbook.save')
    def test_save_uses_self_filename(self, m_save):
        """Use self.filename if no filename specified."""
        swb = SeedsWorkbook('foo.xlsx')
        swb.wb = None
        swb.setup_workbook()
        swb.save()
        m_save.assert_called_with('foo.xlsx')

    @mock.patch('app.seeds.excel.Workbook.save')
    def test_save_no_filename(self, m_save):
        swb = SeedsWorkbook()
        swb.wb = None
        swb.setup_workbook()
        with pytest.raises(ValueError):
            swb.save()
        assert not m_save.called

    @mock.patch('app.seeds.excel.datetime')
    @mock.patch('app.seeds.excel.Workbook.save')
    def test_save_append_timestamp(self, m_save, m_dt):
        """Append a timestamp to the filename if told to."""
        m_utcnow = mock.MagicMock()
        m_utcnow.strftime.return_value = 'timestamp'
        m_dt.utcnow.return_value = m_utcnow
        swb = SeedsWorkbook()
        swb.wb = None
        swb.setup_workbook()
        swb.save('bar.xlsx', append_timestamp=True)
        m_save.assert_called_with('bar_timestamp.xlsx')

    @mock.patch('app.seeds.excel.SeedsWorkbook.beautify')
    @mock.patch('app.seeds.excel.Workbook.save')
    def test_save_calls_beautify(self, m_save, m_b):
        """Call beautify on spreadsheet when saving.

        Certain formatting options can only be applied cell-by-cell, so they
        need to be applied before each save in case cells without the
        formatting have been added.
        """
        swb = SeedsWorkbook()
        swb.wb = None
        swb.setup_workbook()
        swb.save('foo.xlsx')
        m_save.assert_called_with('foo.xlsx')
        assert m_b.called

    def test_load_indexes(self):
        """Load a list of Index objects into the Indexes spreadsheet."""
        indexes = [Index(name='Perennial', description='Built to last.'),
                   Index(name='Annual', description='Not built to last.'),
                   Index(name='Vegetable', description='And fruit, too!')]
        swb = SeedsWorkbook()
        swb.wb = None
        swb.setup_workbook()
        swb.load_indexes(indexes)
        assert swb.indexes['A2'].value == 'Perennial'
        assert swb.indexes['B2'].value == 'Built to last.'
        assert swb.indexes['A3'].value == 'Annual'
        assert swb.indexes['B3'].value == 'Not built to last.'
        assert swb.indexes['A4'].value == 'Vegetable'
        assert swb.indexes['B4'].value == 'And fruit, too!'

    def test_load_common_names(self):
        """Load a list of CommonName objects into CommonNames spreadsheet."""
        idx1 = Index(name='Perennial')
        idx2 = Index(name='Annual')
        cn1 = CommonName(name='Foxglove',
                         description='Spotty.',
                         instructions='Just add water.')
        cn1.index = idx1
        cn1.synonyms.append(CommonName(name='Digitalis'))
        cn2 = CommonName(name='Lupine',
                         description='Pretty.',
                         instructions='Do stuff.')
        cn2.index = idx2
        cn2.synonyms.append(CommonName(name='Lupin'))
        cn2.gw_common_names.append(cn1)
        cn1.gw_common_names.append(cn2)
        cn2.invisible = True
        cv = Cultivar(name='White')
        cv.common_name = cn1
        cv.series = Series(name='Dalmatian')
        cn2.gw_cultivars.append(cv)
        swb = SeedsWorkbook()
        swb.wb = None
        swb.setup_workbook()
        swb.load_common_names([cn1, cn2])
        ws = swb.common_names
        cols = ws.col_map
        assert ws[cols['Index'] + '2'].value == 'Perennial'
        assert ws[cols['Common Name'] + '2'].value == 'Foxglove'
        assert ws[cols['Subcategory of'] + '2'].value is None
        assert ws[cols['Description'] + '2'].value == 'Spotty.'
        assert ws[cols['Planting Instructions'] + '2'].value ==\
            'Just add water.'
        assert ws[cols['Synonyms'] + '2'].value == 'Digitalis'
        assert ws[cols['Grows With Common Names'] + '2'].value == 'Lupine'
        assert ws[cols['Grows With Cultivars'] + '2'].value is None
        assert ws[cols['Invisible'] + '2'].value is None
        assert ws[cols['Index'] + '3'].value == 'Annual'
        assert ws[cols['Common Name'] + '3'].value == 'Lupine'
        assert ws[cols['Subcategory of'] + '3'].value is None
        assert ws[cols['Description'] + '3'].value == 'Pretty.'
        assert ws[cols['Planting Instructions'] + '3'].value == 'Do stuff.'
        assert ws[cols['Synonyms'] + '3'].value == 'Lupin'
        assert ws[cols['Grows With Common Names'] + '3'].value == 'Foxglove'
        assert ws[cols['Grows With Cultivars'] + '3'].value ==\
            '[' + cn2.gw_cultivars[0].lookup_string() + ']'
