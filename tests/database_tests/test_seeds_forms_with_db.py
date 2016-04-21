from unittest import mock

import pytest
from wtforms import ValidationError
from app.seeds.forms import (
    AddBotanicalNameForm,
    AddSectionForm,
    AddCommonNameForm,
    AddIndexForm,
    AddPacketForm,
    AddCultivarForm,
    EditSectionForm,
    EditCultivarForm,
    EditPacketForm,
    select_field_choices
)
from app.seeds.models import (
    BotanicalName,
    Section,
    CommonName,
    Index,
    Packet,
    Cultivar
)


class TestFunctionsWithDB:
    """Test module-level methods with the database."""
    def test_select_field_choices_with_model_by_id(self, db):
        """Generate tuple list from queried items ordered by id."""
        idx1 = Index(name='Perennial')
        idx2 = Index(name='Annual')
        idx3 = Index(name='Rock')
        idx1.id = 1
        idx2.id = 2
        idx3.id = 3
        db.session.add_all([idx1, idx2, idx3])
        db.session.flush()
        stls = select_field_choices(model=Index,
                                    title_attribute='name',
                                    order_by='id')
        assert stls == [(1, 'Perennial'), (2, 'Annual'), (3, 'Rock')]

    def test_select_field_choices_with_model_by_name(self, db):
        """Generate tuple list from queried items ordered by name."""
        idx1 = Index(name='Perennial')
        idx2 = Index(name='Annual')
        idx3 = Index(name='Rock')
        idx1.id = 1
        idx2.id = 2
        idx3.id = 3
        db.session.add_all([idx1, idx2, idx3])
        db.session.flush()
        stls = select_field_choices(model=Index,
                                    title_attribute='name',
                                    order_by='name')
        assert stls == [(2, 'Annual'), (1, 'Perennial'), (3, 'Rock')]


class TestAddIndexFormWithDB:
    """Test custom methods of AddIndexForm."""
    def test_validate_name(self, db):
        """Raise a ValidationError if index name already in db."""
        index = Index(name='Annual')
        db.session.add(index)
        db.session.commit()
        form = AddIndexForm()
        form.name.data = 'Perennial'
        form.validate_name(form.name)
        form.name.data = 'Annual'
        with pytest.raises(ValidationError):
            form.validate_name(form.name)


class TestAddCommonNameFormWithDB:
    """Test custom methods of AddCommonNameForm."""
    def test_validate_name(self, db):
        """Raise a Validation error if CommonName & Index combo in db."""
        cn = CommonName(name='Foxglove', index=Index(name='Perennial'))
        db.session.add(cn)
        db.session.commit()
        form = AddCommonNameForm(cn.index)
        form.name.data = 'Fauxglove'
        form.validate_name(form.name)
        form.name.data = 'Foxglove'
        with pytest.raises(ValidationError):
            form.validate_name(form.name)


class TestAddBotanicalNameFormWithDB:
    """Test custom methods of AddBotanicalNameForm."""
    def test_validate_name(self, db):
        """Raise error if name in DB or invalid botanical name."""
        bn = BotanicalName(name='Asclepias incarnata')
        cn = CommonName(name='Butterfly Weed')
        db.session.add_all([bn, cn])
        bn.common_names.append(cn)
        db.session.commit()
        form = AddBotanicalNameForm(cn=cn)
        form.name.data = 'Innagada davida'
        form.validate_name(form.name)
        form.name.data = 'Asclepias incarnata'
        with pytest.raises(ValidationError):
            form.validate_name(form.name)


class TestAddSectionForm:
    """Test custom methods of AddSectionForm."""
    def test_validate_name(self, db):
        section = Section(name='Polkadot',
                          common_name=CommonName(name='Foxglove'))
        db.session.add(section)
        db.session.commit()
        form = AddSectionForm(cn=section.common_name)
        form.name.data = 'Dalmatian'
        form.validate_name(form.name)
        form.name.data = 'Polkadot'
        with pytest.raises(ValidationError):
            form.validate_name(form.name)


class TestAddPacketFormWithDB:
    """Test custom methods of AddPacketForm."""
    def test_validate_sku(self, db):
        """Raise ValidationError if SKU already exists in db."""
        packet = Packet()
        cultivar = Cultivar()
        db.session.add_all([packet, cultivar])
        packet.sku = '8675309'
        cultivar.name = 'Jenny'
        packet.cultivar = cultivar
        db.session.commit()
        form = AddPacketForm(cultivar=cultivar)
        form.sku.data = '8675309'
        with pytest.raises(ValidationError):
            form.validate_sku(form.sku)


class TestAddCultivarFormWithDB:
    """Test custom methods of AddCultivarForm."""
    def test_validate_name(self, db):
        """Raise error if cultivar already exists.

        Cultivars are constrained to have a unique combination of name, common
            name, and section.
        """
        cv1 = Cultivar(name='Polkadot Petra')
        cv1.common_name = CommonName(name='Foxglove')
        cv1.common_name.index = Index(name='Perennial')
        cv1.section = Section(name='Polkadot')
        cv2 = Cultivar(name='Silky Gold')
        cv2.common_name = CommonName(name='Butterfly Weed')
        cv2.common_name.index = Index(name='Annual')
        cv3 = Cultivar(name='Tumbling Tom',
                       common_name=CommonName(name='Tomato'))
        db.session.add_all([cv1, cv2, cv3])
        db.session.commit()
        form1 = AddCultivarForm(cn=cv1.common_name)
        form1.name.data = 'Petra'
        form1.validate_name(form1.name)
        form2 = AddCultivarForm(cn=cv2.common_name)
        form2.name.data = 'Silky Gold'
        with pytest.raises(ValidationError):
            form2.validate_name(form2.name)
        form3 = AddCultivarForm(cn=cv3.common_name)
        form3.name.data = 'Tumbling Tom'
        with pytest.raises(ValidationError):
            form3.validate_name(form3.name)


class TestEditCultivarFormWithDB:
    """Test custom methods of EditCultivarForm."""
    def test_set_selects(self, db):
        """Set selects with values loaded from database."""
        bn = BotanicalName()
        cn = CommonName()
        idx = Index()
        db.session.add_all([bn, cn, idx])
        bn.name = 'Digitalis purpurea'
        cn.name = 'Foxglove'
        idx.name = 'Foxy'
        db.session.commit()
        form = EditCultivarForm()
        form.set_selects()
        assert (bn.id, bn.name) in form.botanical_name_id.choices
        assert (cn.id, cn.name) in form.common_name_id.choices


class TestEditPacketFormWithDB:
    """Test custom methods of EditPacketForm."""
    def test_validate_qty_val(self, db):
        """Raise a ValidationError if field.data can't be used as quantity."""
        field = mock.MagicMock()
        field.data = 'Forty-two'
        with pytest.raises(ValidationError):
            EditPacketForm.validate_qty_val(None, field)


class TestEditSectionFormWithDB:
    """Test custom methods of EditSectionForm."""
    def test_set_selects(self, db):
        """Populate common_name select with ids from database."""
        cn1 = CommonName(name='Foxglove')
        cn2 = CommonName(name='Butterfly Weed')
        cn3 = CommonName(name='Tomato')
        db.session.add_all([cn1, cn2, cn3])
        db.session.commit()
        form = EditSectionForm()
        form.set_selects()
        assert (cn1.id, cn1.name) in form.common_name_id.choices
        assert (cn2.id, cn2.name) in form.common_name_id.choices
        assert (cn3.id, cn3.name) in form.common_name_id.choices
