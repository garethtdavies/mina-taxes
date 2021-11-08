from flask_wtf import FlaskForm
from wtforms import StringField, SelectField, SubmitField, DateField
from wtforms.validators import DataRequired, Length
from wtforms.fields.html5 import DateField


class TaxForm(FlaskForm):
    """
    Class to define the front-end tax form
    """
    address = StringField('Address',
                          validators=[DataRequired(),
                                      Length(min=55, max=55)])
    export = SelectField('Export',
                         choices=[('', 'Choose...'), ('koinly', 'Koinly'),
                                  ('accointing', 'Accointing')],
                         validators=[DataRequired()])
    export_type = SelectField(
        'Export Type',
        choices=
        [('', 'Choose...'),
         ('transactions', 'Transactions (includes staking pool payouts)'),
         ('production',
          'Block Production (only if running a block producer - use coinbase receiver)'
          ), ('snarks', 'SNARK Work'), ('genesis', 'Genesis Grants')],
        validators=[DataRequired()])

    start_date = DateField('Start Date', format="%Y-%m-%d", validators=[DataRequired()])

    end_date = DateField('End Date', format="%Y-%m-%d", validators=[DataRequired()])

    submit = SubmitField('Generate Export')
