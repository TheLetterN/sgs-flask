from unittest import mock
import pytest
from wtforms import ValidationError
from app.seeds.forms import (
    AddPacketForm,
    AddRedirectForm,
    EditBotanicalNameForm,
    EditCommonNameForm,
    EditCultivarForm,
    EditSeriesForm,
    IsBotanicalName,
    NotSpace,
    ReplaceMe,
    RRPath,
    select_field_choices,
    SynonymLength,
    USDollar
)
from app.redirects import Redirect
from app.seeds.models import (
    BotanicalName,
    Index,
    CommonName,
    Cultivar,
    Series
)
from tests.conftest import app  # noqa


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
        form = EditBotanicalNameForm()
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

    def test_usdollar(self):
        """Raise validation error if value can't be converted to USD."""
        usd = USDollar()
        form = EditBotanicalNameForm()
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

    def test_synonymlength_too_short(self):
        """Raise ValidationError if any synonym is too short."""
        sl = SynonymLength(6, 12)
        field = mock.MagicMock()
        field.data = 'oops'
        with pytest.raises(ValidationError):
            sl.__call__(None, field)

    def test_synonymlength_too_long(self):
        """Raise ValidationError if any synonym is too long."""
        sl = SynonymLength(1, 6)
        field = mock.MagicMock()
        field.data = 'Too long; didn\'t read'
        with pytest.raises(ValidationError):
            sl.__call__(None, field)

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


class TestEditBotanicalNameForm:
    """Test custom methods of EditBotanicalNameForm."""
    def test_populate(self, app):
        """Populate form from a BotanicalName object."""
        bn = BotanicalName()
        bn.name = 'Asclepias incarnata'
        bn.synonyms_string = 'Innagada davida'
        form = EditBotanicalNameForm()
        form.populate(bn)
        assert form.name.data == bn.name
        assert form.synonyms.data == 'Innagada davida'

    def test_validate_synonyms_too_long(self):
        """Raise ValidationError if any synonyms are too long."""
        form = EditBotanicalNameForm()
        form.name.data = 'Digitalis purpurea'
        form.synonyms.data = 'Digitalis watchus, Innagada davida'
        form.validate_synonyms(form.synonyms)
        form.synonyms.data = 'Digitalis watchus, He just kept talking in one '\
                             'long incredibly unbroken sentence moving from '\
                             'topic to topic so that no one had a chance to '\
                             'interrupt'
        with pytest.raises(ValidationError):
            form.validate_synonyms(form.synonyms)

    def test_validate_synonyms(self):
        """Raise ValidationError if any synonyms are not valid binomen."""
        form = EditBotanicalNameForm()
        form.name.data = 'Digitalis purpurea'
        form.synonyms.data = 'Digitalis watchus, Innagada davida'
        form.validate_synonyms(form.synonyms)
        form.synonyms.data = 'Digitalis watchus, innagada davida'
        with pytest.raises(ValidationError):
            form.validate_synonyms(form.synonyms)


class TestEditCommonNameForm:
    """Test custom methods of EditCommonNameForm."""

    def test_validate_synonyms_too_long(self):
        """Raise ValidationError if any synonyms are too long."""
        form = EditCommonNameForm()
        form.name.data = 'Foxglove'
        form.synonyms.data = 'Digitalis'
        form.validate_synonyms(form.synonyms)
        form.synonyms.data = 'Digitalis, He just kept talking in one long '\
                             'incredibly unbroken sentence moving from topic '\
                             'to topic so that no one had a chance to '\
                             'interrupt'
        with pytest.raises(ValidationError):
            form.validate_synonyms(form.synonyms)


class TestEditCultivarForm:
    """Test custom methods for EditCultivarForm."""

    def test_validate_synonyms_same_name(self):
        """Raise ValidationError if any synonym same as name."""
        form = EditCultivarForm()
        form.name.data = 'Foxy'
        form.synonyms.data = 'Fauxy, Fawksy'
        form.validate_synonyms(form.synonyms)
        form.synonyms.data = 'Fauxy, Fawksy, Foxy'
        with pytest.raises(ValidationError):
            form.validate_synonyms(form.synonyms)

    def test_validate_synonyms_too_long(self):
        """Raise ValidationError if any synonym is too long."""
        form = EditCultivarForm()
        form.name.data = 'Foxy'
        form.synonyms.data = 'Fauxy, Fawksy'
        form.validate_synonyms(form.synonyms)
        form.synonyms.data = 'Fauxy, He just kept talking in one long '\
                             'incredibly unbroken sentence moving from topic '\
                             'to topic so that no one had a chance to '\
                             'interrupt.'
        with pytest.raises(ValidationError):
            form.validate_synonyms(form.synonyms)


class TestEditSeriesForm:
    """Test custom methods in EditSeriesForm."""
    def test_populate(self):
        """Populate form with information from a Series object."""
        form = EditSeriesForm()
        series = Series(name='Polkadot', description='A bit spotty.')
        series.common_name = CommonName('Foxglove')
        series.common_name.id = 1
        form.populate(series)
        assert form.name.data == 'Polkadot'
        assert form.common_name.data == 1
        assert form.description.data == 'A bit spotty.'
