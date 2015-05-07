"""WTForms for use on the site."""
from flask.ext.wtf import Form
from flask.ext.wtf.file import FileField, FileAllowed
from wtforms import(
        BooleanField,
        DecimalField,
        StringField,
        SubmitField,
        TextAreaField
)
from wtforms.validators import InputRequired, Length


class AddSeedForm(Form):
    """This form allows us to add a seed to the database.

    Fields:
        name -- Name of the seed as we want it depicted on the site.
        binomen -- Binomen (Genus species) for the seed.
        description -- Product description.
        variety -- Seed variety (Ex: Zinnia, Sunflower, Coleus)
        category -- Broad category for seed. 
                    (Ex: Vegetable, Annual Flower, Perennial Flower)
        price -- Price of the seed.
        is_active -- True/False: product is active.
        in_stock -- True/False: product is in stock.
        synonyms -- (optional) Other names for the seed.
        series -- (optional) Series seed is in, if applicable.
                  (Ex: Benary's Giant, Magic Fountains)
        thumbnail -- (optional) Thumbnail image for seed.
        submit -- Submit button.
    """
    name = StringField(
        'Name',
        validators=[InputRequired(), Length(max=64)]
        )
    binomen = StringField(
        'Binomen',
        validators=[InputRequired(), Length(max=129)]
        )
    description = TextAreaField(
        'Description',
        validators=[InputRequired(), Length(max=512)]
        )
    variety = StringField(
        'Variety',
        validators=[InputRequired(), Length(max=32)]
        )
    category = StringField(
        'Category',
        validators=[InputRequired(), Length(max=32)]
        )
    price = DecimalField(
        'Price',
        places=2,
        validators=[InputRequired()]
        )
    is_active = BooleanField('Active', default=True)
    in_stock = BooleanField('In Stock', default=True)
    synonyms = StringField('Synonyms')
    series = StringField(
        'Series',
        validators=[Length(max=32)]
        )
    thumbnail = FileField(
        'Thumbnail',
        validators=[FileAllowed(['jpg', 'jpe', 'jpeg', 'png', 'gif'],
                                'Thumbnail format: jpg, png, gif')]
        )
    submit = SubmitField('Add Seed')
