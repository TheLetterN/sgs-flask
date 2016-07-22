from unittest import mock
import pytest
from wtforms import ValidationError
from app.seeds.forms import (
    AddCultivarForm,
    AddPacketForm,
    AddRedirectForm,
    EditBotanicalNameForm,
    EditSectionForm,
    EditCommonNameForm,
    EditCultivarForm,
    EditIndexForm,
    EditPacketForm,
    IsBotanicalName,
    NotSpace,
    ReplaceMe,
    RRPath,
    SelectSectionForm,
    select_field_choices,
    SynonymLength,
    USDollar
)
from app.seeds.models import (
    BotanicalName,
    Section,
    CommonName
)
from app.redirects import Redirect


class TestModuleFunctions:
    """Test module-level functions in app.seeds.forms."""
    def test_select_field_choices_from_items_by_id(self):
        """Generate a list of tuples based on objects ordered by id."""
        item1 = mock.MagicMock()
        item2 = mock.MagicMock()
        item3 = mock.MagicMock()
        item1.id = 1
        item2.id = 2
        item3.id = 3
        item1.name = 'Zinnia'
        item2.name = 'Acanthus'
        item3.name = 'Sunflower'
        sfcs = select_field_choices(items=[item1, item2, item3],
                                    title_attribute='name',
                                    order_by='id')
        assert sfcs == [(1, 'Zinnia'), (2, 'Acanthus'), (3, 'Sunflower')]

    def test_select_field_choices_from_items_by_name(self):
        """Generate a list of tuples based on objects ordered by name."""
        item1 = mock.MagicMock()
        item2 = mock.MagicMock()
        item3 = mock.MagicMock()
        item1.id = 1
        item2.id = 2
        item3.id = 3
        item1.name = 'Zinnia'
        item2.name = 'Acanthus'
        item3.name = 'Sunflower'
        sfcs = select_field_choices(items=[item1, item2, item3],
                                    title_attribute='name',
                                    order_by='name')
        assert sfcs == [(2, 'Acanthus'), (3, 'Sunflower'), (1, 'Zinnia')]

    def test_select_field_choices_no_items_or_model(self):
        """Return an empty list if given no items or model."""
        assert select_field_choices() == []

    def test_select_field_choices_with_model_and_items(self):
        """Ignore model if items are passed.

        If it doesn't ignore model, it will try to query it, which will result
        in an exception because MagicMock has no 'query' attribute, and even if
        we used an object that had the attribute it would try to query a
        nonexistent database!
        """
        item1 = mock.MagicMock()
        item2 = mock.MagicMock()
        item3 = mock.MagicMock()
        item1.id = 1
        item2.id = 2
        item3.id = 3
        item1.name = 'Zinnia'
        item2.name = 'Acanthus'
        item3.name = 'Sunflower'
        sfcs = select_field_choices(model=mock.MagicMock,
                                    items=[item1, item2, item3],
                                    title_attribute='name',
                                    order_by='id')
        assert sfcs == [(1, 'Zinnia'), (2, 'Acanthus'), (3, 'Sunflower')]


class TestValidators:
    """Test custom validator classes."""
    @mock.patch('app.seeds.forms.BotanicalName.validate')
    def test_isbotanicalname(self, m_bnv):
        """Raise a ValidationError if field data is not a valid bot. name."""
        m_bnv.return_value = False
        field = mock.MagicMock()
        field.data = 'invalid botanical name'
        with pytest.raises(ValidationError):
            ibn = IsBotanicalName()
            ibn.__call__(None, field)
        m_bnv.assert_called_with('invalid botanical name')

    def test_notspace(self, app):
        """Raise validation error if field data is whitespace."""
        ns = NotSpace()
        form = mock.MagicMock()
        form.name.data = 'foo'
        ns.__call__(form, form.name)
        with pytest.raises(ValidationError):
            form.name.data = ' '
            ns.__call__(form, form.name)
        with pytest.raises(ValidationError):
            form.name.data = '\n'
            ns.__call__(form, form.name)
        with pytest.raises(ValidationError):
            form.name.data = '\t'
            ns.__call__(form, form.name)

    def test_replaceme(self):
        """Raise ValidationError if field data contains < and >."""
        form = AddRedirectForm()
        form.old_path.data = '/path/to/redirect'
        rm = ReplaceMe()
        rm.__call__(form, form.old_path)
        form.old_path.data = '/path/to/<replace me>'
        with pytest.raises(ValidationError):
            rm.__call__(form, form.old_path)
        form.old_path.data = '/<replace>/to/redirect'
        with pytest.raises(ValidationError):
            rm.__call__(form, form.old_path)
        form.old_path.data = '/path/<replace this>/redirect'
        with pytest.raises(ValidationError):
            rm.__call__(form, form.old_path)

    def test_rrpath(self):
        """Raise ValidationError if field data does not begin with /."""
        form = AddRedirectForm()
        form.old_path.data = '/path/to/redirect'
        rr = RRPath()
        rr.__call__(form, form.old_path)
        form.old_path.data = '\\windows\\style\\path'
        with pytest.raises(ValidationError):
            rr.__call__(form, form.old_path)
        form.old_path.data = 'relative/path'
        with pytest.raises(ValidationError):
            rr.__call__(form, form.old_path)

    def test_synonymlength_min_and_max_length(self):
        """Raise error if min_length > max_length."""
        SynonymLength(min_length=0, max_length=42)
        SynonymLength(min_length=12, max_length=12)
        with pytest.raises(ValueError):
            SynonymLength(min_length=11, max_length=10)

    def test_synonymlength_too_short(self):
        """Raise error if any synonym is too short."""
        sl = SynonymLength(min_length=9, max_length=32)
        field = mock.MagicMock()
        field.data = 'Napoleon'
        with pytest.raises(ValidationError):
            sl.__call__(form=None, field=field)

    def test_synonymlength_too_long(self):
        sl = SynonymLength(min_length=0, max_length=11)
        field = mock.MagicMock()
        field.data = 'Too long; didn\'t pass'
        with pytest.raises(ValidationError):
            sl.__call__(form=None, field=field)

    def test_synonymlength_just_right(self):
        sl = SynonymLength(min_length=0, max_length=16)
        field = mock.MagicMock()
        field.data = 'Just Right'
        sl.__call__(form=None, field=field)

    def test_synonymlength_no_data(self):
        """Don't raise a ValidationError if no synonyms given.

        Note that min_length is 1 here, as this validator should only care
        about synonym length if synonyms are present.
        """
        sl = SynonymLength(1, 6)
        field = mock.MagicMock()
        field.data = ''
        sl.__call__(None, field)
        field.data = None
        sl.__call__(None, field)

    def test_usdollar(self):
        """Raise validation error if value can't be converted to USD."""
        usd = USDollar()
        form = mock.MagicMock()
        form.name.data = '$3.50'
        usd.__call__(form, form.name)
        form.name.data = '2.99'
        usd.__call__(form, form.name)
        form.name.data = '3'
        with pytest.raises(ValidationError):
            form.name.data = 'tree fiddy'
            usd.__call__(form, form.name)
        with pytest.raises(ValidationError):
            form.name.data = '$3/4'
            usd.__call__(form, form.name)


class TestAddCultivarForm:
    """Test methods of AddCultivarForm."""
    @mock.patch('app.seeds.models.Image.query')
    def test_validate_thumbnail(self, m_imgq):
        m_imgq.return_value = 'Something'
        field = mock.MagicMock()
        field.data.filename = 'Something'
        with pytest.raises(ValidationError):
            AddCultivarForm.validate_thumbnail(self=None, field=field)


class TestAddPacketForm:
    """Test custom methods of AddPacketForm."""
    def test_validate_quantity(self, app):
        """Raise ValidationError if quantity can't be parsed."""
        field = mock.MagicMock()
        field.data = '100'
        AddPacketForm.validate_quantity(None, field)
        field.data = '2.3423'
        AddPacketForm.validate_quantity(None, field)
        field.data = '3/4'
        AddPacketForm.validate_quantity(None, field)
        field.data = '1 1/2'
        AddPacketForm.validate_quantity(None, field)
        field.data = '$2'
        with pytest.raises(ValidationError):
            AddPacketForm.validate_quantity(None, field)
        field.data = '3/4/13'
        with pytest.raises(ValidationError):
            AddPacketForm.validate_quantity(None, field)
            field.data = '127.0.0.1'
        with pytest.raises(ValidationError):
            AddPacketForm.validate_quantity(None, field)


class TestAddRedirectForm:
    """Test custom methods of AddRedirectForm."""
    def test_validate_old_path(self):
        """Raise ValidationError if a redirect from old_path exists."""
        with mock.patch('app.seeds.forms.RedirectsFile') as mock_rdf:
            mock_rdf.exists.return_value = True
            rd1 = Redirect('/one', '/two', 302)
            rd2 = Redirect('/three', '/four', 302)
            rdf = mock.Mock(redirects=[rd1, rd2])
            mock_rdf.return_value = rdf
            form = AddRedirectForm()
            form.old_path.data = '/five'
            form.validate_old_path(form.old_path)
            form.old_path.data = '/three'
            with pytest.raises(ValidationError):
                form.validate_old_path(form.old_path)

    def test_validate_new_path(self):
        """Raise ValidationError if new path points to another redirect."""
        with mock.patch('app.seeds.forms.RedirectsFile') as mock_rdf:
            mock_rdf.exists.return_value = True
            rd1 = Redirect('/one', '/two', 302)
            rd2 = Redirect('/three', '/four', 302)
            rdf = mock.Mock(redirects=[rd1, rd2])
            mock_rdf.return_value = rdf
            form = AddRedirectForm()
            form.new_path.data = '/five'
            form.validate_new_path(form.new_path)
            form.new_path.data = '/three'
            with pytest.raises(ValidationError):
                form.validate_new_path(form.new_path)


class TestEditIndexForm:
    """Test methods of EditIndexForm."""
    @mock.patch('app.seeds.models.Index.query')
    def test_validate_name(self, m_idxq):
        """Raise error if Index with name already exists."""
        m_idxq.return_value = 'Index exists.'
        field = mock.MagicMock()
        self = mock.MagicMock()
        field.data = 'Index exists.'
        with pytest.raises(ValidationError):
            EditIndexForm.validate_name(self=self, field=field)


class TestEditCommonNameForm:
    """Test methods of EditCommonNameForm."""
    @mock.patch('app.seeds.models.CommonName.query')
    def test_validate_name(self, m_cnq):
        m_cnq.return_value = 'CN Exists.'
        field = mock.MagicMock()
        self = mock.MagicMock()
        field.data = 'CN Exists.'
        with pytest.raises(ValidationError):
            EditCommonNameForm.validate_name(self=self, field=field)

    def test_validate_synonyms_string(self):
        """Raise ValidationError if any synonyms are too long."""
        field = mock.MagicMock()
        field.data = 'Digitalis'
        EditCommonNameForm.validate_synonyms_string(None, field)
        field.data = 'Digitalis, He just kept talking in one long '\
                     'incredibly unbroken sentence moving from topic '\
                     'to topic so that no one had a chance to interrupt'
        with pytest.raises(ValidationError):
            EditCommonNameForm.validate_synonyms_string(None, field)


class TestEditBotanicalNameForm:
    """Test custom methods of EditBotanicalNameForm."""
    @mock.patch('app.seeds.forms.select_field_choices')
    def test_init(self, m_sfc):
        m_sfc.return_value = [(1, 'One'), (2, 'Two'), (3, 'Three')]
        cn1 = CommonName(name='One')
        cn1.id = 1
        cn2 = CommonName(name='Two')
        cn2.id = 2
        obj = BotanicalName(name='Bot nam')
        obj.common_names = [cn1, cn2]
        ebnf = EditBotanicalNameForm(obj=obj)
        assert ebnf.common_names.data == [1, 2]

    @mock.patch('app.seeds.models.BotanicalName.validate')
    def test_validate_name(self, m_bnv):
        """Raise error if data fails to pass BotanicalName.validate."""
        m_bnv.return_value = False
        field = mock.MagicMock()
        field.data = 'invalid BOTANICAL name'
        with pytest.raises(ValidationError):
            EditBotanicalNameForm.validate_name(self=None, field=field)

    def test_validate_synonyms_string_too_long(self):
        """Raise ValidationError if any synonyms are too long."""
        field = mock.MagicMock()
        field.data = 'Digitalis watchus, Innagada davida'
        EditBotanicalNameForm.validate_synonyms_string(None, field)
        field.data = ('Digitalis watchus, He just kept talking in one long '
                      'incredibly unbroken sentence moving from topic to '
                      'topic so that no one had a chance to interrupt')
        with pytest.raises(ValidationError):
            EditBotanicalNameForm.validate_synonyms_string(None, field)

    def test_validate_synonyms_string_not_bn(self):
        """Raise ValidationError if any synonyms are not valid binomen."""
        field = mock.MagicMock()
        field.data = 'Digitalis watchus, Innagada davida'
        EditBotanicalNameForm.validate_synonyms_string(None, field)
        field.data = 'Digitalis watchus, innagada davida'
        with pytest.raises(ValidationError):
            EditBotanicalNameForm.validate_synonyms_string(None, field)


class TestEditSectionForm:
    """Test methods of EditSectionForm."""
    @mock.patch('app.seeds.models.Section.query')
    def test_validate_name(self, m_cq):
        """Raise error if Section already exists."""
        m_cq.return_value = 'Cat exists.'
        field = mock.MagicMock()
        self = mock.MagicMock()
        with pytest.raises(ValidationError):
            EditSectionForm.validate_name(self=self, field=field)


class TestEditCultivarForm:
    """Test custom methods for EditCultivarForm."""
    @mock.patch('app.seeds.models.Cultivar.query')
    def test_validate_name(self, m_cvq):
        """Raise error if Cultivar already exists."""
        m_cvq.return_value = 'Cultivar exists.'
        field = mock.MagicMock()
        field.data = 'Cultivar exists.'
        self = mock.MagicMock()
        with pytest.raises(ValidationError):
            EditCultivarForm.validate_name(self=self, field=field)

    @mock.patch('app.seeds.models.BotanicalName.query')
    def test_validate_botanical_name_id(self, m_bnq):
        """Raise error if selected BN is not in selected CN."""
        bn = BotanicalName('Digitalis über alles')
        cn1 = CommonName(name='Fauxglove')
        cn1.id = 1
        cn2 = CommonName(name='Spuriousglove')
        cn2.id = 2
        bn.common_names = [cn1, cn2]
        m_bnq.return_value = bn
        self = mock.MagicMock()
        self.common_name_id.data = 3
        field = mock.MagicMock()
        with pytest.raises(ValidationError):
            EditCultivarForm.validate_botanical_name_id(self=self, field=field)

    @mock.patch('app.seeds.models.Section.query')
    def test_validate_section_id(self, m_secq):
        """Raise error if selected sec is not in selected CN."""
        sec = Section(name='Five')
        sec.common_name_id = 1
        m_secq.return_value = sec
        self = mock.MagicMock()
        self.common_name_id.data = 2
        field = mock.MagicMock()
        with pytest.raises(ValidationError):
            EditCultivarForm.validate_section_id(self=self, field=field)

    def test_validate_synonyms_string_too_long(self):
        """Raise ValidationError if any synonym is too long."""
        field = mock.MagicMock()
        field.data = 'Fauxy, Fawksy'
        EditCultivarForm.validate_synonyms_string(None, field)
        field.data = ('Fauxy, He just kept talking in one long incredibly '
                      'unbroken sentence moving from topic to topic so that '
                      'no one had a chance to interrupt.')
        with pytest.raises(ValidationError):
            EditCultivarForm.validate_synonyms_string(None, field)


class TestEditPacketForm:
    @mock.patch('app.seeds.models.Packet.query')
    def test_validate_sku(self, m_pktq):
        """Raise error if Packet exists with SKU."""
        m_pktq.return_value = '8675309'
        field = mock.MagicMock()
        self = mock.MagicMock()
        with pytest.raises(ValidationError):
            EditPacketForm.validate_sku(self=self, field=field)


class TestSelectSectionForm:
    @mock.patch('app.seeds.forms.select_field_choices')
    def test_set_select(self, m_sfc):
        """Call select_field_choices with Section and order by name."""
        choices = [(1, 'One'), (2, 'Two')]
        m_sfc.return_value = choices
        self = mock.MagicMock()
        SelectSectionForm.set_select(self=self)
        assert self.section.choices == choices
