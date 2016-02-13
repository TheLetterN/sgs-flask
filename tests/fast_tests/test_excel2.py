import json
import pytest
from unittest import mock
from openpyxl import Workbook
from app.seeds.excel2 import lookup_dicts_to_json, SeedsWorkbook, SeedsWorksheet
from app.seeds.models import (
    BotanicalName,
    CommonName,
    Cultivar,
    Index,
    Series
)


class TestExcel2Functions:
    """Test module level functions."""
    def test_lookup_dicts_to_json(self):
        """Generate a JSON string for looking up Grows With cns/cvs.

        It can take either, as both have the lookup_dict() method.
        """
        gwcn1 = CommonName(name='Foxglove')
        gwcn1.index = Index(name='Perennial')
        assert lookup_dicts_to_json([gwcn1]) == json.dumps((gwcn1.lookup_dict(),))
        gwcn2 = CommonName(name='Butterfly Weed')
        gwcn2.index = Index(name='Perennial')
        assert lookup_dicts_to_json([gwcn1, gwcn2]) == json.dumps((gwcn1.lookup_dict(),
                                                      gwcn2.lookup_dict()))
        gwcv1 = Cultivar(name='Soulmate')
        gwcv1.common_name = CommonName(name='Butterfly Weed')
        gwcv1.common_name.index = Index(name='Perennial')
        assert lookup_dicts_to_json([gwcv1]) == json.dumps((gwcv1.lookup_dict(),))
        gwcv2 = Cultivar(name='Petra')
        gwcv2.common_name = CommonName(name='Foxglove')
        gwcv2.common_name.index = Index(name='Perennial')
        gwcv2.series = Series(name='Polkadot')
        assert lookup_dicts_to_json([gwcv1, gwcv2]) == json.dumps((gwcv1.lookup_dict(),
                                                      gwcv2.lookup_dict()))


class TestSeedsWorksheet:
    """Test methods of the SeedsWorksheet container class.
    
    We use Workbook to create sheets instead of Worksheet because it ensures
    the worksheet is created as it would be when used in a workbook.
    """
    def test_rows_property(self):
        """Return a tuple of tuples containing cells.

        It should return a tuple containing an empty tuple if no cells have
        data.
        """
        wb = Workbook()
        ws = wb.active
        sws = SeedsWorksheet(ws)
        assert sws.rows == ((),)
        a1 = sws._ws['A1']
        a1.value = 'One'
        assert sws.rows == ((a1,),)
        b1 = sws._ws['B1']
        b1.value = 'Two'
        assert sws.rows == ((a1, b1),)
        a2 = sws._ws['A2']
        a2.value = 'Three'
        # B2 is created with a null value to fill the grid. 
        b2 = sws._ws['B2']
        assert sws.rows == ((a1, b1), (a2, b2))

    def test_active_row_property(self):
        """Return the row number of the first empty row."""
        wb = Workbook()
        ws = wb.active
        sws = SeedsWorksheet(ws)
        assert sws.active_row == 1
        sws._ws['A1'].value = 'One'
        assert sws.active_row == 2
        sws._ws['A2'].value = 'Two'
        assert sws.active_row == 3
        sws._ws['A3'].value = 'Three'
        assert sws.active_row == 4

    def test_data_rows_property(self):
        """Return all rows except the first row, which contains titles."""
        wb = Workbook()
        ws = wb.active
        sws = SeedsWorksheet(ws)
        assert sws.data_rows == tuple()
        ws['A1'] = 'One'
        assert sws.data_rows == tuple()
        ws['A2'] = 'Two'
        assert sws.data_rows == ((ws['A2'],),)
        ws['A3'] = 'Three'
        assert sws.data_rows == ((ws['A2'],), (ws['A3'],))

    def test_cell(self):
        """Return a cell given integer coordinates."""
        wb = Workbook()
        ws = wb.active
        sws = SeedsWorksheet(ws)
        ws['A1'].value = 'A1'
        ws['B1'].value = 'B1'
        ws['A2'].value = 'A2'
        assert sws.cell(1, 1) is ws['A1']
        assert sws.cell(2, 1) is ws['A2']
        assert sws.cell(1, 2) is ws['B1']

    def test_set_column_titles(self):
        """Set the top row of the worksheet to a list of titles."""
        wb = Workbook()
        ws = wb.active
        sws = SeedsWorksheet(ws)
        titles = ['One', 'Two', 'Three', 'Four']
        sws.set_column_titles(titles)
        assert sws._ws['A1'].value == 'One'
        assert sws._ws['B1'].value == 'Two'
        assert sws._ws['C1'].value == 'Three'
        assert sws._ws['D1'].value == 'Four'

    def test_set_column_titles_existing_sheet(self):
        """Raise a ValueError if there is already data in the top row."""
        wb = Workbook()
        ws = wb.active
        sws = SeedsWorksheet(ws)
        titles = ['One', 'Two', 'Three', 'Four']
        sws._ws.append(titles)
        with pytest.raises(ValueError):
            sws.set_column_titles(titles)

    def test_populate_cols_dict(self):
        """Set cols keys to values in first row, and vals to col numbers."""
        wb = Workbook()
        ws = wb.active
        sws = SeedsWorksheet(ws)
        titles = ['One', 'Two', 'Three', 'Four']
        sws.set_column_titles(titles)
        sws.populate_cols_dict()
        assert sws.cols['One'] == 1
        assert sws.cols['Two'] == 2
        assert sws.cols['Three'] == 3
        assert sws.cols['Four'] == 4

    def test_populate_cols_dict_no_titles(self):
        """Raise a ValueError if there is no data in the first row."""
        wb = Workbook()
        ws = wb.active
        sws = SeedsWorksheet(ws)
        with pytest.raises(ValueError):
            sws.populate_cols_dict()

    def test_freeze_title_row(self):
        """Freeze cell A2 to cause the top row to act as column titles."""
        wb = Workbook()
        ws = wb.active
        sws = SeedsWorksheet(ws)
        sws.freeze_title_row()
        assert sws._ws.freeze_panes == 'A2'


class TestSeedsWorkbook:
    """Test methods of the SeedsWorkbook container class."""
    @mock.patch('app.seeds.excel2.SeedsWorkbook.create_all_sheets')
    def test_create_indexes_sheet(self, m):
        """Create a sheet titled 'Indexes' and prepare it for use."""
        swb = SeedsWorkbook()
        swb.create_indexes_sheet()
        ws = swb.indexes._ws
        assert ws.title == 'Indexes'
        assert ws['A1'].value == 'Index'
        assert ws['B1'].value == 'Description'
        assert swb.indexes.cols['Index'] == 1
        assert swb.indexes.cols['Description'] == 2
    
    @mock.patch('app.seeds.excel2.SeedsWorksheet.populate_cols_dict')
    def test_load_indexes_from_workbook(self, m):
        """Setup self.indexes and with data from Indexes sheet."""
        swb = SeedsWorkbook()
        wb = Workbook()
        wb.create_sheet(title='Indexes')
        wb['Indexes'].append(['One', 'Two', 'Three'])
        swb._wb = wb
        swb.load_indexes_from_workbook()
        assert swb.indexes._ws is swb._wb['Indexes']
        assert m.called

    def test_add_index(self):
        """Add data from an Index to active row of the Indexes sheet."""
        swb = SeedsWorkbook()
        sws = swb.indexes
        idx1 = Index(name='Perennial', description='Built to last.')
        swb.add_index(idx1)
        idx_col = sws.cols['Index']
        desc_col = sws.cols['Description']
        assert sws.cell(2, idx_col).value == 'Perennial'
        assert sws.cell(2, desc_col).value == 'Built to last.'
        idx2 = Index(name='Annual', description='Not built to last.')
        swb.add_index(idx2)
        assert sws.cell(3, idx_col).value == 'Annual'
        assert sws.cell(3, desc_col).value == 'Not built to last.'

    def test_add_index_not_index(self):
        """Raise a TypeError given non Index data."""
        swb = SeedsWorkbook()
        with pytest.raises(TypeError):
            swb.add_index(42)
        with pytest.raises(TypeError):
            swb.add_index(CommonName(name='Not an index'))

    @mock.patch('app.seeds.excel2.SeedsWorkbook.add_index')
    def test_add_indexes(self, m):
        """Run add_index for each Index in passed iterable."""
        swb = SeedsWorkbook()
        indexes = (Index(name='Perennial'),
                   Index(name='Annual'),
                   Index(name='Herb'))
        swb.add_indexes(indexes)
        assert m.call_count == 3

    @mock.patch('app.seeds.excel2.SeedsWorkbook.create_all_sheets')
    def test_create_common_names_sheet(self, m):
        """Create a sheet titled 'Common Names' and prepare for use."""
        swb = SeedsWorkbook()
        swb.create_common_names_sheet()
        ws = swb.common_names._ws
        assert ws.title == 'Common Names'
        assert ws['A1'].value == 'Index'
        assert ws['B1'].value == 'Common Name'
        assert ws['C1'].value == 'Subcategory of'
        assert ws['D1'].value == 'Description'
        assert ws['E1'].value == 'Planting Instructions'
        assert ws['F1'].value == 'Synonyms'
        assert ws['G1'].value == 'Invisible'
        assert ws['H1'].value == 'Grows With Common Names (JSON)'
        assert ws['I1'].value == 'Grows With Cultivars (JSON)'
        sws = swb.common_names
        assert sws.cols['Index'] == 1
        assert sws.cols['Common Name'] == 2
        assert sws.cols['Subcategory of'] == 3
        assert sws.cols['Description'] == 4
        assert sws.cols['Planting Instructions'] == 5
        assert sws.cols['Synonyms'] == 6
        assert sws.cols['Invisible'] == 7
        assert sws.cols['Grows With Common Names (JSON)'] == 8
        assert sws.cols['Grows With Cultivars (JSON)'] == 9

    @mock.patch('app.seeds.excel2.SeedsWorksheet.populate_cols_dict')
    def test_load_common_names_from_workbook(self, m):
        """Setup self.common_names with data from Common Names sheet."""
        swb = SeedsWorkbook()
        wb = Workbook()
        wb.create_sheet(title='Common Names')
        swb._wb = wb
        swb.load_common_names_from_workbook()
        assert swb.common_names._ws is swb._wb['Common Names']
        assert m.called

    def test_add_common_name_no_optionals(self):
        """Add a common name (with no optional data) to Common Names sheet."""
        swb = SeedsWorkbook()
        cn = CommonName(name='Foxglove')
        cn.index = Index(name='Perennial')
        swb.add_common_name(cn)
        sws = swb.common_names
        assert sws.cell(2, sws.cols['Index']).value == 'Perennial'
        assert sws.cell(2, sws.cols['Common Name']).value == 'Foxglove'

    def test_add_common_name_no_gw(self):
        """Add a common name (with no Grows With) to Common Names sheet."""
        swb = SeedsWorkbook()
        cn = CommonName(name='Foxglove',
                        description='Spotty.',
                        instructions='Just add water!')
        cn.index = Index(name='Perennial')
        cn.parent = CommonName(name='Fauxglove')
        cn.invisible = True
        cn.set_synonyms_string('Digitalis')
        swb.add_common_name(cn)
        sws = swb.common_names
        assert sws.cell(2, sws.cols['Subcategory of']).value == 'Fauxglove'
        assert sws.cell(2, sws.cols['Description']).value == 'Spotty.'
        assert sws.cell(
            2, sws.cols['Planting Instructions']
        ).value == 'Just add water!'
        assert sws.cell(2, sws.cols['Synonyms']).value == 'Digitalis'
        assert sws.cell(2, sws.cols['Invisible']).value == 'True'

    def test_add_common_name_with_gw_cn(self):
        """Add a common name with some Grows With Common Names."""
        swb = SeedsWorkbook()
        cn = CommonName(name='Foxglove')
        cn.index = Index(name='Perennial')
        gwcn1 = CommonName(name='Tomato')
        gwcn1.index = Index(name='Vegetable')
        gwcn2 = CommonName(name='Basil')
        gwcn2.index = Index(name='Herb')
        cn.gw_common_names = [gwcn1, gwcn2]
        swb.add_common_name(cn)
        sws = swb.common_names
        assert sws.cell(
            2, sws.cols['Grows With Common Names (JSON)']
        ).value == lookup_dicts_to_json([gwcn1, gwcn2]) 

    def test_add_common_name_with_gw_cv(self):
        """Add a common name with some Grows With Cultivars."""
        swb = SeedsWorkbook()
        cn = CommonName(name='Foxglove')
        cn.index = Index(name='Perennial')
        gwcv1 = Cultivar(name='Soulmate')
        gwcv1.common_name = CommonName(name='Butterfly Weed')
        gwcv1.common_name.index = Index(name='Perennial')
        gwcv2 = Cultivar(name='Petra')
        gwcv2.common_name = CommonName(name='Foxglove')
        gwcv2.common_name.index = Index(name='Perennial')
        gwcv2.series = Series(name='Polkadot')
        cn.gw_cultivars = [gwcv1, gwcv2]
        swb.add_common_name(cn)
        sws = swb.common_names
        assert sws.cell(
            2, sws.cols['Grows With Cultivars (JSON)']
        ).value == lookup_dicts_to_json([gwcv1, gwcv2])

    def test_add_common_name_not_common_name(self):
        """Raise a TypeError given data that isn't a CommonName."""
        swb = SeedsWorkbook()
        with pytest.raises(TypeError):
            swb.add_common_name(42)
        with pytest.raises(TypeError):
            swb.add_common_name(Index(name='Perennial'))

    @mock.patch('app.seeds.excel2.SeedsWorkbook.add_common_name')
    def test_add_common_names(self, m):
        """Run add_common_name on each CommonName in passed iterable."""
        swb = SeedsWorkbook()
        cn1 = CommonName(name='Foxglove')
        cn1.index = Index(name='Perennial')
        cn2 = CommonName(name='Butterfly Weed')
        cn2.index = Index(name='Perennial')
        cn3 = CommonName(name='Basil')
        cn3.index = Index(name='Herb')
        swb.add_common_names((cn1, cn2, cn3))
        assert m.call_count == 3

    @mock.patch('app.seeds.excel2.SeedsWorkbook.create_all_sheets')
    def test_create_botanical_names_sheet(self, m):
        """Create a sheet titled 'Botanical Names' and prepare for use."""
        swb = SeedsWorkbook()
        swb.create_botanical_names_sheet()
        ws = swb.botanical_names._ws
        assert ws.title == 'Botanical Names'
        assert ws['A1'].value == 'Common Names (JSON)'
        assert ws['B1'].value == 'Botanical Name'
        assert ws['C1'].value == 'Synonyms'
        sws = swb.botanical_names
        assert sws.cols['Common Names (JSON)'] == 1
        assert sws.cols['Botanical Name'] == 2
        assert sws.cols['Synonyms'] == 3

    @mock.patch('app.seeds.excel2.SeedsWorksheet.populate_cols_dict')
    def test_load_botanical_names_from_workbook(self, m):
        """Setup self.botanical_names with data from Botanical Names sheet."""
        swb = SeedsWorkbook()
        wb = Workbook()
        wb.create_sheet(title='Botanical Names')
        swb._wb = wb
        swb.load_botanical_names_from_workbook()
        assert swb.botanical_names._ws is swb._wb['Botanical Names']
        assert m.called

    def test_add_botanical_name_no_optionals(self):
        """Add a BotanicalName object to Botanical Names sheet."""
        swb = SeedsWorkbook()
        bn = BotanicalName(name='Innagada davida')
        cn = CommonName(name='Rock')
        cn.index = Index(name='Music')
        bn.common_names = [cn]
        swb.add_botanical_name(bn)
        sws = swb.botanical_names
        assert sws.cell(
            2, sws.cols['Common Names (JSON)']
        ).value == lookup_dicts_to_json([cn])
        assert sws.cell(
            2, sws.cols['Botanical Name']
        ).value == 'Innagada davida'

    def test_add_botanical_name_with_synonyms(self):
        """Add a BotanicalName with synonyms to Botanical Names sheet."""
        swb = SeedsWorkbook()
        bn = BotanicalName(name='Innagada davida')
        cn = CommonName(name='Rock')
        cn.index = Index(name='Music')
        bn.common_names = [cn]
        bn.set_synonyms_string('Iron butterfly')
        swb.add_botanical_name(bn)
        sws = swb.botanical_names
        assert sws.cell(2, sws.cols['Synonyms']).value == 'Iron butterfly'

    def test_add_botanical_name_not_botanical_name(self):
        """Raise a TypeError given non-BotanicalName data."""
        swb = SeedsWorkbook()
        with pytest.raises(TypeError):
            swb.add_botanical_name(42)
        with pytest.raises(TypeError):
            swb.add_botanical_name(CommonName(name='Spurious'))

    @mock.patch('app.seeds.excel2.SeedsWorkbook.add_botanical_name')
    def test_add_botanical_names(self, m):
        """Run add_botanical_name on each BotanicalName in passed iterable."""
        swb = SeedsWorkbook()
        bns = (BotanicalName(name='Innagada davida'),
               BotanicalName(name='Digitalis über alles'),
               BotanicalName(name='Canis lupus'))
        swb.add_botanical_names(bns)
        assert m.call_count == 3

    @mock.patch('app.seeds.excel2.SeedsWorkbook.create_all_sheets')
    def test_create_series_sheet(self, m):
        """Create a sheet titled 'Series' and prepare for use."""
        swb = SeedsWorkbook()
        swb.create_series_sheet()
        ws = swb.series._ws
        assert ws.title == 'Series'
        assert ws['A1'].value == 'Common Name (JSON)'
        assert ws['B1'].value == 'Series'
        assert ws['C1'].value == 'Position'
        assert ws['D1'].value == 'Description'
        sws = swb.series
        assert sws.cols['Common Name (JSON)'] == 1
        assert sws.cols['Series'] == 2
        assert sws.cols['Position'] == 3
        assert sws.cols['Description'] == 4

    @mock.patch('app.seeds.excel2.SeedsWorksheet.populate_cols_dict')
    def test_load_series_from_workbook(self, m):
        swb = SeedsWorkbook()
        wb = Workbook()
        wb.create_sheet(title='Series')
        swb._wb = wb
        swb.load_series_from_workbook()
        assert swb.series._ws is swb._wb['Series']
        assert m.called

    @mock.patch('app.seeds.excel2.SeedsWorkbook.create_all_sheets')
    def test_create_cultivars_sheet(self, m):
        """Create a sheet titled 'Cultivars' and prepare for use."""
        swb = SeedsWorkbook()
        swb.create_cultivars_sheet()
        ws = swb.cultivars._ws
        assert ws.title == 'Cultivars'
        assert ws['A1'].value == 'Index'
        assert ws['B1'].value == 'Common Name'
        assert ws['C1'].value == 'Botanical Name'
        assert ws['D1'].value == 'Series'
        assert ws['E1'].value == 'Cultivar Name'
        assert ws['F1'].value == 'Thumbnail Filename'
        assert ws['G1'].value == 'Description'
        assert ws['H1'].value == 'Synonyms'
        assert ws['I1'].value == 'New For'
        assert ws['J1'].value == 'In Stock'
        assert ws['K1'].value == 'Active'
        assert ws['L1'].value == 'Invisible'
        assert ws['M1'].value == 'Grows With Common Names (JSON)'
        assert ws['N1'].value == 'Grows With Cultivars (JSON)'
        sws = swb.cultivars
        assert sws.cols['Index'] == 1
        assert sws.cols['Common Name'] == 2
        assert sws.cols['Botanical Name'] == 3
        assert sws.cols['Series'] == 4
        assert sws.cols['Cultivar Name'] == 5
        assert sws.cols['Thumbnail Filename'] == 6
        assert sws.cols['Description'] == 7
        assert sws.cols['Synonyms'] == 8
        assert sws.cols['New For'] == 9
        assert sws.cols['In Stock'] == 10
        assert sws.cols['Active'] == 11
        assert sws.cols['Invisible'] == 12
        assert sws.cols['Grows With Common Names (JSON)'] == 13
        assert sws.cols['Grows With Cultivars (JSON)'] == 14

    @mock.patch('app.seeds.excel2.SeedsWorksheet.populate_cols_dict')
    def test_load_cultivars_from_workbook(self, m):
        swb = SeedsWorkbook()
        wb = Workbook()
        wb.create_sheet('Cultivars')
        swb._wb = wb
        swb.load_cultivars_from_workbook()
        assert swb.cultivars._ws is swb._wb['Cultivars']
        assert m.called

    @mock.patch('app.seeds.excel2.SeedsWorkbook.create_all_sheets')
    def test_create_packets_sheet(self, m):
        swb = SeedsWorkbook()
        swb.create_packets_sheet()
        ws = swb.packets._ws
        assert ws.title == 'Packets'
        assert ws['A1'].value == 'Cultivar (JSON)'
        assert ws['B1'].value == 'SKU'
        assert ws['C1'].value == 'Price'
        assert ws['D1'].value == 'Quantity'
        assert ws['E1'].value == 'Units'
        sws = swb.packets
        assert sws.cols['Cultivar (JSON)'] == 1
        assert sws.cols['SKU'] == 2
        assert sws.cols['Price'] == 3
        assert sws.cols['Quantity'] == 4
        assert sws.cols['Units'] == 5

    @mock.patch('app.seeds.excel2.SeedsWorksheet.populate_cols_dict')
    def test_load_packets_from_workbook(self, m):
        swb = SeedsWorkbook()
        wb = Workbook()
        wb.create_sheet('Packets')
        swb._wb = wb
        swb.load_packets_from_workbook()
        assert swb.packets._ws is swb._wb['Packets']
        assert m.called

    @mock.patch('app.seeds.excel2.SeedsWorkbook.create_all_sheets')
    def test_remove_all_sheets(self, m):
        """Remove all worksheets from the workbook."""
        swb = SeedsWorkbook()
        swb._wb.remove_sheet(swb._wb.active)
        assert not swb._wb.worksheets
        titles = ['One', 'Two', 'Three']
        for title in titles:
            swb._wb.create_sheet(title=title)
        assert sorted(titles) == sorted(swb._wb.sheetnames)

    @mock.patch('app.seeds.excel2.SeedsWorkbook.remove_all_sheets')
    @mock.patch('app.seeds.excel2.SeedsWorkbook.create_indexes_sheet')
    @mock.patch('app.seeds.excel2.SeedsWorkbook.create_common_names_sheet')
    @mock.patch('app.seeds.excel2.SeedsWorkbook.create_botanical_names_sheet')
    @mock.patch('app.seeds.excel2.SeedsWorkbook.create_series_sheet')
    @mock.patch('app.seeds.excel2.SeedsWorkbook.create_cultivars_sheet')
    @mock.patch('app.seeds.excel2.SeedsWorkbook.create_packets_sheet')
    def test_create_all_sheets(self,
                               m_pkt,
                               m_cv,
                               m_sr,
                               m_bn,
                               m_cn,
                               m_idx,
                               m_remove):
        """Remove all worksheets, then create all worksheets."""
        with mock.patch('app.seeds.excel2.SeedsWorkbook.create_all_sheets'):
            swb = SeedsWorkbook()
        swb.create_all_sheets()
        assert m_remove.called
        assert m_idx.called
        assert m_cn.called
        assert m_bn.called
        assert m_sr.called
        assert m_cv.called
        assert m_pkt.called

    @mock.patch('app.seeds.excel2.SeedsWorkbook.load_indexes_from_workbook')
    @mock.patch('app.seeds.excel2.SeedsWorkbook'
                '.load_common_names_from_workbook')
    @mock.patch('app.seeds.excel2.SeedsWorkbook'
                '.load_botanical_names_from_workbook')
    @mock.patch('app.seeds.excel2.SeedsWorkbook.load_series_from_workbook')
    @mock.patch('app.seeds.excel2.SeedsWorkbook.load_cultivars_from_workbook')
    @mock.patch('app.seeds.excel2.SeedsWorkbook.load_packets_from_workbook')
    def test_load_all_sheets_from_workbook(self,
                                           m_pkt,
                                           m_cv,
                                           m_sr,
                                           m_bn,
                                           m_cn,
                                           m_idx):
        """Load all sheets from self._wb into appropriate attributes."""
        swb = SeedsWorkbook()
        swb.load_all_sheets_from_workbook()
        assert m_idx.called
        assert m_cn.called
        assert m_bn.called
        assert m_sr.called
        assert m_cv.called
        assert m_pkt.called
