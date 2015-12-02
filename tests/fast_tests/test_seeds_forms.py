from app.seeds.forms import (
    EditBotanicalNameForm,
    EditCategoryForm,
    EditCommonNameForm
)
from app.seeds.models import BotanicalName, Category, CommonName
from tests.conftest import app  # noqa


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
