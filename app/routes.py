from flask import render_template, make_response
from app import app
from app.forms import TaxForm
from app.exporters.koinly import Koinly
from app.exporters.accointing import Accointing


@app.route('/', methods=['GET', 'POST'])
@app.route('/index', methods=['GET', 'POST'])
def index():
    form = TaxForm()

    if form.validate_on_submit():
        address = form.address.data
        export = form.export.data
        export_type = form.export_type.data

        if export == "accointing":
            exporter = Accointing()
        else:
            exporter = Koinly()
        output = make_response(exporter.download_export(address, export_type))
        output.headers[
            "Content-Disposition"] = f"attachment; filename={address}-{export_type}.csv"
        output.headers["Content-type"] = "text/csv"
        return output

    return render_template('home.html', title='Home', form=form)