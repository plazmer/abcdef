# -*- coding: utf-8 -*-
"""
Created on Mon Jan  9 16:30:12 2017
@author: Plazmer

Download CSV files from
https://www.rossvyaz.ru/activity/num_resurs/registerNum/
to directory .\ABCDEF\*.csv

"""


import math
from lxml import html, etree
import os, sys
import csv
import sqlite3

alias={'date': 1, 'time': 2, 'tel': 4, 'zone': 6, 'len': 9, 'cost': 10}

fed_okrug = {}
with open('federal_okrug.txt', encoding='utf8') as f:
    for line in f:
        columns = line.strip().split("\t")
        if len(columns)>0:
            fed_okrug[columns[0]] = columns[1]

conn = sqlite3.connect('abcdef.db')
conn.row_factory = sqlite3.Row


def create_tables():
    c = conn.cursor()
    c.execute('''DROP TABLE IF EXISTS codes;''')
    c.execute('''CREATE TABLE codes (`from` int, `to` int, `reg` text, `city` text, PRIMARY KEY (`from`,`to`));''')
    conn.commit()


def check_data():
    c = conn.cursor()
    result = False
    try:
        c.execute('select count(*) from codes;')
        rez = c.fetchone()
        if rez[0]>0:
            result=True
    except:
        pass
    return result


def get_region(tel):

    if len(tel) == 12: #+7495...
        tel = tel[2:]

    if len(tel) == 11: #7495...
        tel = tel[1:]

    c = conn.cursor()
    c.execute("SELECT * FROM codes WHERE '%s'>=`from` AND '%s'<=`to`;"%(tel,tel))
    tmp = c.fetchone()
    row = dict()
    if tmp:
        row = dict(tmp)

    if tel[0] == '9':
        row['reg'] = 'Федеральные сотовые сети'

    if tel[0:3] == '800':
        row['reg'] = 'Бесплатный вызов 8-800'

    return row


def load_abcdef():
    tmp = conn.isolation_level

    conn.isolation_level = None
    c = conn.cursor()
    c.execute('begin;')
    c.execute('DELETE FROM codes;')
    c.execute('commit;')

    c.execute('VACUUM;')

    conn.isolation_level = tmp

    abcdef = os.path.join(os.getcwd(), 'abcdef')
    for fname in os.listdir(abcdef):
        print(abcdef, fname)
        fp = open(os.path.join(abcdef,fname),'r',encoding='utf8')
        fp.readline()
        csvr = csv.reader(fp,delimiter=';')
        for row in csvr:
            if len(row)<5:
                continue
            try:
                tmp = {}
                tmp['from'] = int(row[0].strip()+row[1].strip())
                tmp['to']   = int(row[0].strip() + row[2].strip())
                reg = row[5].strip().split('|')
                if len(reg)==3:
                    city = reg[0]
                    reg = reg[2]
                if len(reg)==2:
                    city = reg[0]
                    reg = reg[1]
                if len(reg)==1:
                    reg = reg[0]
                    city = ''
                tmp['reg'] = reg
                ins = (tmp['from'],tmp['to'],tmp['reg'],city)
                c.execute('INSERT INTO codes(`from`,`to`,`reg`,`city`) VALUES (?,?,?,?);',ins)
            except:
                print(row)
                print(sys.exc_info())
                print(sys.last_traceback)
                pass
        fp.close()
        conn.commit()


def analyze_files():
    in_file = os.getcwd()+'\\in\\'
    calls = []
    for fname in os.listdir(in_file):
        for call in analyze_string(in_file + fname):
            calls.append(call)
    return calls


def analyze_string(page):
    calls = []
    tree = html.fromstring(page)
    main_tables = tree.xpath('//body/table')
    print(len(main_tables))
    for main_table in main_tables:
        tables = main_table.xpath('.//table[@width=770 and @border=2]')
        numer_from = 'unknown'
        if len(tables) == 0:
            continue

        table_numer = main_table.xpath('.//table[@width=770 and @border=0]/tr/td[1]/text()')
        #print(etree.tostring(table_numer[0]))
        if len(table_numer) > 0:
            numer_from = table_numer[0].split(' ')[-1]



        for table in tables:
            tbody = table.xpath('tbody/tr')
            for tr in tbody:
                tds = tr.xpath('td')
                tmp = {}
                tmp['from'] = numer_from

                for a in alias.keys():
                    tmp[a] = tds[alias[a]].text
                if len(tmp.keys()) < len(alias.keys()):
                    print("no keys")
                    continue
                lenm,lens=tmp['len'].split(':')
                len_sec=int(lenm)*60+int(lens)
                if len_sec <= 3:
                    len_min=0
                else:
                    len_min=len_sec/60
                    if math.trunc(len_min) < len_min:
                        len_min = math.trunc(len_sec / 60) + 1
                    else:
                        len_min = math.trunc(len_sec / 60)
                tmp['minutes'] = int(len_min)
                reg = get_region(tmp['tel'])
                tmp['region'] = reg.get('reg')

                try:
                    tmp['cost'] = float(tmp['cost'].replace(',','.'))
                except:
                    tmp['cost'] = 0.0

                if tmp['minutes'] > 0:
                    tmp['per_minute'] = round(tmp['cost'] / int(tmp['minutes']), 4)
                else:
                    tmp['per_minute'] = 0

                tmp['okrug'] = fed_okrug.get(tmp['region'],'None')

                calls.append(tmp)

    return calls


def analyze_calls(calls):
    full_cost = 0
    full_minutes = 0
    svodny = {}
    for call in calls:
        if not svodny.get(call['region']):
            svodny[call['region']] = {'minutes':0, 'cost':0.0, 'region':call['region'], 'okrug':call['okrug']}
        svodny[call['region']]['minutes'] += int(call['minutes'])
        svodny[call['region']]['cost'] += float(call['cost'])
        full_cost += float(call['cost'])
        full_minutes += int(call['minutes'])

    for region in svodny.keys():
        if svodny[region]['minutes'] == 0:
            svodny[region]['per_minute'] = 0
        else:
            svodny[region]['per_minute'] = svodny[region]['cost'] / svodny[region]['minutes']

    svodny['ITOGO'] = {'minutes': 0, 'cost': 0.0, 'region': 'ITOGO','okrug':'я'}
    svodny['ITOGO']['per_minute'] = 0
    svodny['ITOGO']['cost'] = full_cost
    svodny['ITOGO']['minutes'] = full_minutes
    return svodny


def render_calls_svodny(calls):
    svodny = analyze_calls(calls)
    html = ''
    headers = ['okrug','region','per_minute','per_minute_NDS20','minutes','cost','costNDS20']
    html += '<h3>Сводный отчет</h3>'
    html += '<table border="2"><tr>'
    for h in headers:
        html += '<th>%s</th>' % h

    html += '</tr>\n'

    regions = list(svodny.keys())
    
    tmp = []
    for k in svodny.keys():
        tmp.append(svodny[k])

    tmp = sorted(tmp, key=lambda s: s.get('okrug','_')+s.get('region',''))
    for row in tmp:
        call = row

        html += '<tr>'
        for h in headers:
            elem = call.get(h, '&nbsp;')
            if h in ['cost', 'per_minute']:
                elem = str(round(elem,2)).replace('.',',')

            if h=='per_minute_NDS20':
                tmp = call.get('per_minute')
                tmp = round(tmp * 1.2,2)
                elem = str(tmp).replace('.',',')

            if h=='costNDS20':
                tmp = call.get('cost')
                tmp = round(tmp * 1.2,2)
                elem = str(tmp).replace('.',',')

            if h != 'region':
                html += '<td align="right">%s</td>' % elem
            else:
                html += '<td>%s</td>' % elem

        html += '</tr>\n'

    html += '</table>'
    return html


def render_calls(calls):
    html = ''
    headers = ['date','time','from','tel','zone','region','minutes','cost']
    html += '<h3>Исходные данные</h3>'
    html += '<table border="2"><tr>'
    for h in headers:
        html += '<th>%s</th>' % h

    html += '</tr>\n'

    for call in calls:
        html += '<tr>'
        for h in headers:
            elem = call.get(h, '&nbsp;')
            if h in ['cost', 'per_minute']:
                elem = str(elem).replace('.',',')
            html += '<td>%s</td>' % elem
        html += '</tr>\n'

    html += '</table>'
    return html

if __name__ == "__main__":
    #print(len('73452468073'))
    #print(len('+73452468073'))
    calls = analyze_string(open('r:/1.html','r',encoding='utf8').read())


