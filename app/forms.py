from flask_wtf import FlaskForm
from wtforms import StringField, SelectField, SubmitField
from wtforms.validators import DataRequired, Length


class TaxForm(FlaskForm):
    """
    Class to define the front-end tax form
    """
    address = StringField('address',
                          validators=[DataRequired(),
                                      Length(min=55, max=55)])
    export = SelectField('export',
                         choices=[('', 'Choose...'), ('koinly', 'Koinly'),
                                  ('accointing', 'Accointing - COMING SOON')],
                         validators=[DataRequired()])
    export_type = SelectField(
        'export_type',
        choices=[('', 'Choose...'),
                 ('transactions',
                  'Transactions (includes staking pool payouts)'),
                 ('production',
                  'Block Production (only if running a block producer - use coinbase receiver)'),
                 ('snarks', 'SNARK Work - COMING SOON'),
                 ('genesis', 'Genesis Grants')],
        validators=[DataRequired()])
    submit = SubmitField('Generate Export')
