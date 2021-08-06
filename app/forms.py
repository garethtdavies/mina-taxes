from flask_wtf import FlaskForm
from wtforms import StringField, SelectField, SubmitField
from wtforms.validators import DataRequired, Length

class TaxForm(FlaskForm):
    address = StringField('address', validators=[DataRequired(), Length(min=55, max=55)])
    export = SelectField('export', choices=[('', 'Choose...'), ('koinly', 'Koinly')], validators=[DataRequired()])
    submit = SubmitField('Generate Export')