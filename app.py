# -*- coding: utf-8 -*-
"""
Created on Mon Jan  9 16:30:12 2017
@author: Plazmer

Download CSV files from
https://www.rossvyaz.ru/activity/num_resurs/registerNum/
to directory .\ABCDEF\*.csv

"""

from bottle import run, template, request, get, post, default_app
import parser_sqlite

@get('/')
def index():
    if not parser_sqlite.check_data():
        parser_sqlite.create_tables()
        parser_sqlite.load_abcdef()

    return template('static/index.html')
    """<html><head><meta http-equiv="Content-Type" content="text/html; charset=windows-1251"></head>
    <body>
        <form method="POST" action="/send" enctype="multipart/form-data">
            <textarea name="html">insert html</textarea><br/>
                or<br/>
            <input type="file" name="file"><br/>
            <input type="submit" value="SEND">
        </form>
    </body></html>"""


@get('/reload')
def reload():
    parser_sqlite.create_tables()
    parser_sqlite.load_abcdef()
    return "reload ok"


@post('/send')
def send():
    html = request.forms.get('html','')

    if not html:
        f = request.files.get('file')
        if f:
            html = f.file.read().decode('utf8')

    calls = parser_sqlite.analyze_string(html)

    html = ''
    html += '<html><head><meta charset="utf-8"></head><body>'
    html += parser_sqlite.render_calls_svodny(calls)
    html += parser_sqlite.render_calls(calls)
    html += '</body></html>'
    return html


if __name__ == "__main__":
    run(host='0.0.0.0', port=20049, debug=True, reloader=True)
else:
    application = default_app()
