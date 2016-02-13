import pytest
from contextlib import redirect_stdout
from decimal import Decimal
from io import StringIO
from unittest import mock
from app.seeds.excel import SeedsWorkbook
from app.seeds.models import (
    BotanicalName,
    CommonName,
    Cultivar,
    Index,
    Packet,
    Quantity,
    Series
)


class TestSeedsWorkbookWithDB:
    """Test methods of SeedsWorkbook which use the database."""

    def test_dump_indexes_adds_to_db(self, db):
        """Dump Indexes sheet data into database."""
        swb = SeedsWorkbook()
        idx1 = Index(name='Perennial', description='Built to last.')
        idx2 = Index(name='Annual', description='Not buil to last.')
        idx3 = Index(name='Herb', description='Not that kind of herb.')
        swb.load_indexes([idx1, idx2, idx3])
        swb.dump_indexes()
        assert Index.query.filter(Index.name == idx1.name).one_or_none()
        assert Index.query.filter(Index.name == idx2.name).one_or_none()
        assert Index.query.filter(Index.name == idx3.name).one_or_none()

    def test_dump_indexes_edits_existing_indexes(self, db):
        idx1 = Index(name='Perennial', description='Lives a long time.')
        idx2 = Index(name='Annual', description='Short-lived.')
        idx3 = Index(name='Herb', description='Some sort of plant.')
        db.session.add_all([idx1, idx2, idx3])
        db.session.commit()
        swb = SeedsWorkbook()
        swb.load_indexes([Index(name='Perennial',
                                description='Built to last.'),
                          Index(name='Annual',
                                description='Not built to last.'),
                          Index(name='Herb',
                                description='Not that kind of herb.')])
        swb.dump_indexes()
        assert idx1.description == 'Built to last.'
        assert idx2.description == 'Not built to last.'
        assert idx3.description == 'Not that kind of herb.'

    @mock.patch('app.seeds.excel.db.session.commit')
    def test_dump_indexes_no_changes(self, m_commit, db):
        """Do not commit if no new indexes added."""
        idx = Index(name='Perennial', description='Built to last.')
        db.session.add(idx)
        db.session.commit()
        swb = SeedsWorkbook()
        swb.load_indexes([Index('Perennial', description='Built to last.')])
        out = StringIO()
        with redirect_stdout(out):
            swb.dump_indexes()
        out.seek(0)
        m_commit.assert_not_called()
        assert 'No changes were made' in out.read()

    def test_dump_common_names_adds_to_database(self, db):
        """Add new common names to the database."""
        cn1 = CommonName(name='Foxglove',
                         description='Spotty!',
                         instructions='Put them in the ground.')
        cn1.index = Index(name='Perennial')
        cn1.invisible = False
        cn1.set_synonyms_string('Digitalis')
        cn2 = CommonName(name='Ageratum',
                         description='Lots of petals.',
                         instructions='Just add water.')
        cn2.index = Index(name='Annual')
        cn2.set_synonyms_string('Floss Flower')
        swb = SeedsWorkbook()
        swb.load_common_names([cn1, cn2])
        swb.dump_common_names()
        assert CommonName.query\
            .join(Index, Index.id == CommonName.index_id)\
            .filter(CommonName._name == 'Foxglove',
                    Index._name == 'Perennial')\
            .one_or_none()
        assert CommonName.query\
            .join(Index, Index.id == CommonName.index_id)\
            .filter(CommonName._name == 'Ageratum',
                    Index._name == 'Annual')\
            .one_or_none()

    @mock.patch('app.seeds.excel.db.session.commit')
    def test_dump_common_names_no_changes(self, m_commit, db):
        """Do not change the db if no differing data present."""
        cn = CommonName(name='Foxglove',
                        description='Spotty!',
                        instructions='Hope for the best.')
        cn.index = Index(name='Perennial')
        db.session.add(cn)
        db.session.commit()
        swb = SeedsWorkbook()
        swb.load_common_names([cn])
        out = StringIO()
        with redirect_stdout(out):
            swb.dump_common_names()
            out.seek(0)
        m_commit.assert_not_called()
        assert 'No changes were made' in out.read()

    def test_dump_common_names_existing_indexes(self, db):
        """Don't create indexes that already exist."""
        idx = Index(name='Perennial')
        db.session.add(idx)
        db.session.commit()
        cn = CommonName(name='Foxglove',
                        description='Spotty!',
                        instructions='Hope for the best.')
        cn.index = Index(name='Perennial')
        swb = SeedsWorkbook()
        swb.load_common_names([cn])
        swb.dump_common_names()
        cnq = CommonName.query\
            .join(Index, Index.id == CommonName.index_id)\
            .filter(CommonName._name == 'Foxglove',
                    Index._name == 'Perennial')\
            .one_or_none()
        assert cnq.index is idx

    def test_dump_common_names_with_parents(self, db):
        """Use existing cn or create new one to fill parent.

        Created parents should be set to invisible.
        """
        idx = Index(name='Vegetable')
        cn1 = CommonName(name='Heirloom Tomato',
                         description='A bit old for eating.',
                         instructions='Pass it on.')
        cnp = CommonName(name='Tomato')
        cn1.parent = cnp
        cn1.index = idx
        cnp.index = idx
        db.session.add(cnp)
        db.session.commit()
        swb = SeedsWorkbook()
        swb.load_common_names([cn1])
        swb.dump_common_names()
        cnq = CommonName.query\
            .join(Index, Index.id == CommonName.index_id)\
            .filter(CommonName._name == 'Heirloom Tomato',
                    Index._name == 'Vegetable')\
            .one_or_none()
        assert cnq.parent is cnp
        assert not cnq.parent.invisible
        cn2 = CommonName(name='Dwarf Cosmos',
                         description='Not as tall as the other cosmos.',
                         instructions='Plant them in space.')
        cnp2 = CommonName(name='Cosmos')
        idx2 = Index(name='Annual')
        cn2.index = idx2
        cnp2.index = idx2
        cn2.parent = cnp2
        swb = SeedsWorkbook()
        swb.load_common_names([cn2])
        swb.dump_common_names()
        cnq2 = CommonName.query\
            .join(Index, Index.id == CommonName.index_id)\
            .filter(CommonName._name == 'Dwarf Cosmos',
                    Index._name == 'Annual')\
            .one_or_none()
        assert cnq2.parent is not cnp2
        assert cnq2.parent.name == 'Cosmos'

    def test_dump_common_names_with_existing_parent(self, db):
        """Load existing parent if present in db."""
        cnp = CommonName(name='Tomato')
        cnp.index = Index(name='Vegetable')
        db.session.add(cnp)
        db.session.commit()
        cn = CommonName(name='Paste Tomato')
        cn.index = Index(name='Vegetable')
        cn.parent = CommonName(name='Tomato')
        cn.parent.index = cn.index
        swb = SeedsWorkbook()
        swb.load_common_names([cn])
        swb.dump_common_names()
        cnq = CommonName.query\
            .join(Index, Index.id == CommonName.index_id)\
            .filter(CommonName.name == 'Paste Tomato')\
            .one_or_none()
        assert cnq.parent is cnp

    def test_dump_common_names_changes_values(self, db):
        """Change description, instructions, and invisible if different."""
        cn = CommonName(name='Foxglove',
                        description='Floral.',
                        instructions='Put in ground.')
        cn.index = Index(name='Perennial')
        cn.set_synonyms_string('Digitalis')
        cn.invisible = True
        db.session.add(cn)
        db.session.commit()
        cn2 = CommonName(name='Foxglove',
                         description='Spotty.',
                         instructions='Hope for the best.')
        cn2.set_synonyms_string('Analogus')
        cn2.index = Index(name='Perennial')
        cn2.invisible = False
        swb = SeedsWorkbook()
        swb.load_common_names([cn2])
        swb.dump_common_names()
        assert cn.description == 'Spotty.'
        assert cn.instructions == 'Hope for the best.'
        assert cn.get_synonyms_string() == 'Analogus'
        assert not cn.invisible

    def test_dump_common_names_clears_synonyms(self, db):
        """Clear synonyms if they need to be emptied."""
        cn = CommonName(name='Foxglove')
        cn.index = Index(name='Perennial')
        cn.set_synonyms_string('Digitalis')
        db.session.add(cn)
        db.session.commit()
        cn2 = CommonName(name='Foxglove')
        cn2.index = Index(name='Perennial')
        swb = SeedsWorkbook()
        swb.load_common_names([cn2])
        out = StringIO()
        with redirect_stdout(out):
            swb.dump_common_names()
        out.seek(0)
        assert 'The synonyms for \'Foxglove\' have been cleared.' in out.read()

    def test_dump_common_names_with_gwcns(self, db):
        """Use existing cns if present, else create for gwcns.

        Set created cns to invisible.
        """
        cn = CommonName(name='Foxglove',
                        description='Spotty.',
                        instructions='Do what you want, man.')
        cn.index = Index(name='Perennial')
        gwcn1 = CommonName(name='Tomato')
        gwcn1.index = Index(name='Vegetable')
        db.session.add(gwcn1)
        db.session.commit()
        gwcn2 = CommonName(name='Butterfly Weed')
        gwcn2.index = Index(name='Annual')
        cn.gw_common_names = [gwcn1, gwcn2]
        swb = SeedsWorkbook()
        swb.load_common_names([cn])
        swb.dump_common_names()
        cnq = CommonName.query\
            .join(Index, Index.id == CommonName.index_id)\
            .filter(CommonName._name == 'Foxglove',
                    Index._name == 'Perennial')\
            .one_or_none()
        assert gwcn1 in cnq.gw_common_names
        assert not gwcn1.invisible
        assert gwcn2 not in cnq.gw_common_names
        for gwcn in cnq.gw_common_names:
            if gwcn.name == 'Butterfly Weed':
                assert gwcn.invisible

    def test_dump_common_names_removes_old_gwcns(self, db):
        """Remove gwcns that are in loaded common name but not in sheet."""
        cn = CommonName(name='Foxglove')
        cn.index = Index(name='Perennial')
        gwcn = CommonName(name='Butterfly Weed')
        gwcn.index = cn.index
        cn.gw_common_names = [gwcn]
        db.session.add(cn)
        db.session.commit()
        assert gwcn in cn.gw_common_names
        cn2 = CommonName(name='Foxglove')
        cn2.index = Index(name='Perennial')
        swb = SeedsWorkbook()
        swb.load_common_names([cn2])
        swb.dump_common_names()
        assert gwcn not in cn.gw_common_names

    def test_dump_common_names_with_gwcvs(self, db):
        """Use existing cvs if present, else create for gwcvs.

        Set created cvs to invisible.
        """
        cn = CommonName(name='Foxglove',
                        description='Spotty.',
                        instructions='Do stuff.')
        cn.index = Index(name='Perennial')
        gwcv1 = Cultivar(name='Blue')
        gwcv1.common_name = CommonName(name='Parrot')
        gwcv1.common_name.index = Index(name='Bird')
        gwcv1.series = Series(name='Norwegian')
        gwcv1.series.common_name = gwcv1.common_name
        db.session.add(gwcv1)
        db.session.commit()
        gwcv2 = Cultivar(name='Blue')
        gwcv2.common_name = CommonName(name='Parrot')
        gwcv2.common_name.index = Index(name='Bird')
        gwcv2.series = Series(name='Norwegian')
        gwcv2.series.common_name = gwcv2.common_name
        gwcv3 = Cultivar(name='Crunchy')
        gwcv3.common_name = CommonName(name='Frog')
        gwcv3.common_name.index = Index(name='Amphibian')
        gwcv3.series = Series(name='Chocolate-covered')
        gwcv3.series.common_name = gwcv3.common_name
        cn.gw_cultivars = [gwcv2, gwcv3]
        swb = SeedsWorkbook()
        swb.load_common_names([cn])
        swb.dump_common_names()
        cnq = CommonName.query\
            .join(Index, Index.id == CommonName.index_id)\
            .filter(CommonName._name == 'Foxglove',
                    Index._name == 'Perennial')\
            .one_or_none()
        assert gwcv1 in cnq.gw_cultivars
        assert gwcv2 not in cnq.gw_cultivars
        gwcvq = Cultivar.from_lookup_dict(gwcv3.lookup_dict())
        print(gwcv3.lookup_dict())
        assert gwcvq in cnq.gw_cultivars
        assert gwcv3 not in cnq.gw_cultivars

    def test_dump_common_names_removes_old_gwcvs(self, db):
        """Remove gwcvs present in loaded cn but not in sheet."""
        cn = CommonName(name='Foxglove')
        cn.index = Index(name='Perennial')
        gwcv = Cultivar(name='Soulmate')
        gwcv.common_name = CommonName(name='Butterfly Weed')
        gwcv.common_name.index = cn.index
        cn.gw_cultivars = [gwcv]
        db.session.add(cn)
        db.session.commit()
        assert gwcv in cn.gw_cultivars
        cn2 = CommonName(name='Foxglove')
        cn2.index = Index(name='Perennial')
        swb = SeedsWorkbook()
        swb.load_common_names([cn2])
        swb.dump_common_names()
        assert gwcv not in cn.gw_cultivars

    def test_dump_common_names_sets_invisible(self, db):
        """Set cn to invisible if invisible set in sheet, and vice-versa."""
        cn = CommonName(name='Foxglove')
        cn.index = Index(name='Perennial')
        cn.invisible = False
        db.session.add(cn)
        db.session.commit()
        cn2 = CommonName(name='Foxglove')
        cn2.index = Index(name='Perennial')
        cn2.invisible = True
        assert not cn.invisible
        swb = SeedsWorkbook()
        swb.load_common_names([cn2])
        swb.dump_common_names()
        assert cn.invisible
        swb = SeedsWorkbook()
        cn2.invisible = False
        swb.load_common_names([cn2])
        swb.dump_common_names()
        assert not cn.invisible

    def test_dump_botanical_names_adds_to_database(self, db):
        """Add new botanical name to database if not already there."""
        bn = BotanicalName(name='Digitalis purpurea')
        bn.common_names = [CommonName(name='Foxglove')]
        bn.common_names[0].index = Index(name='Perennial')
        swb = SeedsWorkbook()
        swb.load_botanical_names([bn])
        swb.dump_botanical_names()
        bnq = BotanicalName.query\
            .filter(BotanicalName.name == 'Digitalis purpurea')\
            .one_or_none()
        assert bnq
        assert bnq.name == 'Digitalis purpurea'
        cn = bnq.common_names[0]
        assert cn.name == 'Foxglove'
        assert cn.index.name == 'Perennial'

    def test_dump_botanical_names_existing(self, db):
        """Use existing botanical name if present."""
        bn1 = BotanicalName(name='Asclepias incarnata')
        bn1.common_names = [CommonName(name='Butterfly Weed')]
        bn1.common_names[0].index = Index(name='Perennial')
        db.session.add(bn1)
        db.session.commit()
        bn2 = BotanicalName(name='Asclepias incarnata')
        bn2.common_names = [CommonName(name='Butterfly Weed')]
        bn2.common_names[0].index = Index(name='Perennial')
        bn2.set_synonyms_string('Innagada davida')
        assert not bn1.get_synonyms_string()
        swb = SeedsWorkbook()
        swb.load_botanical_names([bn2])
        swb.dump_botanical_names()
        assert bn1.get_synonyms_string() == 'Innagada davida'

    @mock.patch('app.seeds.excel.db.session.commit')
    def test_dump_botanical_names_no_changes(self, m_commit, db):
        """Don't change anything given identical data to what's in db."""
        bn1 = BotanicalName(name='Digitalis purpurea')
        bn1.common_names = [CommonName(name='Foxglove')]
        bn1.common_names[0].index = Index(name='Perennial')
        db.session.add(bn1)
        db.session.commit()
        bn2 = BotanicalName(name='Digitalis purpurea')
        bn2.common_names = [CommonName(name='Foxglove')]
        bn2.common_names[0].index = Index(name='Perennial')
        swb = SeedsWorkbook()
        swb.load_botanical_names([bn2])
        out = StringIO()
        with redirect_stdout(out):
            swb.dump_botanical_names()
            out.seek(0)
        m_commit.assert_not_called()
        assert 'No changes were made' in out.read()

    def test_dump_botanical_names_removes_common_names(self, db):
        """Remove common names in bn if not present in sheet."""
        bn = BotanicalName(name='Digitalis über alles')
        cn1 = CommonName(name='Foxglove')
        cn1.index = Index(name='Perennial')
        cn2 = CommonName(name='Digitalis')
        cn2.index = cn1.index
        bn.common_names = [cn1, cn2]
        db.session.add(bn)
        db.session.commit()
        assert len(bn.common_names) == 2
        assert 'Digitalis' in [cn.name for cn in bn.common_names]
        bn2 = BotanicalName(name='Digitalis über alles')
        bn2.common_names = [CommonName(name='Foxglove')]
        bn2.common_names[0].index = Index(name='Perennial')
        swb = SeedsWorkbook()
        swb.load_botanical_names([bn2])
        swb.dump_botanical_names()
        assert len(bn.common_names) == 1
        assert 'Digitalis' not in [cn.name for cn in bn.common_names]

    def test_dump_botanical_names_clears_synonyms(self, db):
        """Clear synonyms if none in sheet."""
        bn = BotanicalName(name='Digitalis purpurea')
        bn.common_names = [CommonName(name='Foxglove')]
        bn.common_names[0].index = Index(name='Perennial')
        bn.set_synonyms_string('Digitalis über alles, Digitalis pururin')
        db.session.add(bn)
        db.session.commit()
        assert bn.get_synonyms_string()
        bn2 = BotanicalName(name='Digitalis purpurea')
        bn2.common_names = [CommonName(name='Foxglove')]
        bn2.common_names[0].index = Index(name='Perennial')
        swb = SeedsWorkbook()
        swb.load_botanical_names([bn2])
        swb.dump_botanical_names()
        assert not bn.get_synonyms_string()

    def test_dump_botanical_names_bad_botanical_name(self, db):
        """Raise a ValueError given a bad botanical name."""
        bn = BotanicalName()
        bn._name = 'Digitalis Invalidus'
        bn.common_name = CommonName(name='Fauxglove')
        bn.common_name.index = Index(name='Spurious')
        swb = SeedsWorkbook()
        swb.load_botanical_names([bn])
        with pytest.raises(ValueError):
            swb.dump_botanical_names()

    def test_dump_series_adds_to_db(self, db):
        """Add new series to database if not already there."""
        sr = Series(name='Polkadot')
        sr.position = Series.BEFORE_CULTIVAR
        sr.description = 'Spotty.'
        sr.common_name = CommonName(name='Foxglove')
        sr.common_name.index = Index(name='Perennial')
        swb = SeedsWorkbook()
        swb.load_series([sr])
        swb.dump_series()
        srq = Series.query\
            .join(CommonName, CommonName.id == Series.common_name_id)\
            .join(Index, Index.id == CommonName.index_id)\
            .filter(Series.name == 'Polkadot',
                    CommonName._name == 'Foxglove',
                    Index._name == 'Perennial')\
            .one_or_none()
        assert srq
        assert srq.position == Series.BEFORE_CULTIVAR
        assert srq.description == 'Spotty.'

    def test_dump_series_existing(self, db):
        """Load and edit existing series if present in db."""
        sr = Series(name='Polkadot')
        sr.position = Series.BEFORE_CULTIVAR
        sr.description = 'Spotty.'
        sr.common_name = CommonName(name='Foxglove')
        sr.common_name.index = Index(name='Perennial')
        db.session.add(sr)
        db.session.commit()
        sr2 = Series(name='Polkadot')
        sr2.position = Series.AFTER_CULTIVAR
        sr2.description = 'Like my shorts!'
        sr2.common_name = CommonName(name='Foxglove')
        sr2.common_name.index = Index(name='Perennial')
        swb = SeedsWorkbook()
        swb.load_series([sr2])
        swb.dump_series()
        srq = Series.query\
            .join(CommonName, CommonName.id == Series.common_name_id)\
            .join(Index, Index.id == CommonName.index_id)\
            .one_or_none()
        assert srq is sr
        assert sr.position == Series.AFTER_CULTIVAR
        assert sr.description == 'Like my shorts!'

    @mock.patch('app.seeds.excel.db.session.commit')
    def test_dump_series_no_changes(self, m_commit, db):
        """Don't commit anything if no changes are made."""
        sr = Series(name='Polkadot')
        sr.position = Series.BEFORE_CULTIVAR
        sr.description = 'Spotty.'
        sr.common_name = CommonName(name='Foxglove')
        sr.common_name.index = Index(name='Perennial')
        db.session.add(sr)
        db.session.commit()
        swb = SeedsWorkbook()
        swb.load_series([sr])
        out = StringIO()
        with redirect_stdout(out):
            swb.dump_series()
        out.seek(0)
        m_commit.assert_not_called()
        assert 'No changes have been made' in out.read()

    def test_dump_series_flips_position(self, db):
        """If sheet position differs from series position in db, change it."""
        sr = Series(name='Polkadot')
        sr.common_name = CommonName(name='Foxglove')
        sr.common_name.index = Index(name='Perennial')
        sr.position = Series.BEFORE_CULTIVAR
        db.session.add(sr)
        db.session.commit()
        assert sr.position == Series.BEFORE_CULTIVAR
        sr2 = Series(name='Polkadot')
        sr2.common_name = CommonName(name='Foxglove')
        sr2.common_name.index = Index(name='Perennial')
        sr2.position = Series.AFTER_CULTIVAR
        swb = SeedsWorkbook()
        swb.load_series([sr2])
        swb.dump_series()
        assert sr.position == Series.AFTER_CULTIVAR
        sr3 = Series(name='Polkadot')
        sr3.common_name = CommonName(name='Foxglove')
        sr3.common_name.index = Index(name='Perennial')
        sr3.position = Series.BEFORE_CULTIVAR
        swb = SeedsWorkbook()
        swb.load_series([sr3])
        swb.dump_series()
        assert sr.position == Series.BEFORE_CULTIVAR
        

    def test_dump_cultivars_adds_to_database(self, db):
        """Add new cultivars to the database."""
        cv = Cultivar(name='Foxy')
        cv.common_name = CommonName(name='Foxglove')
        cv.common_name.index = Index(name='Perennial')
        cv.botanical_name = BotanicalName(name='Digitalis purpurea')
        cv.botanical_name.common_names.append(cv.common_name)
        swb = SeedsWorkbook()
        swb.load_cultivars([cv])
        swb.dump_cultivars()
        cvq = Cultivar.query\
            .join(CommonName, CommonName.id == Cultivar.common_name_id)\
            .join(Index, Index.id == CommonName.index_id)\
            .filter(Cultivar._name == 'Foxy',
                    CommonName._name == 'Foxglove',
                    Index._name == 'Perennial')\
            .one_or_none()
        assert cvq
        assert cvq is not cv

    def test_dump_cultivars_uses_existing_no_series(self, db):
        """Load cultivar if exists, even if no series specified."""
        cv = Cultivar(name='Foxy')
        cv.common_name = CommonName(name='Foxglove')
        cv.common_name.index = Index(name='Perennial')
        cv.botanical_name = BotanicalName(name='Digitalis purpurea')
        cv.botanical_name.common_names.append(cv.common_name)
        cv.description = 'Like Hendrix!'
        cv.in_stock = True
        cv.active = True
        cv.invisible = False
        db.session.add(cv)
        db.session.commit()
        cv2 = Cultivar(name='Foxy')
        cv2.common_name = CommonName(name='Foxglove')
        cv2.common_name.index = Index(name='Perennial')
        cv2.botanical_name = BotanicalName(name='Digitalis purpurea')
        cv2.botanical_name.common_names.append(cv2.common_name)
        cv2.description = 'Like a lady.'
        cv2.in_stock = False
        cv2.active = False
        cv2.invisible = True
        swb = SeedsWorkbook()
        swb.load_cultivars([cv2])
        swb.dump_cultivars()
        cvq = Cultivar.query\
            .join(CommonName, CommonName.id == Cultivar.common_name_id)\
            .join(Index, Index.id == CommonName.index_id)\
            .filter(Cultivar._name == 'Foxy',
                    CommonName._name == 'Foxglove',
                    Index._name == 'Perennial')\
            .one_or_none()
        assert cvq is cv
        assert cvq.description == 'Like a lady.'
        assert not cvq.in_stock
        assert not cvq.active
        assert cvq.invisible

    def test_dump_cultivars_uses_existing_with_series(self, db):
        """Load cultivar if it exists with given series."""
        cv = Cultivar(name='Petra')
        cv.common_name = CommonName(name='Foxglove')
        cv.common_name.index = Index(name='Perennial')
        cv.botanical_name = BotanicalName(name='Digitalis purpurea')
        cv.botanical_name.common_names.append(cv.common_name)
        cv.series = Series(name='Polkadot')
        cv.series.common_name = cv.common_name
        cv.description = 'Got nothin\'.'
        cv.in_stock = True
        cv.active = True
        cv.invisible = False
        db.session.add(cv)
        db.session.commit()
        cv2 = Cultivar(name='Petra')
        cv2.common_name = CommonName(name='Foxglove')
        cv2.common_name.index = Index(name='Perennial')
        cv2.botanical_name = BotanicalName(name='Digitalis purpurea')
        cv2.botanical_name.common_names.append(cv2.common_name)
        cv2.series = Series(name='Polkadot')
        cv2.series.common_name = cv2.common_name
        cv2.description = 'Still got nothin\'.'
        cv2.in_stock = False
        cv2.active = False
        cv2.invisible = True
        swb = SeedsWorkbook()
        swb.load_cultivars([cv2])
        swb.dump_cultivars()
        cvq = Cultivar.query\
            .join(CommonName, CommonName.id == Cultivar.common_name_id)\
            .join(Index, Index.id == CommonName.index_id)\
            .join(Series, Series.id == Cultivar.series_id)\
            .filter(Cultivar._name == 'Petra',
                    CommonName._name == 'Foxglove',
                    Index._name == 'Perennial',
                    Series.name == 'Polkadot')\
            .one_or_none()
        assert cvq is cv
        assert cv.description == 'Still got nothin\'.'
        assert not cv.in_stock
        assert not cv.active
        assert cv.invisible

    @mock.patch('app.seeds.excel.db.session.commit')
    def test_dump_cultivars_no_changes(self, m_commit, db):
        """Do not add anything to the database given identical data."""
        cv = Cultivar(name='Petra')
        cv.common_name = CommonName(name='Foxglove')
        cv.common_name.index = Index(name='Perennial')
        cv.botanical_name = BotanicalName(name='Digitalis purpurea')
        cv.botanical_name.common_names.append(cv.common_name)
        cv.series = Series(name='Polkadot')
        cv.series.common_name = cv.common_name
        cv.description = 'Got nothin\'.'
        cv.in_stock = True
        cv.active = True
        cv.invisible = False
        db.session.add(cv)
        db.session.commit()
        cv2 = Cultivar(name='Petra')
        cv2.common_name = CommonName(name='Foxglove')
        cv2.common_name.index = Index(name='Perennial')
        cv2.botanical_name = BotanicalName(name='Digitalis purpurea')
        cv2.botanical_name.common_names.append(cv2.common_name)
        cv2.series = Series(name='Polkadot')
        cv2.series.common_name = cv2.common_name
        cv2.description = 'Got nothin\'.'
        cv2.in_stock = True
        cv2.active = True
        cv2.invisible = False
        swb = SeedsWorkbook()
        swb.load_cultivars([cv2])
        out = StringIO()
        with redirect_stdout(out):
            swb.dump_cultivars()
        out.seek(0)
        m_commit.assert_not_called()
        assert 'No changes have been made' in out.read()

    def test_dump_packets_adds_to_database(self, db):
        """Add new packets to the database."""
        pkt = Packet(sku='8675309')
        pkt.price = Decimal('3.50')
        pkt.quantity = Quantity(value=100, units='seeds')
        pkt.cultivar = Cultivar(name='Foxy')
        pkt.cultivar.common_name = CommonName(name='Foxglove')
        pkt.cultivar.common_name.index = Index(name='Perennial')
        swb = SeedsWorkbook()
        swb.load_packets([pkt])
        swb.dump_packets()
        pktq = Packet.query.filter(Packet.sku == '8675309').one_or_none()
        assert pktq
        assert pktq.price == Decimal('3.50')
        assert pktq.cultivar.name == 'Foxy'
        assert pktq.cultivar.common_name.name == 'Foxglove'
        assert pktq.cultivar.common_name.index.name == 'Perennial'

    def test_dump_packets_adds_to_database_with_series(self, db):
        """Add all data, including series, if a series is in the sheet."""
        pkt = Packet(sku='8675309')
        pkt.price = Decimal('3.50')
        pkt.quantity = Quantity(value=100, units='seeds')
        pkt.cultivar = Cultivar(name='Petra')
        pkt.cultivar.common_name = CommonName(name='Foxglove')
        pkt.cultivar.common_name.index = Index(name='Perennial')
        pkt.cultivar.series = Series(name='Polkadot')
        pkt.cultivar.series.common_name = pkt.cultivar.common_name
        swb = SeedsWorkbook()
        swb.load_packets([pkt])
        swb.dump_packets()
        pktq = Packet.query.filter(Packet.sku == '8675309').one_or_none()
        assert pktq
        assert pktq.cultivar.series.name == 'Polkadot'

    def test_dump_packets_uses_existing(self, db):
        """Use existing packet from db if present."""
        pkt = Packet(sku='8675309')
        pkt.price = Decimal('3.50')
        pkt.quantity = Quantity(value=100, units='seeds')
        pkt.cultivar = Cultivar(name='Foxy')
        pkt.cultivar.common_name = CommonName(name='Foxglove')
        pkt.cultivar.common_name.index = Index(name='Perennial')
        db.session.add(pkt)
        db.session.commit()
        pkt2 = Packet(sku='8675309')
        pkt2.price = Decimal('1.99')
        pkt2.quantity = Quantity(value=100, units='seeds')
        pkt2.cultivar = Cultivar(name='Foxy')
        pkt2.cultivar.common_name = CommonName(name='Foxglove')
        pkt2.cultivar.common_name.index = Index(name='Perennial')
        swb = SeedsWorkbook()
        swb.load_packets([pkt2])
        swb.dump_packets()
        pktq = Packet.query.filter(Packet.sku == '8675309').one_or_none()
        assert pktq is pkt
        assert pkt.price == Decimal('1.99')

    def test_dump_packets_deletes_orphaned_quantity(self, db):
        """Delete quantity row if it has no packets associated with it."""
        pkt = Packet(sku='8675309')
        pkt.price = Decimal('3.50')
        pkt.quantity = Quantity(value=100, units='seeds')
        pkt.cultivar = Cultivar(name='Foxy')
        pkt.cultivar.common_name = CommonName(name='Foxglove')
        pkt.cultivar.common_name.index = Index(name='Perennial')
        db.session.add(pkt)
        db.session.commit()
        pkt2 = Packet(sku='8675309')
        pkt2.price = Decimal('3.50')
        pkt2.quantity = Quantity(value='1/2', units='gram')
        pkt2.cultivar = Cultivar(name='Foxy')
        pkt2.cultivar.common_name = CommonName(name='Foxglove')
        pkt2.cultivar.common_name.index = Index(name='Perennial')
        swb = SeedsWorkbook()
        swb.load_packets([pkt2])
        swb.dump_packets()
        assert not Quantity.query\
            .filter(Quantity.value == Quantity.for_cmp(100),
                    Quantity.units == 'seeds')\
            .one_or_none()
        qtyq = Quantity.query\
            .filter(Quantity.value == Quantity.for_cmp('1/2'),
                    Quantity.units == 'gram')\
            .one_or_none()
        assert pkt.quantity is qtyq
