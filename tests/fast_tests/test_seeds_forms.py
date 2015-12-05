import pytest
from wtforms import ValidationError
from app.seeds.forms import (
    AddBotanicalNameForm,
    AddCommonNameForm,
    AddPacketForm,
    AddSeedForm,
    EditBotanicalNameForm,
    EditCategoryForm,
    EditCommonNameForm,
    NotSpace,
    USDollar
)
from app.seeds.models import BotanicalName, Category, CommonName
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
        form.synonyms.data = 'Digitalis watchus, He just spoke in one long'\
                             'incredibly unbroken sentence moving from topic'\
                             'to topic it was quite hypnotic'
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


class TestAddSeedForm:
    """Test custom methods of AddSeedForm."""
    def test_validate_synonyms(self, app):
        """Raise ValidationError if any synonyms are invalid."""
        form = AddSeedForm()
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
        form = EditBotanicalNameForm()
        form.populate(bn)
        assert form.name.data == bn.name


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
        cn.name = 'Coleus'
        cn.description = 'Not mint.'
        form = EditCommonNameForm()
        form.populate(cn)
        assert cn.name == form.name.data
        assert cn.description == form.description.data
