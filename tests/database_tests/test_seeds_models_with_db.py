from app.seeds.models import (
    BotanicalName,
    Index,
    CommonName,
    Image,
    Cultivar,
    Series
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

    def test_clear_synonyms(self, db):
        """Clear all synonyms from BotanicalName and delete orphans."""
        bn1 = BotanicalName(name='Digitalis purpurea')
        bn2 = BotanicalName(name='Digitalis interspecific hybrid')
        s1 = BotanicalName(name='Digitalis watchus')
        s1.invisible = True
        s2 = BotanicalName(name='Innagada davida')
        s2.invisible = True
        s3 = BotanicalName(name='Canis lupus')
        s3.invisible = True
        db.session.add_all([bn1, bn2, s1, s2, s3])
        bn1.synonyms = [s1, s2, s3]
        bn2.synonyms = [s1]
        db.session.commit()
        bn1.clear_synonyms()
        assert not bn1.synonyms
        assert not BotanicalName.query.filter_by(name=s2.name).first()
        assert not BotanicalName.query.filter_by(name=s3.name).first()
        assert BotanicalName.query.filter_by(name=s1.name).first()
        assert s1 in bn2.synonyms

    def test_set_synonyms_from_string_list_with_existing(self, db):
        """Remove synonyms not present in list, add present in list."""
        bn = BotanicalName(name='Digitalis purpurea')
        s1 = BotanicalName(name='Digitalis watchus')
        s1.invisible = True
        s2 = BotanicalName(name='Digitalis über alles')
        s2.invisible = True
        db.session.add_all([bn, s1, s2])
        bn.synonyms = [s1, s2]
        db.session.commit()
        bn.set_synonyms_from_string_list('Digitalis watchus, Digitalis scalus')
        db.session.commit()
        assert not BotanicalName.query.filter_by(name=s2.name).first()
        s3 = BotanicalName.query.filter_by(name='Digitalis scalus').first()
        assert s1 in bn.synonyms
        assert s2 not in bn.synonyms
        assert s3 in bn.synonyms

    def test_set_synonyms_from_string_list_no_existing(self, db):
        """Create synonym if not in db, or load from db if exist."""
        bn = BotanicalName(name='Digitalis purpurea')
        s1 = BotanicalName(name='Digitalis watchus')
        s1.invisible = True
        db.session.add_all([bn, s1])
        db.session.commit()
        bn.set_synonyms_from_string_list('Digitalis watchus, Digitalis scalus')
        db.session.commit()
        s2 = BotanicalName.query.filter_by(name='Digitalis scalus').first()
        assert s2.invisible
        assert s1 in bn.synonyms
        assert s2 in bn.synonyms


class TestIndexWithDB:
    """Test Index model methods that require database access."""
    def test_index_expression(self, db):
        """.name should be usable in filters."""
        idx1 = Index()
        idx2 = Index()
        idx3 = Index()
        db.session.add_all([idx1, idx2, idx3])
        idx1.name = 'Annual Flower'
        idx2.name = 'Perennial Flower'
        idx3.name = 'Rock'
        db.session.commit()
        assert Index.query.filter_by(name='Annual Flower')\
            .first() is idx1
        assert Index.query.filter_by(name='Perennial Flower')\
            .first() is idx2
        assert Index.query.filter_by(name='Rock').first() is idx3


class TestCommonNameWithDB:
    """Test CommonName model methods that require db access."""
    def test_clear_synonyms(self, db):
        """Remove synonyms from CommonName and delete orphans."""
        cn1 = CommonName(name='Foxglove')
        cn2 = CommonName(name='Digitalis')
        s1 = CommonName(name='Fauxglove')
        s1.invisible = True
        s2 = CommonName(name='Fawksglove')
        s2.invisible = True
        s3 = CommonName(name='Focksglove')
        s3.invisible = True
        db.session.add_all([cn1, cn2, s1, s2, s3])
        cn1.synonyms = [s1, s2, s3]
        cn2.synonyms = [s1, s2]
        db.session.commit()
        cn1.clear_synonyms()
        assert not cn1.synonyms
        assert s1 in cn2.synonyms
        assert s2 in cn2.synonyms
        assert not CommonName.query.filter_by(name='Focksglove').first()
        assert CommonName.query.filter_by(name='Fauxglove').first()
        assert CommonName.query.filter_by(name='Fawksglove').first()

    def test_set_synonyms_from_string_list_with_existing(self, db):
        """Remove synonyms not present in list, add present ones."""
        cn = CommonName(name='Foxglove')
        s1 = CommonName(name='Fauxglove')
        s1.invisible = True
        s2 = CommonName(name='Fawksglove')
        s2.invisible = True
        db.session.add_all([cn, s1])
        cn.synonyms = [s1, s2]
        db.session.commit()
        cn.set_synonyms_from_string_list('Fauxglove, Focksglove')
        db.session.commit()
        assert s1 in cn.synonyms
        s3 = CommonName.query.filter_by(name='Focksglove').first()
        assert s3.invisible
        assert s3 in cn.synonyms
        assert s2 not in cn.synonyms
        assert not CommonName.query.filter_by(name='Fawksglove').first()

    def test_set_synonyms_from_string_list_no_existing(self, db):
        """Add synonyms CN from db if present, otherwise create them."""
        cn = CommonName(name='Foxglove')
        s1 = CommonName(name='Fauxglove')
        s1.invisible = True
        db.session.add_all([cn, s1])
        db.session.commit()
        cn.set_synonyms_from_string_list('Fauxglove, Fawksglove')
        s2 = CommonName.query.filter_by(name='Fawksglove').first()
        assert s2.invisible
        assert s1 in cn.synonyms
        assert s2 in cn.synonyms


class TestCultivarWithDB:
    """Test Cultivar model methods that require database access."""
    def test_from_lookup_string(self, db):
        """Instantiate a Cultivar using a formatted string.

        It should only load a Cultivar that exactly matches the data in the
        string.
        """
        cv1 = Cultivar(name='Name')
        cv2 = Cultivar(name='Name')
        cv3 = Cultivar(name='Name')
        cv4 = Cultivar(name='Name')
        cv5 = Cultivar(name='Name')
        cv6 = Cultivar(name='Name')
        cv7 = Cultivar(name='Like, Other Name')
        cn = CommonName(name='Common Name')
        cn2 = CommonName(name='Other Common Name')
        sr = Series(name='Series')
        sr2 = Series(name='Other Series')
        cv2.common_name = cn
        cv3.common_name = cn
        cv4.common_name = cn2
        cv5.common_name = cn2
        cv6.common_name = cn
        cv7.common_name = cn
        cv3.series = sr
        cv5.series = sr
        cv6.series = sr2
        cv7.series = sr

        db.session.add_all([cv1,
                            cv2,
                            cv3,
                            cv4,
                            cv5,
                            cv6,
                            cv7,
                            cn,
                            cn2,
                            sr,
                            sr2])
        db.session.commit()
        assert Cultivar.from_lookup_string('{CULTIVAR NAME: Name}') is cv1
        assert Cultivar.from_lookup_string(
            '{CULTIVAR NAME: Name}, {COMMON NAME: Common Name}'
        ) is cv2
        assert Cultivar.from_lookup_string(
            '{CULTIVAR NAME: Name}, '
            '{COMMON NAME: Common Name}, '
            '{SERIES: Series}'
        ) is cv3
        assert Cultivar.from_lookup_string(
            '{CULTIVAR NAME: Name}, {COMMON NAME: Other Common Name}'
        ) is cv4
        assert Cultivar.from_lookup_string(
            '{CULTIVAR NAME: Name}, '
            '{COMMON NAME: Other Common Name}, '
            '{SERIES: Series}'
        ) is cv5
        assert Cultivar.from_lookup_string(
            '{CULTIVAR NAME: Name}, '
            '{COMMON NAME: Common Name}, '
            '{SERIES: Other Series}'
        ) is cv6
        assert Cultivar.from_lookup_string(
            '{CULTIVAR NAME: Like, Other Name}, '
            '{COMMON NAME: Common Name}, '
            '{SERIES: Series}'
        ) is cv7

    def test_clear_synonyms(self, db):
        """Remove all synonyms and delete orphans."""
        cv1 = Cultivar(name='Foxy')
        cv2 = Cultivar(name='Focksy')
        s1 = Cultivar(name='Fauxy')
        s1.invisible = True
        s2 = Cultivar(name='Fawksy')
        s2.invisible = True
        db.session.add_all([cv1, cv2, s1, s2])
        cv1.synonyms = [s1, s2]
        cv2.synonyms = [s1]
        db.session.commit()
        cv1.clear_synonyms()
        db.session.commit()
        assert not cv1.synonyms
        assert not Cultivar.query.filter_by(name='Fawksy').first()
        assert Cultivar.query.filter_by(name='Fauxy').first()
        assert s1 in cv2.synonyms

    def test_set_synonyms_from_string_list_with_existing(self, db):
        """Remove synonyms not present in list, add present ones."""
        cv = Cultivar(name='Foxy')
        s1 = Cultivar(name='Fauxy')
        s1.invisible = True
        s2 = Cultivar(name='Fawksy')
        s2.invisible = True
        db.session.add_all([cv, s1, s2])
        cv.synonyms = [s1, s2]
        db.session.commit()
        cv.set_synonyms_from_string_list('Fauxy, Focksy')
        db.session.commit()
        assert s1 in cv.synonyms
        assert s2 not in cv.synonyms
        assert not Cultivar.query.filter_by(name='Fawksy').first()
        s3 = Cultivar.query.filter_by(name='Focksy').first()
        assert s3 in cv.synonyms

    def test_set_synonyms_from_string_list_no_existing(self, db):
        """Add synonyms from list if not present."""
        cv = Cultivar(name='Foxy')
        s1 = Cultivar(name='Fauxy')
        db.session.add_all([cv, s1])
        db.session.commit()
        cv.set_synonyms_from_string_list('Fauxy, Fawksy, Focksy')
        db.session.commit()
        assert s1 in cv.synonyms
        s2 = Cultivar.query.filter_by(name='Fawksy').first()
        assert s2.invisible
        assert s2 in cv.synonyms
        s3 = Cultivar.query.filter_by(name='Focksy').first()
        assert s3.invisible
        assert s3 in cv.synonyms

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
