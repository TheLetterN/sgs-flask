from unittest import mock
import pytest
from wtforms import ValidationError
from app.seeds.forms import (
    AddBotanicalNameForm,
    AddCommonNameForm,
    AddPacketForm,
    AddRedirectForm,
    AddCultivarForm,
    EditBotanicalNameForm,
    EditCategoryForm,
    EditCommonNameForm,
    EditCultivarForm,
    EditSeriesForm,
    NotSpace,
    ReplaceMe,
    RRPath,
    USDollar
)
from app.redirects import Redirect
from app.seeds.models import (
    BotanicalName,
    Category,
    CommonName,
    Cultivar,
    Series
)
from tests.conftest import app  # noqa


class TestValidators:
    """Test custom validator classes."""
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

    def test_usdollar(self, app):
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
        with pytest.raises(ValidationError):
            form.name.data = '12.999'
            usd.__call__(form, form.name)


class TestAddBotanicalNameForm:
    """Test custom methods of AddBotanicalNameForm."""
    def test_validate_synonyms(self, app):
        """Raise validation error if any synonyms don't work."""
        form = AddBotanicalNameForm()
        form.name.data = 'Digitalis purpurea'
        form.synonyms.data = 'Digitalis watchus, Digitalis thermometer'
        form.validate_synonyms(form.synonyms)
        form.synonyms.data = 'Digitalis watchus, Digitalis purpurea'
        with pytest.raises(ValidationError):
            form.validate_synonyms(form.synonyms)
        form.synonyms.data = 'Digitalis watchus, He just kept talking in one '\
                             'long incredibly unbroken sentence moving from '\
                             'topic to topic so that no one had a chance to '\
                             'interrupt'
        with pytest.raises(ValidationError):
            form.validate_synonyms(form.synonyms)
        form.synonyms.data = 'Digitalis watchus, Digitalis Walrus'
        with pytest.raises(ValidationError):
            form.validate_synonyms(form.synonyms)


class TestAddCommonNameForm:
    """Test custom methods of AddCommonNameForm."""
    def test_validate_synonyms(self, app):
        """Raise a ValidationError if any synonyms are more than 64 chars."""
        form = AddCommonNameForm()
        form.name.data = 'Foxglove'
        form.synonyms.data = 'Sixty-four characters is actually quite a lot '\
                             'of characters to fit in one name, the limit is '\
                             'perfectly reasonable'
        with pytest.raises(ValidationError):
            form.validate_synonyms(form.synonyms)
        form.synonyms.data = 'Foxglove, Digitalis'
        with pytest.raises(ValidationError):
            form.validate_synonyms(form.synonyms)


class TestAddPacketForm:
    """Test custom methods of AddPacketForm."""
    def test_validate_quantity(self, app):
        """Raise ValidationError if quantity can't be parsed."""
        form = AddPacketForm()
        form.quantity.data = '100'
        form.validate_quantity(form.quantity)
        form.quantity.data = '2.3423'
        form.validate_quantity(form.quantity)
        form.quantity.data = '3/4'
        form.validate_quantity(form.quantity)
        form.quantity.data = '1 1/2'
        form.validate_quantity(form.quantity)
        form.quantity.data = '$2'
        with pytest.raises(ValidationError):
            form.validate_quantity(form.quantity)
        form.quantity.data = '3/4/13'
        with pytest.raises(ValidationError):
            form.validate_quantity(form.quantity)
            form.quantity.data = '127.0.0.1'
        with pytest.raises(ValidationError):
            form.validate_quantity(form.quantity)


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


class TestAddCultivarForm:
    """Test custom methods of AddCultivarForm."""
    def test_validate_synonyms(self, app):
        """Raise ValidationError if any synonyms are invalid."""
        form = AddCultivarForm()
        form.name.data = 'Foxy'
        form.synonyms.data = 'Digitalis'
        form.validate_synonyms(form.synonyms)
        form.synonyms.data = 'Digitalis, Foxy'
        with pytest.raises(ValidationError):
            form.validate_synonyms(form.synonyms)
        form.synonyms.data = 'Digitalis, He just spoke in one long incredibly'\
                             ' unbroken sentence moving from topic to topic'\
                             ' it was quite hypnotic'
        with pytest.raises(ValidationError):
            form.validate_synonyms(form.synonyms)


class TestEditBotanicalNameForm:
    """Test custom methods of EditBotanicalNameForm."""
    def test_populate(self, app):
        """Populate form from a BotanicalName object."""
        bn = BotanicalName()
        bn.name = 'Asclepias incarnata'
        bns = BotanicalName()
        bns.name = 'Innagada davida'
        bn.synonyms.append(bns)
        form = EditBotanicalNameForm()
        form.populate(bn)
        assert form.name.data == bn.name
        assert form.synonyms.data == 'Innagada davida'

    def test_validate_name(self):
        """Raise ValidationError if name doesn't appear to be a binomen."""
        form = EditBotanicalNameForm()
        form.name.data = 'Digitalis purpurea'
        form.validate_name(form.name)
        form.name.data = 'digitalis watchus'
        with pytest.raises(ValidationError):
            form.validate_name(form.name)

    def test_validate_synonyms_same_as_name(self):
        """Raise ValidationError if any synonyms same as name."""
        form = EditBotanicalNameForm()
        form.name.data = 'Digitalis purpurea'
        form.synonyms.data = 'Digitalis watchus, Innagada davida'
        form.validate_synonyms(form.synonyms)
        form.synonyms.data = 'Digitalis purpurea, Digitalis watchus'
        with pytest.raises(ValidationError):
            form.validate_synonyms(form.synonyms)

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


class TestEditCategoryForm:
    """Test custom methods of EditCategoryForm."""
    def test_populate(self, app):
        """Populate form from a Category object."""
        category = Category()
        category.name = 'Annual Flowers'
        category.description = 'Not really built to last.'
        form = EditCategoryForm()
        form.populate(category)
        assert form.category.data == category.name
        assert form.description.data == category.description


class TestEditCommonNameForm:
    """Test custom methods of EditCommonNameForm."""
    def test_populate(self, app):
        """Populate form from CommonName object."""
        cn = CommonName()
        cn.id = 1
        cn.name = 'Dwarf Coleus'
        cat = Category()
        cat.id = 1
        cat.name = 'Perennial Flower'
        cn.categories.append(cat)
        cnp = CommonName()
        cnp.id = 2
        cnp.name = 'Coleus'
        cn.parent = cnp
        cns = CommonName()
        cns.name = 'Vertically Challenged Coleus'
        cn.synonyms.append(cns)
        gwcn = CommonName()
        gwcn.id = 3
        gwcn.name = 'Foxglove'
        cn.gw_common_names.append(gwcn)
        gwcv = Cultivar()
        gwcv.name = 'Foxy'
        gwcv.id = 1
        cn.gw_cultivars.append(gwcv)
        cn.description = 'Not mint.'
        form = EditCommonNameForm()
        form.populate(cn)
        assert form.name.data == cn.name
        assert form.description.data == cn.description
        assert form.synonyms.data == cns.name
        assert cat.id in form.categories.data
        assert gwcn.id in form.gw_common_names.data
        assert gwcv.id in form.gw_cultivars.data

    def test_validate_synonyms_same_as_name(self):
        """Raise ValidationError if a synonym is the same as name."""
        form = EditCommonNameForm()
        form.name.data = 'Foxglove'
        form.synonyms.data = 'Digitalis'
        form.validate_synonyms(form.synonyms)
        form.synonyms.data = 'Digitalis, Foxglove'
        with pytest.raises(ValidationError):
            form.validate_synonyms(form.synonyms)

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
    def test_populate(self):
        """Populate form with values from a Cultivar."""
        form = EditCultivarForm()
        cv = Cultivar(name='Foxy', description='Like Hendrix!')
        cv.id = 1
        bn = BotanicalName(name='Digitalis purpurea')
        bn.id = 2
        cv.botanical_name = bn
        cat = Category(name='Perennial Flower')
        cat.id = 3
        cv.categories.append(cat)
        cn = CommonName(name='Foxglove')
        cn.id = 4
        cv.common_name = cn
        cv.in_stock = True
        cv.dropped = True
        gwcn = CommonName(name='Butterfly Weed')
        gwcn.id = 5
        cv.gw_common_names.append(gwcn)
        gwcv = Cultivar(name='Soulmate')
        gwcv.common_name = gwcn
        gwcv.id = 6
        cv.gw_cultivars.append(gwcv)
        series = Series(name='Spotty')
        series.id = 7
        cv.series = series
        cvsyn = Cultivar(name='Fauxy')
        cvsyn.id = 8
        cv.synonyms.append(cvsyn)
        form.populate(cv)
        assert form.name.data == 'Foxy'
        assert form.description.data == 'Like Hendrix!'
        assert cat.id in form.categories.data
        assert form.common_name.data == cn.id
        assert form.in_stock.data
        assert form.dropped.data
        assert gwcn.id in form.gw_common_names.data
        assert gwcv.id in form.gw_cultivars.data
        assert form.series.data == series.id
        assert form.synonyms.data == 'Fauxy'

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
