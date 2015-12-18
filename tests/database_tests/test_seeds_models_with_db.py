from app.seeds.models import (
    BotanicalName,
    Category,
    Image,
    Cultivar
)
from tests.conftest import app, db  # noqa


class TestBotanicalNameWithDB:
    """Test BotanicalName model methods that require database access."""
    def test_name_is_queryable(self, db):
        """.name should be usable in queries."""
        bn = BotanicalName()
        db.session.add(bn)
        bn.name = 'Asclepias incarnata'
        assert BotanicalName.query\
            .filter_by(name='Asclepias incarnata').first() is bn


class TestCategoryWithDB:
    """Test Category model methods that require database access."""
    def test_category_expression(self, db):
        """.name should be usable in filters."""
        cat1 = Category()
        cat2 = Category()
        cat3 = Category()
        db.session.add_all([cat1, cat2, cat3])
        cat1.name = 'Annual Flower'
        cat2.name = 'Perennial Flower'
        cat3.name = 'Rock'
        db.session.commit()
        assert Category.query.filter_by(name='Annual Flower')\
            .first() is cat1
        assert Category.query.filter_by(name='Perennial Flower')\
            .first() is cat2
        assert Category.query.filter_by(name='Rock').first() is cat3


class TestCultivarWithDB:
    """Test Cultivar model methods that require database access."""
    def test_thumbnail_path_with_thumbnail(self, db):
        """Return path to thumbnail if it exists."""
        cultivar = Cultivar()
        thumb = Image()
        db.session.add_all([cultivar, thumb])
        cultivar.name = 'Foxy'
        thumb.filename = 'hello.jpg'
        cultivar.thumbnail = thumb
        db.session.commit()
        assert cultivar.thumbnail_path == 'images/hello.jpg'

    def test_thumbnail_path_no_thumbnail(self, db):
        """Return path to defaulth thumbnail if cultivar has none."""
        cultivar = Cultivar()
        db.session.add(cultivar)
        cultivar.name = 'Foxy'
        db.session.commit()
        assert cultivar.thumbnail_path == 'images/default_thumb.jpg'
