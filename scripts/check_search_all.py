"""Live regression: run inside the app container; uses configured model credits.

Exercises chat generation without saving test conversations or modifying indexes.
"""
import contextlib
import copy
import io
import sqlite3

from ktem.main import App
from ktem.pages.chat.common import STATE

app = App()
app.make()
with sqlite3.connect('file:/app/ktem_app_data/user_data/sql.db?mode=ro', uri=True) as db:
    uid = db.execute("select id from user where username='admin'").fetchone()[0]
    generator_id = db.execute(
        "select id from index__1__source where name = ?",
        ('220_2AZ-FE_Charging_-_Generator.pdf',),
    ).fetchone()[0]

question = ('for the rav4 2012, 2wd smaller engine, what is the '
            'alternatior mouting bolt torque spec')
for mode, selected in [('all', []), ('select', [generator_id])]:
    output = io.StringIO()
    with contextlib.redirect_stdout(output):
        for result in app.chat_page.chat_fn(
            'diagnostic-search-all', [(question, None)],
            app.default_settings.flatten(), 'simple', '', False, 'highlight',
            'en', copy.deepcopy(STATE), None, uid, '', mode, selected, uid,
        ):
            last = result
    for line in output.getvalue().splitlines():
        if line.startswith(('Mechanical search query:', 'Got 40', 'Got 1 cited')):
            print(line)
    answer, evidence = last[0][-1][1], last[1]
    print(mode, 'ANSWER:', answer, flush=True)
    assert '21' in answer and '52' in answer, 'Expected torque evidence absent'
    assert '220_2AZ-FE_Charging_-_Generator.pdf' in evidence, 'Expected source absent'
    assert '<mark' in evidence, 'Highlight marker absent'
    print(mode, 'PASS: answer, source and highlight', flush=True)
