from flask import render_template, make_response
from app import app
from app.forms import TaxForm
from app.exporters.koinly import Koinly
from app.exporters.accointing import Accointing
from datetime import datetime
import pytz


@app.route('/', methods=['GET', 'POST'])
@app.route('/index', methods=['GET', 'POST'])
def index():
    form = TaxForm()

    if form.validate_on_submit():
        address = form.address.data
        export = form.export.data
        export_type = form.export_type.data
        start_date = datetime(form.start_date.data.year,
                              form.start_date.data.month,
                              form.start_date.data.day,
                              tzinfo=pytz.utc)
        end_date = datetime(form.end_date.data.year,
                            form.end_date.data.month,
                            form.end_date.data.day,
                            tzinfo=pytz.utc)

        start_date = start_date.replace().isoformat()
        end_date = end_date.replace().isoformat()

        if export == "accointing":
            exporter = Accointing()
        else:
            exporter = Koinly()
        output = make_response(
            exporter.download_export(address, export_type, start_date,
                                     end_date))
        output.headers[
            "Content-Disposition"] = f"attachment; filename={address}-{export_type}.csv"
        output.headers["Content-type"] = "text/csv"
        return output

    return render_template('home.html', title='Home', form=form)