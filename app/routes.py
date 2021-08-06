from flask import render_template, make_response
from app import app
from app.forms import TaxForm
from app.exporters.koinly import Koinly


@app.route('/', methods=['GET', 'POST'])
@app.route('/index', methods=['GET', 'POST'])
def index():
    form = TaxForm()

    if form.validate_on_submit():
        address = form.address.data
        #export = form.export.data

        # TODO instantiate based on the export type
        exporter = Koinly()
        output = make_response(exporter.download_export(address))
        output.headers[
            "Content-Disposition"] = f"attachment; filename={address}.csv"
        output.headers["Content-type"] = "text/csv"
        return output

    return render_template('home.html', title='Home', form=form)