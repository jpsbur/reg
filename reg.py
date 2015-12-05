import cymysql
from flask import Flask, url_for, render_template, request, make_response
import cgi
import hashlib
import time
import smtplib
import random
import string
from email.mime.text import MIMEText
reg = Flask (__name__)

conn = False
cur = False

@reg.route ('/')
def index ():
  conn = cymysql.connect (host = '127.0.0.1', user = 'reg', passwd = 'password', db = 'reg', charset = 'utf8')
  cur = conn.cursor ()
  where = ''
  host = request.headers.getlist("X-Forwarded-Host")[0]
  if host == 'archimedes-contest.org':
    where = ' where type=2' # archimedes -> 2
  elif host == 'spbtc.ru':
    where = ' where type=1 or type=2' # archimedes -> 2, mmcup -> 1
  elif host == 'acm.math.spbu.ru':
    where = ' where type=0 or type=1'
  cur.execute ('select id, name, state, date from events' + where + ' order by id desc')
  events = []
  for r in cur.fetchall ():
    events.append (r)
  content = ''
  content += '<table>\n'
  content += '<tr><th>' + lang['index_event'] + '</th><th>' + lang['index_date'] + '</th><th>' + lang['index_state'] + '</th></tr>\n'
  for e in events:
    event_id = e[0]
    event_name = e[1]
    state = e[2]
    event_date = e[3]
    if state == 0:
      state_str = lang['index_state_pending']
    elif state == 1:
      state_str = '<a href="' + '/reg/register' + str (event_id) + '">' + lang['index_state_registration'] + '</a>'
    elif state == 2:
      state_str = lang['index_state_closed']
    else:
      state_str = lang['index_state_error']
    event_link = '<a href="' + '/reg/event' + str (event_id) + '">' + cgi.escape (event_name) + '</a>'
    content += '<tr><td style="width: 60%;">' + event_link + '</td><td>' + event_date + '</td><td>' + state_str + '</td></tr>\n'
  content += '</table>\n'
  cur.close ()
  conn.close ()
  return render_template ('template.html', title = lang['index_title'], content = content)

@reg.route ('/login')
def login ():
  pass

@reg.route ('/event<int:event_id>')
def event (event_id):
  event_id = int (event_id)
  conn = cymysql.connect (host = '127.0.0.1', user = 'reg', passwd = 'password', db = 'reg', charset = 'utf8')
  cur = conn.cursor ()
  cur.execute ('select id, name, state, flags, users, description from events where id=' + str (event_id))
  e = False
  for r in cur.fetchall ():
    e = r
  if e == False:
    cur.close ()
    conn.close ()
    return render_template ('template.html', title = 'Error', content = 'No such event')
  event_name = e[1]
  event_state = e[2]
  event_flags = e[3]
  event_users = e[4]
  event_description = e[5]
  title = lang['event_registration_for'] + ' ' + event_name
  content = ''
  content += '<div>' + event_description + '</div>\n'
  cur.execute ('select id, name, state from teams where event_id=' + str (event_id))
  teams = []
  for t in cur.fetchall ():
    teams.append (t)
  if len (teams) > 0:
    content += '<h2>' + lang['event_registered_teams'] + '</h2>\n'
    content += '<div><table>\n'
    content += '<tr><th>' + lang['index_team'] + ' </th><th> </th><th> </th><th>' + lang['index_state'] + ' </th></tr>\n'
    for t in teams:
      team_id = t[0]
      team_name = t[1]
      state = t[2]
      if state == 0:
        state_str = lang['team_state_pending']
      elif state == 1:
        state_str = lang['team_state_registered']
      elif state == 2:
        state_str = lang['team_state_rejected']
      else:
        state_str = lang['team_state_error']
      cur.execute ('select last_name, state, grade, school_name, group_name, first_name from users where team_id = %s', [team_id])
      users = cur.fetchall ()
      comment = ''
      is_school = True
      is_c = True
      is_spbsu = True
      is_first = True
      for u in users:
        if u[0] in ['-', 'X', 'XXX', 'YYY', 'ZZZ']:
          continue
        if u[2] < 1 or u[2] > 11:
          is_school = False
        if u[3][0:5] != 'СПбГУ':
          is_spbsu = False
        if (u[2] < 1 or u[2] > 11) and (u[3][0:5] != 'СПбГУ'):
          is_c = False
        if u[3][0:5] != 'СПбГУ' or u[4] // 100 != 1:
          is_first = False
      if is_school:
        comment = ' (шк)'
      if is_first:
        comment = ' (1к)'
      if not is_c:
        comment = ' (вк)'
      if event_users > 1:
        users_text = ', '.join ('<span class="user_' + cgi.escape (str (u[1])) + '">' + cgi.escape (u[0]) + '</span>' for u in users)
        content += '<tr>' + \
          '<td><b>' + cgi.escape (team_name) + '</b> </td>' + \
          '<td>' + users_text + ' </td>' + \
          '<td>' + cgi.escape (comment) + '</td>' + \
          '<td>' + state_str + ' </td></tr>\n'
      else:
        users_text = '<span class="user_' + cgi.escape (str (u[1])) + '">' + cgi.escape (u[5]) + ' ' + cgi.escape (u[0]) + '</span>'
        content += '<tr>' + \
          '<td colspan="2">' + users_text + ' </td>' + \
          '<td>' + cgi.escape (comment) + '</td>' + \
          '<td>' + state_str + ' </td></tr>\n'
    content += '</table></div>\n'
    content += '<div>' + lang['event_count_teams'] + ': <b>' + str (len (teams)) + '</b> </div>\n'
  else:
    content += '<h2>' + lang['event_no_teams'] + '</h2>\n'
  cur.close ()
  conn.close ()
  if event_state == 1:
    content += '<div><a href="/reg/register' + str (event_id) + '">' + lang['index_link_register'] + '</a></div>\n'
  else:
    content += '<div>' + lang['event_registration_closed'] + '</div>\n'
  return render_template ('template.html', title = title, content = content)

def display_form (event_id, event_flags, event_users, team, users, form_errors):
  content = ''
  content += '<h2>' + lang['event_register_team'] + '</h2>\n'
  if form_errors != '':
    content += '<div>' + lang['event_form_errors'] + ': ' + form_errors + '</div>'
  content += '<form action="/reg/register' + str (event_id) + '" method="POST">\n'
  content += '<input type="hidden" name="event_id" value="' + str (event_id) + '" />\n'
  content += '<table>\n'
  content += '<tr><th colspan="2">' + lang['event_team'] + '</th></tr>\n'
  if event_flags & 1 == 1:
    content += '<tr><td>' + lang['event_form_team_name'] + '</td><td><input type="text" name="team_name" value="' + cgi.escape (team['name']) + '"></td></tr>\n'
  if event_flags & 2 == 2:
    content += '<tr><td>' + lang['event_form_team_email'] + '</td><td><input type="text" name="team_email" value="' + cgi.escape (team['email']) + '"></td></tr>\n'
  for u in range (event_users):
    content += '<tr><th colspan="2">' + lang['event_user'] + ' ' + str (u + 1) + '</th></tr>\n'
    #content += '<tr><td colspan="2"><i>' + lang['event_user_help'] + '</i></td></tr>\n'
    for f in user_fields:
      f_id = 'user' + str (u) + '_' + f
      old_value = ''
      try:
        old_value = default_value[f]
      except:
        pass
      try:
        old_value = str (users[u][f])
      except:
        pass
      content += '<tr><td>' + lang['event_form_' + f] + \
        '</td><td><input type="text" name="' + f_id + '" value="' + cgi.escape (old_value) + '" list="' + f + '" /></td></tr>\n'
  for f in default_values:
    content += '<datalist id="' + f + '">\n'
    for v in default_values[f]:
      content += '<option value="' + cgi.escape (v) + '">' + cgi.escape (v) + '</option>\n'
    content += '</datalist>\n'
  content += '<tr><td colspan="2"><input type="submit" value="' + lang['event_form_submit'] + '" /></td></tr>\n'
  content += '</table>\n'
  content += '</form>\n'
  return content

@reg.route ('/register<int:event_id>', methods = ['GET', 'POST'])
def register (event_id):
  event_id = int (event_id)
  conn = cymysql.connect (host = '127.0.0.1', user = 'reg', passwd = 'password', db = 'reg', charset = 'utf8')
  cur = conn.cursor ()
  cur.execute ('select id, name, state, flags, users from events where id=' + str (event_id))
  e = False
  for r in cur.fetchall ():
    e = r
  if e == False:
    cur.close ()
    conn.close ()
    return render_template ('template.html', title = 'Error', content = 'No such event')
  show_long = False
  try:
    if request.args.get ('show_long', '') == 'true':
      show_long = True
  except:
    pass
  event_name = e[1]
  event_state = e[2]
  event_flags = e[3]
  event_users = e[4]
  title = lang['event_registration_for'] + ' ' + event_name
  content = ''
  need_form = 0
  form_errors = ''
  team = {'name': '', 'email': ''}
  users = []
  if request.method == 'POST':
    need_form = 1
    if event_flags & 1 == 1:
      try:
        team['name'] = request.form['team_name']
      except:
        team['name'] = ''
      if team['name'] == '' or len (team['name']) > 50:
        form_errors += lang['form_error_name']
        need_form = 0
    if event_flags & 2 == 2:
      try:
        team['email'] = request.form['team_email']
      except:
        team['email'] = ''
      if team['email'] == '' or len (team['email']) > 50:
        form_errors += lang['form_error_email']
        need_form = 0

    for u in range (event_users):
      user = {}
      for f in user_fields:
        f_id = 'user' + str (u) + '_' + f
        try:
          user[f] = request.form[f_id]
        except:
          user[f] = ''
      #cur.execute ('select ' + ', '.join (user_fields) + ' from users where email=%s and current = 1', [user['email']])
      #sug_users = cur.fetchall ()
      #if len (sug_users) > 0:
      #  for xuser in sug_users:
      #    #content += str (xuser) + '\n'
      #    i = 0
      #    for f in user_fields:
      #      #content += '== (' + user[f] + ') == ' + str (xuser[i]) + ' =='
      #      if user[f] == '':
      #        #content += 'okay' + str (xuser[i])
      #        user[f] = str (xuser[i])
      #      i += 1
      ##content += '!!!!' + str (user) + '!!!!'
      err = []
      for f in user_fields:
        if user[f] == '' or len (user[f]) > 50:
          err.append (f)
      if len (err) > 0:
        form_errors += lang['form_error_user'] + ' ' + str (u + 1) + ' (' + \
          ', '.join ([lang['event_form_' + x + '_lc'] for x in err]) + '); '
        need_form = 0
      users.append (user)

  if event_state == 0:
    content += '<h2>' + lang['event_registration_closed'] + '</h2>\n'
  elif event_state == 1:
    if need_form == 1:
      cur.execute ('insert into teams (name, email, event_id, state) values (%s, %s, %s, %s)', [team['name'], team['email'], event_id, 0])
      cur.execute ('select last_insert_id()')
      team_id = cur.fetchall ()[0][0]
      s = smtplib.SMTP ('localhost')
      for u in range (event_users):
        hashcode = hashlib.md5 (('$29vs4' + str (event_id) + str (team_id) + str (u) + str (time.time ())).encode ()).hexdigest ()
        cur.execute ('insert into users (team_id, state, hashcode, ' + ', '.join (user_fields) + ') ' + \
          'values (%s, %s, %s, ' + ', '.join (['%s' for x in user_fields]) + ')', \
          [team_id, 0, hashcode] + [users[u][x] for x in user_fields])
        message = MIMEText (lang['email_text1'] + '\n' + \
          'https://acm.math.spbu.ru/reg/confirm?hash=' + hashcode + '\n' + \
          lang['email_text2'] + '\n' + \
          lang['email_contest'] + ' ' + event_name + ' ' + \
          lang['email_you'] + ' ' + users[u]['first_name'] + ' ' + users[u]['last_name'] + ' ' + \
          lang['email_your_team'] + ' ' + team['name'] + '\n')
        message['Subject'] = lang['email_subject']
        message['From'] = 'SPb SU Registration System <reg@acm.math.spbu.ru>'
        message['To'] = users[u]['email']
        try:
          s.send_message (message)
        except:
          need_form = 0
          form_errors += ' ' + lang['form_error_email']
          break
      s.quit ()
      if need_form == 1:
        content += '<h2>' + lang['event_successfully_registered'] + '</h2>'
        conn.commit ()
      else:
        conn.rollback ()
    if need_form == 0:
      content += display_form (event_id, event_flags, event_users, team, users, form_errors)
  cur.close ()
  conn.close ()
  content += '<div><a href="/reg/event' + str (event_id) + '">' + lang['event_registered_teams'] + '</a></div>\n'
  return render_template ('template.html', title = title, content = content)

@reg.route ('/confirm')
def confirm ():
  try:
    hashcode = request.args.get ('hash', '')
  except:
    hashcode = ''
  conn = cymysql.connect (host = '127.0.0.1', user = 'reg', passwd = 'password', db = 'reg', charset = 'utf8')
  cur = conn.cursor ()
  cur.execute ('select ' + ', '.join (['id'] + user_fields) + ' from users where hashcode=%s', [hashcode])
  u = False
  for r in cur.fetchall ():
    u = r
  if u == False:
    cur.close ()
    conn.close ()
    return render_template ('template.html', title = 'Error', content = 'No such hashcode')
  user = {}
  i = 1
  for f in user_fields:
    user[f] = u[i]
    i = i + 1
  title = lang['event_confirmation_success']
  content = '<div>' + lang['event_confirmation_success'] + '</div>\n'
  content += '<table>\n'
  for f in user_fields:
    content += '<tr><td>' + lang['event_form_' + f] + '</td><td>' + str (user[f]) + '</td></tr>\n'
  content += '</table>\n'
  content += '<div><a href="/reg/useredit?hash=' + cgi.escape (hashcode) + '">Редактировать информацию</a></div>\n'
  cur.execute ('update users set state=1 where id=%s', [str (u[0])])
  conn.commit ()
  cur.close ()
  conn.close ()
  return render_template ('template.html', title = title, content = content)

@reg.route ('/useredit', methods = ['GET', 'POST'])
def useredit ():
  try:
    hashcode = request.args.get ('hash', '')
  except:
    hashcode = ''
  conn = cymysql.connect (host = '127.0.0.1', user = 'reg', passwd = 'password', db = 'reg', charset = 'utf8')
  cur = conn.cursor ()
  cur.execute ('select ' + ', '.join (['id'] + user_fields) + ' from users where hashcode=%s', [hashcode])
  u = False
  for r in cur.fetchall ():
    u = r
  if u == False:
    cur.close ()
    conn.close ()
    return render_template ('template.html', title = 'Error', content = 'No such hashcode')
  user = {}
  i = 1
  for f in user_fields:
    user[f] = u[i]
    i = i + 1
  need_form = 0
  form_errors = ''
  title = lang['event_edit_user']
  content = ''
  if request.method == 'POST':
    need_form = 1
    for f in user_fields:
      try:
        user[f] = request.form[f]
      except:
        pass
      if user[f] == '' or len (user[f]) > 50:
        form_errors = lang['form_error_user']
        need_form = 0

  if need_form == 0:
    content += '<form action="/reg/useredit?hash=' + cgi.escape (hashcode) + '" method="POST">\n'
    content += '<table>\n'
    for f in user_fields:
      content += '<tr><td>' + lang['event_form_' + f] + \
        '</td><td><input type="text" name="' + f + '" value="' + cgi.escape (str (user[f])) + '" list="' + f + '" /></td></tr>\n'
    content += '</table>\n'
    for f in default_values:
      content += '<datalist id="' + f + '">\n'
      for v in default_values[f]:
        content += '<option value="' + cgi.escape (v) + '">' + cgi.escape (v) + '</option>\n'
      content += '</datalist>\n'
    content += '<tr><td colspan="2"><input type="submit" value="' + lang['event_form_edit'] + '" /></td></tr>\n'
  else:
    cur.execute ('update users set ' + \
      ', '.join ([x + ' = %s' for x in user_fields]) + ' where hashcode=%s', \
      [str (user[x]) for x in user_fields] + [hashcode])
    content += '<h2>' + lang['event_edit_user_success'] + '</h2>'
  conn.commit ()
  cur.close ()
  conn.close ()
  return render_template ('template.html', title = title, content = content)

@reg.route ('/resend')
def resend ():
  try:
    hashcode = request.args.get ('hash', '')
  except:
    hashcode = ''
  conn = cymysql.connect (host = '127.0.0.1', user = 'reg', passwd = 'password', db = 'reg', charset = 'utf8')
  cur = conn.cursor ()
  cur.execute ('select ' + ', '.join (['id', 'team_id'] + user_fields) + ' from users where hashcode=%s', [hashcode])
  u = cur.fetchone ()
  i = 2
  user = {}
  for f in user_fields:
    user[f] = u[i]
    i = i + 1
  user['id'] = u[0]
  user['team_id'] = u[1]
  cur.execute ('select name, event_id from teams where id=%s', [user['team_id']])
  t = cur.fetchone ()
  team = {}
  team['name'] = t[0]
  team['event_id'] = t[1]
  cur.execute ('select name from events where id=%s', [team['event_id']])
  e = cur.fetchone ()
  event_name = e[0]
  s = smtplib.SMTP ('localhost')
  message = MIMEText (lang['email_text1'] + '\n' + \
    'https://acm.math.spbu.ru/reg/confirm?hash=' + hashcode + '\n' + \
    lang['email_text2'] + '\n' + \
    lang['email_contest'] + ' ' + event_name + ' ' + \
    lang['email_you'] + ' ' + user['first_name'] + ' ' + user['last_name'] + ' ' + \
    lang['email_your_team'] + ' ' + team['name'] + '\n')
  message['Subject'] = lang['email_subject']
  message['From'] = 'SPb SU Registration System <reg@acm.math.spbu.ru>'
  message['To'] = user['email']
  s.send_message (message)
  return render_template ('template.html', title = 'Resent ok', content = 'Resent ok')

def export_team (t, res_type):
  global conn, cur
  team_id = t[0]
  team_name = t[1]
  state = t[2]
  login = t[3]
  password = t[4]
  password2 = t[5]
  room = t[6]
  team_res = t[7]
  if state == 0:
    state_str = lang['team_state_pending']
  elif state == 1:
    state_str = lang['team_state_registered']
  elif state == 2:
    state_str = lang['team_state_rejected']
  else:
    state_str = lang['team_state_error']
  cur.execute ('select last_name, state, grade, school_name, group_name, first_name, patronymic, email, phone from users where team_id = %s', [team_id])
  users = cur.fetchall ()
  comment = ''
  is_school = True
  for u in users:
    if u[2] < 1 or u[2] > 11:
      is_school = False
  is_spbsu = True
  for u in users:
    if u[3][0:5] != 'СПбГУ':
      is_spbsu = False
  is_first = True
  for u in users:
    if u[3][0:5] != 'СПбГУ' or u[4] // 100 != 1:
      is_first = False
  if is_school:
    comment = ' (шк)'
  if is_first:
    comment = ' (1к)'
  if not (is_school or is_spbsu):
    comment = ' (вк)'
  users_text = ', '.join (cgi.escape (u[0]) for u in users)
  if res_type == 'html':
    users_text = ', '.join ( \
      '<span class="user_' + cgi.escape (str (u[1])) + '">' + \
      cgi.escape (u[5] + ' ' + u[0] + ' (' + str (u[3]) + ', ' + str (u[4]) + ')') + '</span>' \
      for u in users)
    return '<tr><td>' + str (team_id) + ' </td>' + \
      '<td><b>' + cgi.escape (team_name) + '</b> </td>' + \
      '<td>' + users_text + ' </td>' + \
      '<td>' + cgi.escape (comment) + '</td>' + \
      '<td>' + state_str + ' </td></tr>\n'
  elif res_type == 'tex-password':
    users_text = ', '.join (cgi.escape (u[0]) for u in users)
    if len(users) == 1:
      team_text = cgi.escape(users[0][5] + ' ' + users[0][0] + ', ' + str(users[0][2]))
    else:
      team_text = cgi.escape(team_name + ' (' + users_text + ')' + comment)
    return '  \\noindent\n' + \
      '  \\begin{tabular}{p{4cm}p{11cm}}\n' + \
      '  \\hline\n' + \
      '  \\bf{Team:} & ' + team_text + ' \\\\\n' + \
      '  \\bf{Room:} & ' + room + ' \\\\\n' + \
      '  \\bf{OS login:} & \\texttt{studentmm} \\\\\n' + \
      '  \\bf{OS password:} & \\texttt{Vfnvt[vfnvt[} \\\\\n' + \
      '  \\bf{Testsys login:} & \\texttt{' + login + '} \\\\\n' + \
      '  \\bf{Password:} & \\texttt{' + password + '} \\\\\n' + \
      '  \\end{tabular}\n' + \
      '  \\vskip 1cm\n'
  elif res_type == 'tex-password2':
    users_text = ', '.join (cgi.escape (u[0]) for u in users)
    if len(users) == 1:
      team_text = cgi.escape(users[0][5] + ' ' + users[0][0] + ', ' + str(users[0][2]))
    else:
      team_text = cgi.escape(team_name + ' (' + users_text + ')' + comment)
    return '  \\noindent\n' + \
      '  \\begin{tabular}{p{4cm}p{11cm}}\n' + \
      '  \\hline\n' + \
      '  \\bf{Team:} & ' + team_text + ' \\\\\n' + \
      '  \\bf{Room:} & ' + room + ' \\\\\n' + \
      '  \\bf{OS login:} & \\texttt{studentmm} \\\\\n' + \
      '  \\bf{OS password:} & \\texttt{Vfnvt[vfnvt[} \\\\\n' + \
      '  \\bf{Testsys login:} & \\texttt{' + login + '} \\\\\n' + \
      '  \\bf{Password:} & \\texttt{' + password2 + '} \\\\\n' + \
      '  \\end{tabular}\n' + \
      '  \\vskip 1cm\n'
  elif res_type == 'tex-reg':
    if len(users) == 1:
      return users[0][5] + ' ' + users[0][0] + ' & ' + room + ' & ' + login + ' \\\\\n  \\hline\n'
    return '  ' + cgi.escape (team_name + ' (' + users_text + ')' + comment) + ' & ' + room + ' & ' + login + ' \\\\\n  \\hline\n'
  elif res_type == 'tex-diploma':
    return '{\\Huge \\bf присуждается команде &lt;&lt;' + cgi.escape (team_name) + '&gt;&gt; в~составе}\n\n\\vskip 3em\n\n' + \
      ''.join ('{\\huge \\bf ' + cgi.escape (u[5]) + ' ' + cgi.escape (u[0]) + ' (' + cgi.escape (u[3]) + ')}\n\n' for u in users)
  elif res_type == 'tex-diploma2':
    return \
      '\\newpage\n' + \
      '\\begin{center}\n' + \
      '{~}\n\n' + \
      '\\vskip 9em\n\n' + \
      '{\\Huge \\bf VIII}\n\n' + \
      '\\vskip 1em\n\n' + \
      '{\\Huge \\bf Кубок}\n\n' + \
      '\\vskip 1em\n\n' + \
      '{\\Huge \\bf школьников}\n\n' + \
      '\\vskip 1em\n\n' + \
      '{\\Huge \\bf по программированию \\vphantom{С}}\n\n' + \
      '\\vskip 3em\n\n' + \
      '\\resizebox{7cm}{!}{\\Huge \\bf ДИПЛОМ}\n\n' + \
      '\\vskip 3em\n\n' + \
      '{\\Huge \\bf ' + cgi.escape(team_res) + '}\n\n' + \
      '\\vskip 3em\n\n' + \
      '{\\huge \\bf награждается}\n\n' + \
      '\\vskip 3em\n\n' + \
      '{\huge \\bf ' + cgi.escape(users[0][5]) + ' ' + cgi.escape(users[0][0]) + ' (' + cgi.escape(users[0][3]) + ', ' + str(users[0][2]) + ')' + '}\n\n' + \
      '\\end{center}\n' + \
      '\\newpage\n\n'
  elif res_type == 'cfg':
    if len(users) == 1:
      return '  teamEH ({}, "{}", "{}", "{}", 1, umon)\n'.format(login, cgi.escape(users[0][5] + ' ' + users[0][0] + ', ' + str(users[0][2])), password, room)
    return '  teamEH ({}, "{}", "{}", "{}", 1, umon)\n'.format(login, cgi.escape (team_name + ' (' + users_text + ')' + comment), password, room)
  elif res_type == 'cfg2':
    if len(users) == 1:
      return '  teamEH ({}, "{}", "{}", "{}", 1, umon)\n'.format(login, cgi.escape(users[0][5] + ' ' + users[0][0] + ', ' + str(users[0][2])), password2, room)
    return '  teamEH ({}, "{}", "{}", "{}", 1, umon)\n'.format(login, cgi.escape (team_name + ' (' + users_text + ')' + comment), password2, room)
  elif res_type == 'email':
    return cgi.escape (team_name) + ': ' + ', '.join (cgi.escape (u[7]) for u in users) + '\n'
  elif res_type == 'txt':
    return ''.join ('' + cgi.escape (u[0]) + ' ' + cgi.escape (u[5]) + ' ' + cgi.escape (u[6]) + '\n' for u in users)
  elif res_type == 'txt2':
    return cgi.escape (team_name) + ' (' + ', '.join ('' + cgi.escape (u[0]) for u in users) + ')\n'
  elif res_type == 'txt3':
    return cgi.escape (team_name) + '\n' + ''.join ('' + cgi.escape (u[0]) + ' ' + cgi.escape (u[5]) + ' ' + cgi.escape (u[6]) + ', ' + cgi.escape (u[3]) + ', ' + str (u[4]) + '\n' for u in users)
  elif res_type == 'phone':
    return cgi.escape (team_name) + ': ' + ', '.join (cgi.escape (u[5]) + ' ' + cgi.escape (u[0]) + ' (' + cgi.escape (u[8]) + ')' for u in users) + '\n'
  return 'error'

@reg.route ('/export<int:event_id>')
def export (event_id):
  global conn, cur
  event_id = int (event_id)
  try:
    res_type = request.args.get ('type', '')
  except:
    res_type = 'html'
  try:
    h = request.args.get ('hash', '')
  except:
    h = ''
  if h != 'password':
    return render_template ('template.html', title = 'Error', content = 'Wrong hash code')
  conn = cymysql.connect (host = '127.0.0.1', user = 'reg', passwd = 'password', db = 'reg', charset = 'utf8')
  cur = conn.cursor ()
  cur.execute ('select id, name, state, flags, users from events where id=' + str (event_id)) 
  e = False
  for r in cur.fetchall ():
    e = r
  if e == False:
    cur.close ()
    conn.close ()
    return render_template ('template.html', title = 'Error', content = 'No such event')
  event_name = e[1]
  event_state = e[2]
  event_flags = e[3]
  event_users = e[4]
  title = lang['event_registration_for'] + ' ' + event_name
  content = ''

  if res_type == 'html':
    cur.execute ('select id, name, state, login, password, password2, room, result from teams where event_id=' + str (event_id) + ' order by room, login')
    teams = []
    for t in cur.fetchall ():
      teams.append (t)
    if len (teams) > 0:
      content += '<h2>' + lang['event_registered_teams'] + '</h2>\n'
      content += '<div><table>\n'
      content += '<tr><th># </th><th>Team </th><th> </th><th> </th><th>State </th></tr>\n'
      for t in teams:
        content += export_team (t, res_type)
      content += '</table></div>\n'
      content += '<div>' + lang['event_count_teams'] + ': <b>' + str (len (teams)) + '</b> </div>\n'
    else:
      content += '<h2>' + lang['event_no_teams'] + '</h2>\n'
  elif res_type == 'tex' or res_type == 'tex-password' or res_type == 'tex-password2' or res_type == 'tex-diploma':
    cur.execute ('select id, name, state, login, password, password2, room, result from teams where event_id=' + str (event_id) + ' order by room, login')
    teams = []
    for t in cur.fetchall ():
      teams.append (t)
    content += '<pre>\n'
    content += \
      '\\documentclass[12pt,a4paper,oneside]{article}\n' + \
      '\\usepackage[T2A]{fontenc}\n' + \
      '\\usepackage[utf8]{inputenc}\n' + \
      '\\usepackage[english,russian]{babel}\n' + \
      '\\usepackage[margin=0.5in]{geometry}\n' + \
      '\\pagestyle{empty}\n' + \
      '\\begin{document}\n'
    for t in teams:
      content += export_team (t, res_type)
    content += '\\end{document}\n'
    content += '</pre>\n'
  elif res_type == 'tex-diploma2':
    cur.execute ('select id, name, state, login, password, password2, room, result from teams where event_id=' + str (event_id) + ' and result != "" order by result')
    teams = []
    for t in cur.fetchall ():
      teams.append (t)
    content += '<pre>\n'
    content += \
      '\\documentclass[a4paper,12pt]{article}\n\n' + \
      '\\usepackage[russian]{babel}\n' + \
      '\\usepackage[utf8]{inputenc}\n' + \
      '\\usepackage[T2A]{fontenc}\n' + \
      '\\usepackage{fullpage}\n' + \
      '\\usepackage{graphicx}\n\n' + \
      '\\pagestyle{empty}\n\n' + \
      '\\hoffset=-10mm\n' + \
      '\\voffset=-15mm\n' + \
      '\\textheight=245mm\n' + \
      '\\textwidth=175mm\n' + \
      '\\begin{document}\n'
    for t in teams:
      content += export_team (t, res_type)
    content += '\\end{document}\n'
    content += '</pre>\n'
  elif res_type == 'tex-reg':
    cur.execute ('select id, name, state, login, password, password2, room, result from teams where event_id=' + str (event_id) + ' order by room, login')
    teams = []
    for t in cur.fetchall ():
      teams.append (t)
    content += '<pre>\n'
    content += \
      '\\documentclass[12pt,a4paper,oneside]{article}\n' + \
      '\\usepackage[T2A]{fontenc}\n' + \
      '\\usepackage[utf8]{inputenc}\n' + \
      '\\usepackage[english,russian]{babel}\n' + \
      '\\usepackage[margin=0.5in]{geometry}\n' + \
      '\\pagestyle{empty}\n' + \
      '\\begin{document}\n' + \
      '\\begin{tabular}{|p{10cm}|p{2cm}|p{2cm}|}\n' + \
      '  \\hline\n' + \
      '  \\bf{Team} & \\bf{Room} & \\bf{Login} \\\\\n' + \
      '  \\hline\n'
    for t in teams:
      content += export_team (t, res_type)
    content += '\\end{tabular}\n'
    content += '\\end{document}\n'
    content += '</pre>\n'
  elif res_type == 'cfg' or res_type == 'cfg2':
    cur.execute ('select id, name, state, login, password, password2, room, result from teams where event_id=' + str (event_id) + ' order by room, login')
    teams = []
    for t in cur.fetchall ():
      teams.append (t)
    content += '<pre>\n'
    content += 'teams += [\n'
    for t in teams:
      content += export_team (t, res_type)
    content += ']\n'
    content += '</pre>\n'
  elif res_type == 'txt' or res_type == 'txt2' or res_type == 'txt3' or res_type == 'email' or res_type == 'phone':
    cur.execute ('select id, name, state, login, password, password2, room, result from teams where event_id=' + str (event_id) + ' order by login')
    teams = []
    for t in cur.fetchall ():
      teams.append (t)
    content += '<pre>\n'
    for t in teams:
      content += export_team (t, res_type)
    content += '</pre>\n'
  cur.close ()
  conn.close ()
  return render_template ('template.html', title = title, content = content)

@reg.route ('/users')
def users ():
  global conn, cur
  try:
    res_type = request.args.get ('type', 'html')
  except:
    res_type = 'html'
  try:
    h = request.args.get ('hash', '')
  except:
    h = ''
  if h != 'password':
    return render_template ('template.html', title = 'Error', content = 'Wrong hash code')
  conn = cymysql.connect (host = '127.0.0.1', user = 'reg', passwd = 'password', db = 'reg', charset = 'utf8')
  cur = conn.cursor ()
  content = ''
  cur.execute ('select ' + ', '.join (['id'] + user_fields) + ' from users order by last_name, first_name')
  title = 'Users'
  users = []
  for t in cur.fetchall ():
    user = {}
    i = 1
    for f in user_fields:
      user[f] = t[i]
      i = i + 1
    users.append (user)
  
  if res_type == 'html':
    content += '<div><table>\n'
    content += '<tr>' + ''.join ('<th>' + x + '</th>' for x in user_fields) + '</tr>\n'
    last = ''
    cnt = 0
    for u in users:
      current = u['last_name'] + ' ' + u['first_name'] + ' ' + u['patronymic']
      if current == last:
        u['last_name'] = '=='
        u['first_name'] = '=='
        u['patronymic'] = '=='
      else:
        cnt = cnt + 1
      last = current
      content += '<tr>' + ''.join ('<td>' + cgi.escape (str (u[x])) + '</td>' for x in user_fields) + '</tr>\n'
    content += '</table></div>\n'
    content += '<div>' + 'Всего' + ': <b>' + str (len (users)) + '</b>, различных: <b>' + str (cnt) + '</b> </div>\n'
  cur.close ()
  conn.close ()
  return render_template ('template.html', title = title, content = content)

def gen_pass (seed):
  random.seed (seed)
  return ''.join (random.choice (string.ascii_lowercase) for x in range (10))

@reg.route ('/password<int:event_id>')
def password (event_id):
  global conn, cur
  event_id = int (event_id);
  try:
    action = request.args.get ('action', '')
  except:
    action = 'show'
  try:
    h = request.args.get ('hash', '')
  except:
    h = ''
  if h != 'password':
    return render_template ('template.html', title = 'Error', content = 'Wrong hash code')
  conn = cymysql.connect (host = '127.0.0.1', user = 'reg', passwd = 'password', db = 'reg', charset = 'utf8')
  cur = conn.cursor ()
  content = ''
  if action == 'set':
    cur.execute ('select id from teams where event_id=' + str (event_id))
    temp = cur.fetchall ()
    i = 0
    rooms = ['2406'] * 6 + ['2408'] * 5 + ['2410'] * 8 + ['2444'] * 10 + ['2446'] * 11 + ['???'] * 100
    ids = [i for i in range(len(temp))]
    random.seed()
    random.shuffle(ids)
    for t in temp:
      team_id = t[0]
      p1 = gen_pass (team_id * 3239 + 1713)
      p2 = gen_pass (team_id * 1239 + 3713)
      cur.execute ('update teams set password=%s, password2=%s, login=%s, room=%s where id=%s', [p1, p2, '{:02d}'.format(ids[i] + 1), rooms[ids[i]], team_id])
      i += 1
    conn.commit ()
    
  cur.execute ('select id, name, password, password2, login, room from teams where event_id=%s order by login', str(event_id))
  title = 'Teams'
  temp = cur.fetchall ()
  content += '<table>\n'
  content += '<tr><th>ID</th><th>Name</th><th>Password 1</th><th>Password 2</th><th>Login</th><th>Room</th></tr>\n'
  for t in temp:
    cur.execute('select first_name, last_name, school_name, grade from users where team_id=%s', t[0])
    users = ','.join ([x[0] + ' ' + x[1] + ' (' + x[2] + ', ' + str(x[3]) + ')' for x in cur.fetchall ()])
    content += '<tr>'
    for i in range (6):
      if i == 1:
        content += '<td>' + users + '</td>'
      elif str(t[i]) == '':
        content += '<td>(not set)</td>'
      else:
        content += '<td>' + str (t[i]) + '</td>'
    content += '</tr>\n'
  content += '</table>\n'
  cur.close ()
  conn.close ()
  return render_template ('template.html', title = title, content = content)

lang_en = { \
  'index_event': 'Event', \
  'index_state': 'State', \
  'index_state_pending': 'Pending', \
  'index_state_registration': 'Registration', \
  'index_state_closed': 'Closed!', \
  'index_state_error': 'Error', \
  'index_title': 'List of Events', \
  'event_registration_for': 'Registration for', \
  'event_registered_teams': 'Registered Teams', \
  'event_team' : 'Team', \
  'event_user' : 'Person', \
  'event_form_team_name' : 'Team name', \
  'event_form_team_email' : 'Team e-mail', \
  'event_form_last_name' : 'Last name', \
  'event_form_first_name' : 'First name', \
  'event_form_patronymic': 'Patronymic', \
  'event_form_school_name': 'University or school', \
  'event_form_grade': 'Grade (high school students)', \
  'event_form_group_name': 'Group (university students)', \
  'event_form_email': 'E-mail', \
  'event_form_phone': 'Phone', \
  'event_form_vkid': 'VK id', \
  'team_state_pending': 'Pending', \
  'team_state_registered': 'Regstered', \
  'team_state_rejected': 'Rejected', \
  'team_state_error': 'Error', \
  'event_no_teams': 'No teams registered', \
  'event_registration_closed': 'Registration closed', \
  'event_register_team': 'Register your team', \
  'event_successfully_registered': 'Successfully registered!', \
  'event_form_errors': 'You have errors in form', \
  'event_form_submit': 'Register', \
  'form_error_name': 'Incorrect team name' \
}

lang_ru = { \
  'index_event': 'Событие', \
  'index_state': 'Состояние', \
  'index_team': 'Команда', \
  'index_date': 'Дата', \
  'index_state_pending': 'Ожидание', \
  'index_state_registration': 'Идёт регистрация', \
  'index_state_closed': 'Регистрация закрыта', \
  'index_state_error': 'Ошибка', \
  'index_link_register': 'Зарегистрироваться', \
  'index_title': 'Список событий', \
  'event_registration_for': 'Регистрация на соревнование: ', \
  'event_registered_teams': 'Зарегистрированные команды', \
  'event_team' : 'Команда', \
  'event_user' : 'Участник', \
  'event_user_help' : 'Если участник ранее уже регистрировался, вы можете ввести только e-mail', \
  'event_form_team_name' : 'Название команды', \
  'event_form_team_email' : 'E-mail команды', \
  'event_form_last_name' : 'Фамилия', \
  'event_form_first_name' : 'Имя', \
  'event_form_patronymic': 'Отчество', \
  'event_form_school_name': 'Университет или школа', \
  'event_form_grade': 'Класс (для школьников)', \
  'event_form_group_name': 'Группа (для студентов)', \
  'event_form_email': 'E-mail', \
  'event_form_phone': 'Телефон', \
  'event_form_vkid': 'ID ВКонтакте', \
  'event_form_last_name_lc' : 'фамилия', \
  'event_form_first_name_lc' : 'имя', \
  'event_form_patronymic_lc': 'отчество', \
  'event_form_school_name_lc': 'университет или школа', \
  'event_form_grade_lc': 'класс', \
  'event_form_group_name_lc': 'группа', \
  'event_form_email_lc': 'e-mail', \
  'event_form_phone_lc': 'телефон', \
  'event_form_vkid_lc': 'ID ВКонтакте', \
  'team_state_pending': 'Ожидание', \
  'team_state_registered': 'Зарегистрирована', \
  'team_state_rejected': 'Отклонена', \
  'team_state_error': 'Ошибка', \
  'event_no_teams': 'Участников пока нет', \
  'event_registration_closed': 'Регистрация закрыта', \
  'event_register_team': 'Зарегистрируйте команду', \
  'event_successfully_registered': 'Команда зарегистрирована!', \
  'event_form_errors': 'При заполнении формы допущены ошибки', \
  'event_form_submit': 'Зарегистрировать', \
  'form_error_name': 'некорректное название команды', \
  'email_subject': 'Регистрация на соревнование: подтвердите адрес почты', \
  'email_text1': 'Ваш адрес указан при регистрации на соревнование. Пожалуйста, перейдите по следующей ссылке для подтверждения.', \
  'email_text2': 'С наилучшими пожеланиями, система регистрации', \
  'email_contest': 'Вы зарегистрированы на', \
  'email_you': 'под именем', \
  'email_your_team': 'в составе команды', \
  'event_confirmation_success': 'Участие подтверждено', \
  'form_error_user': 'некорректное описание участника', \
  'form_error_email': 'Не удалось отправить письмо для подтверждения e-mail', \
  'event_edit_user': 'Редактировать информацию об участнике', \
  'event_form_edit': 'Редактировать', \
  'event_edit_user_success': 'Информация сохранена', \
  'event_count_teams': 'Всего команд', \
  #'': '', \
  '': '' \
}

lang = lang_ru

user_fields = ['last_name', 'first_name', 'patronymic', 'school_name', 'grade', 'group_name', 'email', 'phone', 'vkid']
default_value = { \
  'school_name': 'СПбГУ, матмех', \
  'grade': 'не школьник' \
}
default_values = { \
  'school_name': ['СПбГУ, матмех', 'СПбГУ, физфак', 'СПбГУ, ПМ-ПУ', 'СПб АУ', 'У ИТМО', 'ФМЛ 30', 'ФМЛ 239', 'ФТШ', 'ЮМШ'], \
  'grade': ['1', '2', '3', '4', '5', '6', '7', '8', '9', '10', '11', 'не школьник'], \
  'group_name': ['нет (я школьник)'] \
}

if __name__ == '__main__':
  reg.debug = True
  reg.run (host = '127.0.0.1', port = 5000)
