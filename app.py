
# app.py
import io
import os
import datetime as dt
import pandas as pd
from flask import Flask, render_template_string, request, send_file, flash
from dotenv import load_dotenv
from scraper import fetch_queue_records, apply_filters

load_dotenv()
app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET", "change_me_in_prod")

FORM_HTML = """
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>Queue Report Export</title>
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <style>
    body { font-family: system-ui, -apple-system, Segoe UI, Roboto, Arial, sans-serif; margin: 2rem;}
    .form-group { margin-bottom: 1rem; }
    label { display:block; font-weight:600; margin-bottom: .5rem;}
    input, select { width: 100%; padding: .5rem; }
    button { padding: .6rem 1rem; }
    .note { color:#555; margin-top:1rem; font-size:.9rem; }
    .flash { color: #c00; margin-bottom: 1rem;}
  </style>
</head>
<body>
  {% with messages = get_flashed_messages() %}
    {% if messages %}
      {% for m in messages %}
        <div class="flash">{{ m }}</div>
      {% endfor %}
    {% endif %}
  {% endwith %}

  <h1>Export Queue Report</h1>
  /export
    <fieldset style="border:1px solid #ddd; padding:1rem; margin-bottom:1rem;">
      <legend>Authentication (optional)</legend>
      <div class="form-group">
        <label>Username (only if login is required)</label>
        <input name="username" placeholder="Your site username" />
      </div>
      <div class="form-group">
        <label>Password (only if login is required)</label>
        <input name="password" type="password" placeholder="Your site password" />
      </div>
      <p class="note">If you are already logged in (session cookies), you can leave these empty.</p>
    </fieldset>

    <div class="form-group">
      <label>Queue name <span style="color:#c00">*</span></label>
      <input name="queue_name" placeholder="e.g., Incidents, Requests" required />
    </div>
    <div class="form-group">
      <label>Category (optional, exact match)</label>
      <input name="category" placeholder="e.g., Hardware" />
    </div>
    <div class="form-group">
      <label>Subcategory (optional, exact match)</label>
      <input name="subcategory" placeholder="e.g., Laptop" />
    </div>
    <button type="submit">Fetch & Export Excel</button>
  </form>

  <p class="note">
    The app uses a headless browser (Playwright) to navigate your site, apply filters, and export results.
    No credentials are stored; they are used only if the site requires a fresh login.
  </p>
</body>
</html>
"""

@app.get("/")
def index():
    return render_template_string(FORM_HTML)

@app.post("/export")
def export():
    queue_name = request.form.get("queue_name", "").strip()
    category = request.form.get("category", "").strip() or None
    subcategory = request.form.get("subcategory", "").strip() or None
    username = request.form.get("username", "").strip() or None
    password = request.form.get("password", "").strip() or None

    if not queue_name:
        flash("Queue name is required.")
        return render_template_string(FORM_HTML)

    try:
        rows = fetch_queue_records(queue_name, username=username, password=password)
        filtered = apply_filters(rows, category, subcategory)

        if not filtered:
            flash("No records found for the given filters.")
            return render_template_string(FORM_HTML)

        # Build DataFrame
        df = pd.DataFrame(filtered)

        # Optional: reorder core columns first (Case ID, Category, Subcategory)
        core_cols = ["case_id", "category", "subcategory"]
        # Keep any other columns after core
        ordered_cols = [c for c in core_cols if c in df.columns] + [c for c in df.columns if c not in core_cols]
        df = df[ordered_cols]

        # Export to Excel in-memory
        output = io.BytesIO()
        ts = dt.datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"queue_report_{queue_name}_{ts}.xlsx"
        with pd.ExcelWriter(output, engine="openpyxl") as writer:
            df.to_excel(writer, index=False, sheet_name="Queue Report")
        output.seek(0)

        return send_file(
            output,
            mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            as_attachment=True,
            download_name=filename,
        )
    except Exception as ex:
        flash(f"Error: {ex}")
        return render_template_string(FORM_HTML)

if __name__ == "__main__":
    # In Codespaces, Flask will expose a forwarded port.
    app.run(host="0.0.0.0", port=5000, debug=True)
