import os, io, re, time, calendar, gzip, hmac, logging, secrets, random, json
from logging.handlers import RotatingFileHandler
from datetime import date, datetime, timedelta
from functools import wraps
from flask import (Flask, render_template, request, redirect, url_for,
                   flash, send_file, abort, jsonify, session, g, has_request_context)
from werkzeug.exceptions import HTTPException
from flask_sqlalchemy import SQLAlchemy
from flask_login import (LoginManager, UserMixin, login_user, logout_user,
                         login_required, current_user)
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy import inspect, text, event, func, Index
from sqlalchemy.sql import expression
from sqlalchemy.schema import CreateTable
from urllib.parse import urlparse
from sqlalchemy.engine import Engine
from sqlalchemy.orm import joinedload
from sqlalchemy.exc import SQLAlchemyError, OperationalError, IntegrityError
from i18n import HI, JS_KEYS, MONTHS_HI
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.environ.get('DATA_DIR', BASE_DIR)          # database, logs, backups and secret key live here
os.makedirs(os.path.join(DATA_DIR, 'logs'), exist_ok=True)


def load_secret_key():
    """Use SECRET_KEY from the environment (needed when several servers share one database);
    otherwise create a random key once and keep it in DATA_DIR/secret.key."""
    key = os.environ.get('SECRET_KEY')
    if key:
        return key
    path = os.path.join(DATA_DIR, 'secret.key')
    if not os.path.exists(path):
        try:
            with open(path, 'x') as fh:
                fh.write(secrets.token_hex(32))
            os.chmod(path, 0o600)
        except (FileExistsError, OSError):
            pass
    with open(path) as fh:
        return fh.read().strip()


DB_URL = os.environ.get('DATABASE_URL', 'sqlite:///' + os.path.join(DATA_DIR, 'attendance.db').replace('\\', '/'))
HTTPS_ONLY = os.environ.get('HTTPS', '0') == '1'
IS_SQLITE = DB_URL.startswith('sqlite')

app = Flask(__name__)
app.config.update(
    SECRET_KEY=load_secret_key(),
    SQLALCHEMY_DATABASE_URI=DB_URL,
    SQLALCHEMY_ENGINE_OPTIONS=({'connect_args': {'timeout': 30}} if IS_SQLITE else
                               {'pool_pre_ping': True, 'pool_recycle': 1800,
                                'pool_size': int(os.environ.get('DB_POOL', 20)),
                                'max_overflow': int(os.environ.get('DB_OVERFLOW', 40)), 'pool_timeout': 30}),
    TEMPLATES_AUTO_RELOAD=False,
    SEND_FILE_MAX_AGE_DEFAULT=timedelta(days=30),          # static files are versioned (?v=...) so this is safe
    SESSION_COOKIE_HTTPONLY=True, SESSION_COOKIE_SAMESITE='Lax', SESSION_COOKIE_SECURE=HTTPS_ONLY,
    REMEMBER_COOKIE_HTTPONLY=True, REMEMBER_COOKIE_SAMESITE='Lax', REMEMBER_COOKIE_SECURE=HTTPS_ONLY,
    REMEMBER_COOKIE_DURATION=timedelta(days=7),
    PERMANENT_SESSION_LIFETIME=timedelta(hours=int(os.environ.get('SESSION_HOURS', 10))),
    MAX_CONTENT_LENGTH=2 * 1024 * 1024,
    CSRF_ENABLED=True,
)
if os.environ.get('BEHIND_PROXY', '0') == '1':           # running behind nginx / a load balancer
    from werkzeug.middleware.proxy_fix import ProxyFix
    app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1)

# ---- logging (rotating file, never grows without limit) ----
_handler = RotatingFileHandler(os.path.join(DATA_DIR, 'logs', 'app.log'), maxBytes=5_000_000, backupCount=5, encoding='utf-8')
_handler.setFormatter(logging.Formatter('%(asctime)s %(levelname)s %(message)s'))
app.logger.addHandler(_handler)
app.logger.setLevel(logging.INFO)

# ---- SQLite tuning: many readers + a writer at the same time without "database is locked" ----
@event.listens_for(Engine, 'connect')
def _sqlite_pragmas(dbapi_conn, _):
    if IS_SQLITE:
        cur = dbapi_conn.cursor()
        cur.execute('PRAGMA journal_mode=WAL')
        cur.execute('PRAGMA synchronous=NORMAL')
        cur.execute('PRAGMA busy_timeout=30000')
        cur.execute('PRAGMA temp_store=MEMORY')
        cur.execute('PRAGMA cache_size=-32000')
        cur.execute('PRAGMA mmap_size=268435456')          # let the OS cache serve reads
        cur.execute('PRAGMA journal_size_limit=67108864')
        cur.close()


db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

COMPANY = 'Lion Enviro'                      # + the project name, e.g. "Lion Enviro Lucknow"
APP_VERSION = '4.8'
_FIRST_PID = [1]                              # id of the first (default) project, set at start-up


def _default_project_id():
    """project_id of a new row when the code did not say: the project being worked on, else the first one."""
    p = g.get('_project') if has_request_context() else None
    return p.id if p is not None else _FIRST_PID[0]


DEFAULT_LANG = os.environ.get('APP_LANG', 'en')   # 'en' = English, 'hi' = Hindi
SHIFTS = ['Day', 'Night']
WORK_TYPES = ['Door to Door', 'Commercial', 'Sweeping']
STATUSES = ['Present', 'Absent', 'Leave', 'Half Day', 'Weekly Off']
CODES = {'P': 'Present', 'A': 'Absent', 'L': 'Leave', 'H': 'Half Day', 'W': 'Weekly Off'}
MODULES = [('zones', 'Zone'), ('wards', 'Ward'), ('holidays', 'Holiday'), ('vehicles', 'Vehicle'), ('routes', 'Route'), ('trackers', 'Tracker'), ('employees', 'Employee'),
           ('attendance', 'Attendance Sheet'), ('reports', 'Reports')]
ACTIONS = ['view', 'add', 'edit', 'delete', 'export']
EXPORT_MODULES = ('attendance', 'reports')


# ---------------------------------------------------------------- models
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    full_name = db.Column(db.String(100), nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), default='user')  # super_admin / user
    is_active_user = db.Column(db.Boolean, default=True)
    all_zones = db.Column(db.Boolean, default=True)
    all_wards = db.Column(db.Boolean, default=True)
    all_works = db.Column(db.Boolean, default=True)
    all_shifts = db.Column(db.Boolean, default=True)
    backdate_days = db.Column(db.Integer, nullable=True)  # None = unlimited
    must_change = db.Column(db.Boolean, default=False)   # force password change at next login
    perms = db.relationship('Permission', backref='user', cascade='all, delete-orphan', lazy='selectin')
    scopes = db.relationship('UserScope', backref='user', cascade='all, delete-orphan', lazy='selectin')
    project_links = db.relationship('UserProject', backref='user', cascade='all, delete-orphan')   # loaded only when needed

    @property
    def is_active(self):
        return self.is_active_user

    @property
    def project_ids(self):
        return {l.project_id for l in self.project_links}

    @property
    def is_super(self):
        return self.role == 'super_admin'

    def can(self, module, action='view'):
        if self.is_super:
            return True
        for p in self.perms:
            if p.module == module:
                return bool(getattr(p, 'can_' + action, False))
        return False

    def allowed(self, kind, universe):
        """kind = wards / works / shifts ; universe = list of string values"""
        if self.is_super or getattr(self, 'all_' + kind):
            return list(universe)
        vals = {s.value for s in self.scopes if s.kind == kind}
        return [x for x in universe if x in vals]

    def scope_text(self, kind):
        if self.is_super or getattr(self, 'all_' + kind):
            return tr('All')
        vals = [s.value for s in self.scopes if s.kind == kind]
        if not vals:
            return tr('None')
        if kind == 'zones':
            names = [z.name for z in Zone.query.filter(Zone.id.in_([int(v) for v in vals])).order_by(Zone.name)]
            return ', '.join(names) or tr('None')
        return '%d %s' % (len(vals), tr('wards')) if kind == 'wards' else ', '.join(tr(v) for v in vals)


class Permission(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    module = db.Column(db.String(30), nullable=False)
    can_view = db.Column(db.Boolean, default=False)
    can_add = db.Column(db.Boolean, default=False)
    can_edit = db.Column(db.Boolean, default=False)
    can_delete = db.Column(db.Boolean, default=False)
    can_export = db.Column(db.Boolean, default=False)


class UserScope(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    kind = db.Column(db.String(10), nullable=False)   # wards / works / shifts
    value = db.Column(db.String(60), nullable=False)


class Project(db.Model):
    """A site / city the company works in (Lucknow, Barabanki, Kashi ...). Every zone - and so every ward, employee,
    vehicle, route, tracker and attendance record - belongs to exactly one project."""
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(60), unique=True, nullable=False)       # Lucknow
    code_prefix = db.Column(db.String(8), default='LE')                # employee codes: LEL00001
    active = db.Column(db.Boolean, default=True)

    @property
    def company(self):
        return '%s %s' % (COMPANY, self.name)


class UserProject(db.Model):
    __table_args__ = (db.UniqueConstraint('user_id', 'project_id'),)
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    project_id = db.Column(db.Integer, db.ForeignKey('project.id'), nullable=False)


class Holiday(db.Model):
    __table_args__ = (db.UniqueConstraint('project_id', 'hdate', name='uq_holiday_proj_date'),)
    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey('project.id'), index=True, default=_default_project_id)
    hdate = db.Column(db.Date, nullable=False, index=True)
    name = db.Column(db.String(100), nullable=False)


class Zone(db.Model):
    __table_args__ = (db.UniqueConstraint('project_id', 'name'),)
    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey('project.id'), index=True, default=_default_project_id)
    name = db.Column(db.String(100), nullable=False)
    wards = db.relationship('Ward', backref='zone')
    project = db.relationship('Project')


class Ward(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    zone_id = db.Column(db.Integer, db.ForeignKey('zone.id'), nullable=False)
    employees = db.relationship('Employee', backref='ward')


class Employee(db.Model):
    __table_args__ = (Index('ix_emp_ward_active', 'ward_id', 'active'), Index('ix_emp_zone', 'zone_id'),
                      Index('ix_emp_name', 'name'), Index('ix_emp_vehicle', 'vehicle_id'), Index('ix_emp_route', 'route_id'), Index('ix_emp_tracker', 'tracker_id'))
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(20), unique=True, nullable=False)
    name = db.Column(db.String(100), nullable=False)
    father_name = db.Column(db.String(100))
    mobile = db.Column(db.String(15))
    designation = db.Column(db.String(60))
    zone_id = db.Column(db.Integer, db.ForeignKey('zone.id'), nullable=False)
    ward_id = db.Column(db.Integer, db.ForeignKey('ward.id'), nullable=False)
    default_shift = db.Column(db.String(10), default='Day')
    default_work = db.Column(db.String(30), default='Door to Door')
    joining_date = db.Column(db.Date)
    active = db.Column(db.Boolean, default=True)
    vehicle_id = db.Column(db.Integer, db.ForeignKey('vehicle.id'), nullable=True)   # only for Driver / Helper
    route_id = db.Column(db.Integer, db.ForeignKey('route.id'), nullable=True)       # only for Driver / Helper
    tracker_id = db.Column(db.Integer, db.ForeignKey('tracker.id'), nullable=True)   # only for Trolleyman
    zone = db.relationship('Zone')


class Vehicle(db.Model):
    __table_args__ = (Index('ix_veh_zone', 'zone_id'),)
    id = db.Column(db.Integer, primary_key=True)
    vehicle_no = db.Column(db.String(20), nullable=False)          # as shown, e.g. UP32 AB 1234
    vkey = db.Column(db.String(20), unique=True, nullable=False)   # UP32AB1234 - makes duplicates impossible
    vehicle_type = db.Column(db.String(40))
    zone_id = db.Column(db.Integer, db.ForeignKey('zone.id'), nullable=False)
    ward_id = db.Column(db.Integer, db.ForeignKey('ward.id'), nullable=True)
    active = db.Column(db.Boolean, default=True)
    zone = db.relationship('Zone')
    ward = db.relationship('Ward')
    crew = db.relationship('Employee', backref='vehicle')          # drivers and helpers on this vehicle


class Route(db.Model):
    __table_args__ = (Index('ix_route_zone', 'zone_id'), db.UniqueConstraint('project_id', 'rkey'))
    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey('project.id'), index=True, default=_default_project_id)
    route_no = db.Column(db.String(20), nullable=False)            # the Route ID as shown, e.g. R-12
    rkey = db.Column(db.String(20), nullable=False)                # R12 - makes duplicates impossible inside a project
    route_name = db.Column(db.String(80))                          # optional: area / description of the route
    zone_id = db.Column(db.Integer, db.ForeignKey('zone.id'), nullable=False)
    ward_id = db.Column(db.Integer, db.ForeignKey('ward.id'), nullable=True)
    active = db.Column(db.Boolean, default=True)
    zone = db.relationship('Zone')
    ward = db.relationship('Ward')
    crew = db.relationship('Employee', backref='route')            # drivers and helpers working this route


class Tracker(db.Model):
    __table_args__ = (Index('ix_tracker_zone', 'zone_id'),)
    id = db.Column(db.Integer, primary_key=True)
    tracker_no = db.Column(db.String(30), nullable=False)          # the Tracker ID as shown
    tkey = db.Column(db.String(30), unique=True, nullable=False)   # upper-case, no spaces - makes duplicates impossible
    zone_id = db.Column(db.Integer, db.ForeignKey('zone.id'), nullable=False)
    active = db.Column(db.Boolean, default=True)
    zone = db.relationship('Zone')
    crew = db.relationship('Employee', backref='tracker')          # trolleymen using this tracker


class Attendance(db.Model):
    __table_args__ = (db.UniqueConstraint('att_date', 'employee_id', 'shift'),
                      Index('ix_att_ward_date_shift', 'ward_id', 'att_date', 'shift'),
                      Index('ix_att_emp_date', 'employee_id', 'att_date'))
    id = db.Column(db.Integer, primary_key=True)
    att_date = db.Column(db.Date, nullable=False, index=True)
    employee_id = db.Column(db.Integer, db.ForeignKey('employee.id'), nullable=False)
    ward_id = db.Column(db.Integer, db.ForeignKey('ward.id'), nullable=False)
    shift = db.Column(db.String(10), nullable=False)
    status = db.Column(db.String(15), nullable=False)
    work_type = db.Column(db.String(30))
    location = db.Column(db.String(150))
    in_time = db.Column(db.String(8))
    remark = db.Column(db.String(200))
    marked_by = db.Column(db.String(50))
    employee = db.relationship('Employee')
    ward = db.relationship('Ward')


def cur_lang():
    return session.get('lang', DEFAULT_LANG)


def tr(text):
    """Translate an English UI string into the active language."""
    return HI.get(text, text) if cur_lang() == 'hi' else text


DAYS_HI = ['सोम', 'मंगल', 'बुध', 'गुरु', 'शुक्र', 'शनि', 'रवि']


def day_label(d):
    return DAYS_HI[d.weekday()] if cur_lang() == 'hi' else calendar.day_abbr[d.weekday()]


def month_label(m):
    return MONTHS_HI[m - 1] if cur_lang() == 'hi' else calendar.month_name[m]


app.jinja_env.globals['_'] = tr
app.jinja_env.globals['dow'] = lambda d: day_label(d)


class AuditLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    ts = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    username = db.Column(db.String(50), index=True)
    ip = db.Column(db.String(45))
    action = db.Column(db.String(40), index=True)
    detail = db.Column(db.String(300))
    project_id = db.Column(db.Integer, index=True)       # project the user was working in (None = before login)


class LoginAttempt(db.Model):
    __table_args__ = (Index('ix_la_ip_ts', 'ip', 'ts'), Index('ix_la_user_ts', 'username', 'ts'))
    id = db.Column(db.Integer, primary_key=True)
    ip = db.Column(db.String(45))
    username = db.Column(db.String(50))
    ts = db.Column(db.DateTime, default=datetime.utcnow)


def audit(action, detail='', username=None, commit=True):
    """Write one line to the audit trail (who did what, from where)."""
    try:
        who = username or (current_user.username if current_user and current_user.is_authenticated else '-')
        proj = current_project() if (current_user and current_user.is_authenticated) else None
        db.session.add(AuditLog(username=who, ip=(request.remote_addr or '-')[:45], action=action, detail=(detail or '')[:300],
                                project_id=proj.id if proj else None))
        if commit:
            db.session.commit()
    except SQLAlchemyError:
        db.session.rollback()
        app.logger.exception('audit failed')


@login_manager.user_loader
def load_user(uid):
    u = db.session.get(User, int(uid))
    return u if u is not None and u.is_active_user else None     # a disabled user is logged out at once


_JS_T = {}


def js_texts():
    lang = cur_lang()
    if lang not in _JS_T:
        _JS_T[lang] = {k: tr(k) for k in JS_KEYS}
    return _JS_T[lang]


@app.context_processor
def inject():
    proj = current_project() if current_user.is_authenticated else None
    return dict(COMPANY=company_name(), PROJECT=proj, MY_PROJECTS=accessible_projects() if proj else [],
                SHIFTS=SHIFTS, WORK_TYPES=WORK_TYPES, STATUSES=STATUSES,
                MODULES=MODULES, ACTIONS=ACTIONS, EXPORT_MODULES=EXPORT_MODULES, today=date.today(),
                lang=cur_lang(), APP_VERSION=APP_VERSION, js_t=js_texts())


# ---------------------------------------------------------------- access helpers
def perm(module, action='view'):
    def deco(fn):
        @wraps(fn)
        @login_required
        def wrapper(*a, **kw):
            if not current_user.can(module, action):
                flash(tr('You do not have access to this page.'), 'error')
                return redirect(url_for('dashboard'))
            return fn(*a, **kw)
        return wrapper
    return deco


def super_only(fn):
    @wraps(fn)
    @login_required
    def wrapper(*a, **kw):
        if not current_user.is_super:
            abort(403)
        return fn(*a, **kw)
    return wrapper


def _cached(key, fn):
    """Compute once per request (these lookups are used many times while rendering one page)."""
    c = g.__dict__.setdefault('_cache', {})
    if key not in c:
        c[key] = fn()
    return c[key]


def accessible_projects(u=None):
    """Projects the user may open: a Super Admin every active one, a normal user the ones given to him."""
    if u is None:
        return _cached('projects', lambda: _accessible_projects(current_user))      # one query per request
    return _accessible_projects(u)


def _accessible_projects(u):
    q = Project.query.filter(Project.active.is_(True))
    if not u.is_super:
        q = q.filter(Project.id.in_(db.session.query(UserProject.project_id).filter(UserProject.user_id == u.id)))
    return q.order_by(Project.name).all()


def current_project():
    """The project the logged-in user is working in (chosen at login, changeable from the top bar)."""
    if not current_user.is_authenticated:
        return None

    def pick():
        projs = accessible_projects()
        want = session.get('project_id')
        p = next((x for x in projs if x.id == want), None) or (projs[0] if projs else None)
        if p is not None and want != p.id:
            session['project_id'] = p.id
        return p
    p = _cached('project', pick)
    g._project = p
    return p


def cur_pid():
    p = current_project()
    return p.id if p else 0


def company_name():
    p = current_project() if (has_request_context() and current_user.is_authenticated) else None
    return p.company if p else COMPANY


def holiday_q():
    return Holiday.query.filter(Holiday.project_id == cur_pid())


def my_zones():
    return _cached('zones', _my_zones)


def _my_zones():
    allz = Zone.query.filter(Zone.project_id == cur_pid()).order_by(Zone.name).all()
    ok = set(current_user.allowed('zones', [str(z.id) for z in allz]))
    return [z for z in allz if str(z.id) in ok]


def zones_limited():
    return True        # always: the data of the other projects must never show, not even to a Super Admin


def zones_user_limited():
    return not (current_user.is_super or current_user.all_zones)


def my_wards():
    return _cached('wards', _my_wards)


def _my_wards():
    """Wards the user may see: only inside allowed zones, and only the allowed wards."""
    allw = Ward.query.options(joinedload(Ward.zone)).join(Zone).filter(Zone.project_id == cur_pid()).order_by(Zone.name, Ward.name).all()
    ok_z = {z.id for z in my_zones()}
    ok_w = set(current_user.allowed('wards', [str(w.id) for w in allw]))
    return [w for w in allw if w.zone_id in ok_z and str(w.id) in ok_w]


def geo_limited():
    return True        # always filter by the wards of the current project


def my_works():
    return _cached('works', lambda: current_user.allowed('works', WORK_TYPES))


def my_shifts():
    return _cached('shifts', lambda: current_user.allowed('shifts', SHIFTS))


def scope_emp(q):
    if geo_limited():
        q = q.filter(Employee.ward_id.in_([w.id for w in my_wards()] or [0]))
    if zones_limited():
        q = q.filter(Employee.zone_id.in_([z.id for z in my_zones()] or [0]))
    if not (current_user.is_super or current_user.all_works):
        q = q.filter(Employee.default_work.in_(my_works() or ['-']))
    return q


def scope_att(q):
    if geo_limited():
        q = q.filter(Attendance.ward_id.in_([w.id for w in my_wards()] or [0]))
    if not (current_user.is_super or current_user.all_works):
        q = q.filter(Attendance.work_type.in_(my_works() or ['-']))
    if not (current_user.is_super or current_user.all_shifts):
        q = q.filter(Attendance.shift.in_(my_shifts() or ['-']))
    return q


def locked_before():
    """Attendance before this date cannot be edited by the user (None = no limit)."""
    if current_user.is_super or current_user.backdate_days is None:
        return None
    return date.today() - timedelta(days=current_user.backdate_days)


def valid_password(p):
    return len(p or '') >= 8 and any(c.isalpha() for c in p) and any(c.isdigit() for c in p)


PW_RULE = 'Password must be at least 8 characters and contain letters and numbers.'


def parse_date(s, default=None):
    try:
        return datetime.strptime(s, '%Y-%m-%d').date()
    except (TypeError, ValueError):
        return default


def next_code():
    p = current_project()
    prefix = (p.code_prefix if p and p.code_prefix else 'LE')
    n = Employee.query.join(Zone, Employee.zone_id == Zone.id).filter(Zone.project_id == cur_pid()).count() + 1
    while True:
        code = '%s%05d' % (prefix, n)
        if not Employee.query.filter_by(code=code).first():
            return code
        n += 1


# ---------------------------------------------------------------- auth
def csrf_token():
    tok = session.get('_csrf')
    if not tok:
        tok = session['_csrf'] = secrets.token_urlsafe(32)
    return tok


app.jinja_env.globals['csrf_token'] = csrf_token


def wants_json():
    return request.is_json or request.path.startswith('/attendance/save')


@app.before_request
def csrf_protect():
    """Every state-changing request must carry the secret token of the current session."""
    if request.method in ('POST', 'PUT', 'PATCH', 'DELETE') and app.config.get('CSRF_ENABLED', True):
        sent = request.form.get('_csrf') or request.headers.get('X-CSRF-Token', '')
        good = session.get('_csrf', '')
        if not sent or not good or not hmac.compare_digest(sent.encode('utf-8'), good.encode('utf-8')):
            app.logger.warning('CSRF rejected %s %s from %s', request.method, request.path, request.remote_addr)
            msg = tr('Your session expired or the form was invalid. Please refresh the page and try again.')
            if wants_json():
                return jsonify(error=msg), 400
            flash(msg, 'error')
            return redirect(url_for('dashboard') if current_user.is_authenticated else url_for('login'))


_GZ_TYPES = ('text/html', 'text/css', 'application/javascript', 'text/javascript', 'application/json', 'image/svg+xml')
_gz_static = {}
CSP = ("default-src 'self'; img-src 'self' data:; style-src 'self' 'unsafe-inline'; script-src 'self' 'unsafe-inline'; "
       "font-src 'self'; object-src 'none'; base-uri 'self'; form-action 'self'; frame-ancestors 'none'")


@app.after_request
def secure_and_compress(resp):
    h = resp.headers
    h['X-Content-Type-Options'] = 'nosniff'
    h['X-Frame-Options'] = 'DENY'
    h['Referrer-Policy'] = 'same-origin'
    h['Permissions-Policy'] = 'geolocation=(), microphone=(), camera=()'
    h['Content-Security-Policy'] = CSP
    if HTTPS_ONLY:
        h['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
    if request.endpoint != 'static' and resp.mimetype in ('text/html', 'application/json'):
        h['Cache-Control'] = 'no-store'            # never keep personal data in the browser cache
    elif request.endpoint == 'static' and request.args.get('v'):
        h['Cache-Control'] = 'public, max-age=31536000, immutable'     # versioned file (?v=...): never asked for again
    # gzip: 4-6x smaller pages = fast on slow networks and far less load on the server
    if (resp.status_code == 200 and 'gzip' in request.headers.get('Accept-Encoding', '') and 'Content-Encoding' not in h
            and resp.mimetype in _GZ_TYPES):
        if request.endpoint == 'static':
            key = (request.path, h.get('ETag'))
            data = _gz_static.get(key)
            if data is None:
                resp.direct_passthrough = False
                data = gzip.compress(resp.get_data(), 6)
                if len(_gz_static) < 64:
                    _gz_static[key] = data
        else:
            resp.direct_passthrough = False
            raw = resp.get_data()
            data = gzip.compress(raw, 5) if len(raw) > 1024 else None
        if data is not None:
            resp.set_data(data)
            h['Content-Encoding'] = 'gzip'
            h['Content-Length'] = str(len(data))
            h.add('Vary', 'Accept-Encoding')
    return resp


def error_page(code, title, msg):
    if wants_json():
        return jsonify(error=msg), code
    try:
        return render_template('error.html', code=code, title=title, msg=msg), code
    except Exception:
        return '%s %s' % (code, title), code


@app.errorhandler(HTTPException)
def on_http_error(e):
    msgs = {403: ('Access denied', 'You do not have permission to open this page.'),
            404: ('Page not found', 'The page you are looking for does not exist.'),
            405: ('Not allowed', 'This action is not allowed.'),
            413: ('Too much data', 'The request was too large.'),
            429: ('Too many requests', 'Please wait a moment and try again.')}
    title, msg = msgs.get(e.code, (e.name, e.description))
    return error_page(e.code, tr(title), tr(msg))


@app.errorhandler(OperationalError)
def on_db_busy(e):
    db.session.rollback()
    app.logger.error('database unavailable/busy: %s', e)
    return error_page(503, tr('Server is busy'), tr('The database is busy right now. Please try again in a few seconds.'))


@app.errorhandler(Exception)
def on_crash(e):
    db.session.rollback()
    app.logger.exception('unhandled error on %s %s', request.method, request.path)
    return error_page(500, tr('Something went wrong'), tr('The error has been recorded. Please try again; if it continues, contact the administrator.'))


@app.route('/healthz')
def healthz():
    """For load balancers / monitoring: 200 only when the database answers."""
    try:
        db.session.execute(text('SELECT 1'))
        return jsonify(status='ok', version=APP_VERSION)
    except SQLAlchemyError:
        db.session.rollback()
        return jsonify(status='db-error'), 503


def static_v(filename):
    return url_for('static', filename=filename, v=APP_VERSION)


@app.before_request
def force_password_change():
    if current_user.is_authenticated and current_user.must_change \
            and request.endpoint not in ('change_password', 'logout', 'set_lang', 'static'):
        flash(tr('You must change your password before continuing.'), 'error')
        return redirect(url_for('change_password'))


@app.before_request
def project_guard():
    """A logged-in user whose projects were all taken away is signed out."""
    if current_user.is_authenticated and request.endpoint not in ('logout', 'static', 'set_lang') and current_project() is None:
        audit('logout-no-project', '')
        logout_user()
        session.clear()
        flash(tr('No project is assigned to your account. Please contact the administrator.'), 'error')
        return redirect(url_for('login'))


_DUMMY_HASH = generate_password_hash('no-such-user')      # same cost as a real hash -> no timing difference


def login_blocked(ip, username):
    since = datetime.utcnow() - timedelta(minutes=5)
    n_ip = LoginAttempt.query.filter(LoginAttempt.ip == ip, LoginAttempt.username != '(check)', LoginAttempt.ts >= since).count()
    n_user = LoginAttempt.query.filter(LoginAttempt.username == username, LoginAttempt.ts >= since).count() if username else 0
    return n_ip >= 60 or n_user >= 6          # per IP is generous: a whole office may share one address


def record_failed_login(ip, username):
    db.session.add(LoginAttempt(ip=ip, username=username))
    if random.random() < 0.02:                # housekeeping: keep the table small
        LoginAttempt.query.filter(LoginAttempt.ts < datetime.utcnow() - timedelta(days=1)).delete()
    db.session.commit()


def project_for_login(u, pid):
    """The project a user asks to enter, or None when he may not open it (no pid = his first project)."""
    projs = accessible_projects(u)
    if pid is None:
        return projs[0] if projs else None
    return next((p for p in projs if p.id == pid), None)


@app.route('/login/check', methods=['POST'])
def login_check():
    """Step 1 of the login: which project(s) does this username belong to?  The password box is shown only
    when the username exists and has at least one project."""
    if current_user.is_authenticated:
        return jsonify(found=False)
    ip = (request.remote_addr or '-')[:45]
    since = datetime.utcnow() - timedelta(minutes=1)
    if LoginAttempt.query.filter(LoginAttempt.ip == ip, LoginAttempt.username == '(check)', LoginAttempt.ts >= since).count() >= 40:
        return jsonify(error='busy'), 429
    record_failed_login(ip, '(check)')
    uname = request.form.get('username', '').strip()[:50]
    u = User.query.filter_by(username=uname).first() if uname else None
    if u is None or not u.is_active_user:
        return jsonify(found=False)
    return jsonify(found=True, projects=[dict(id=p.id, name=p.name, company=p.company) for p in accessible_projects(u)])


@app.route('/', methods=['GET', 'POST'])
@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    uname, sel_pid = '', None
    if request.method == 'POST':
        ip = (request.remote_addr or '-')[:45]
        f = request.form
        uname = f.get('username', '').strip()[:50]
        sel_pid = f.get('project_id', type=int)
        if login_blocked(ip, uname):
            audit('login-blocked', 'too many attempts', username=uname)
            flash(tr('Too many failed attempts. Please try again after 5 minutes.'), 'error')
        else:
            u = User.query.filter_by(username=uname).first()
            ok = check_password_hash(u.password_hash, f.get('password', '')) if u else check_password_hash(
                _DUMMY_HASH, f.get('password', ''))
            if u and ok:
                proj = project_for_login(u, sel_pid) if u.is_active_user else None
                if not u.is_active_user:
                    audit('login-disabled', 'disabled account', username=uname)
                    flash(tr('This account is disabled. Please contact the administrator.'), 'error')
                elif proj is None:
                    audit('login-no-project', 'project=%s' % sel_pid, username=uname)
                    flash(tr('You do not have access to this project. Please contact the administrator.'), 'error')
                else:
                    session.clear()                      # new session after login (prevents session fixation)
                    session.permanent = True
                    login_user(u, remember=f.get('remember') == '1')
                    session['project_id'] = proj.id
                    audit('login', 'project=' + proj.name, username=u.username)
                    nxt = request.args.get('next', '')
                    if nxt.startswith('/') and not nxt.startswith('//') and '\\' not in nxt:
                        return redirect(nxt)
                    return redirect(url_for('dashboard'))
            else:
                record_failed_login(ip, uname)
                audit('login-failed', '', username=uname)
                flash(tr('Incorrect username or password.'), 'error')
    return render_template('login.html', uname=uname, sel_pid=sel_pid)


@app.route('/project/switch', methods=['POST'])
@login_required
def project_switch():
    pid = request.form.get('project_id', type=int)
    p = next((x for x in accessible_projects() if x.id == pid), None) or abort(403)
    session['project_id'] = p.id
    audit('project-switch', 'project=' + p.name)
    flash('%s: %s' % (tr('Project'), p.company), 'ok')
    return redirect(url_for('dashboard'))


@app.route('/lang/<code>')
def set_lang(code):
    if code in ('en', 'hi'):
        session['lang'] = code
    ref = request.referrer or ''
    if ref and urlparse(ref).netloc == request.host:
        return redirect(ref)
    return redirect(url_for('login'))


@app.route('/change-password', methods=['GET', 'POST'])
@login_required
def change_password():
    if request.method == 'POST':
        f = request.form
        cur, new, conf = f.get('current', ''), f.get('new', ''), f.get('confirm', '')
        if not check_password_hash(current_user.password_hash, cur):
            flash(tr('Current password is incorrect.'), 'error')
        elif not valid_password(new):
            flash(tr(PW_RULE), 'error')
        elif new != conf:
            flash(tr('New password and confirmation do not match.'), 'error')
        elif check_password_hash(current_user.password_hash, new):
            flash(tr('New password must be different from the current password.'), 'error')
        else:
            current_user.password_hash = generate_password_hash(new)
            current_user.must_change = False
            db.session.commit()
            audit('password-change')
            flash(tr('Password changed successfully.'), 'ok')
            return redirect(url_for('dashboard'))
    return render_template('change_password.html')


@app.route('/logout')
@login_required
def logout():
    audit('logout')
    logout_user()
    session.clear()
    return redirect(url_for('login'))


# ---------------------------------------------------------------- dashboard
@app.route('/dashboard')
@login_required
def dashboard():
    d = date.today()
    q = scope_att(Attendance.query.filter_by(att_date=d))
    employees_n = scope_emp(Employee.query.filter_by(active=True)).count()
    marked = q.with_entities(Attendance.employee_id).distinct().count()
    grp = q.with_entities(Attendance.status, Attendance.shift, Attendance.work_type, func.count(Attendance.id)) \
           .group_by(Attendance.status, Attendance.shift, Attendance.work_type).all()      # one query instead of ten

    def n(test):
        return sum(c for st, sh, wt, c in grp if test(st, sh, wt))
    stats = dict(
        employees=employees_n,
        wards=len(my_wards()),
        present=n(lambda st, sh, wt: st == 'Present'),
        absent=n(lambda st, sh, wt: st == 'Absent'),
        leave=n(lambda st, sh, wt: st in ('Leave', 'Half Day')),
        day=n(lambda st, sh, wt: st == 'Present' and sh == 'Day'),
        night=n(lambda st, sh, wt: st == 'Present' and sh == 'Night'),
        not_marked=max(0, employees_n - marked))
    work = {w: n(lambda st, sh, wt, w=w: st == 'Present' and wt == w) for w in my_works()}
    per_day = dict(scope_att(Attendance.query.filter(Attendance.att_date.between(d - timedelta(days=6), d),
                                                     Attendance.status == 'Present'))
                   .with_entities(Attendance.att_date, func.count(Attendance.id)).group_by(Attendance.att_date).all())
    trend = []
    for i in range(6, -1, -1):
        dd = d - timedelta(days=i)
        trend.append(dict(n=per_day.get(dd, 0), day=day_label(dd), date=dd.strftime('%d/%m'), sun=dd.weekday() == 6,
                          today=dd == d))
    upcoming = holiday_q().filter(Holiday.hdate >= d).order_by(Holiday.hdate).limit(4).all()
    return render_template('dashboard.html', stats=stats, work=work, trend=trend, upcoming=upcoming)


# ---------------------------------------------------------------- zones
@app.route('/zones', methods=['GET', 'POST'])
@perm('zones', 'view')
def zones():
    edit = None
    if request.method == 'POST':
        zid = request.form.get('id', type=int)
        name = request.form.get('name', '').strip()[:100]
        if not name:
            flash(tr('Please enter the zone name.'), 'error')
        elif zid:
            if not current_user.can('zones', 'edit'):
                abort(403)
            if int(zid) not in [z.id for z in my_zones()]:
                abort(403)
            if Zone.query.filter(Zone.name == name, Zone.project_id == cur_pid(), Zone.id != int(zid)).first():
                flash(tr('This zone already exists.'), 'error')
            else:
                db.session.get(Zone, int(zid)).name = name
                db.session.commit()
                flash(tr('Zone updated.'), 'ok')
        else:
            if not current_user.can('zones', 'add'):
                abort(403)
            if zones_user_limited():
                flash(tr('You cannot add a zone because your access is limited to specific zones.'), 'error')
            elif Zone.query.filter_by(name=name, project_id=cur_pid()).first():
                flash(tr('This zone already exists.'), 'error')
            else:
                db.session.add(Zone(name=name, project_id=cur_pid()))
                db.session.commit()
                flash(tr('Zone added.'), 'ok')
        return redirect(url_for('zones'))
    mine = my_zones()
    if request.args.get('edit'):
        edit = next((z for z in mine if z.id == request.args.get('edit', type=int)), None)
    counts = dict(db.session.query(Ward.zone_id, func.count(Ward.id)).group_by(Ward.zone_id).all())
    return render_template('zones.html', zones=mine, edit=edit, counts=counts)


@app.route('/zones/<int:id>/delete', methods=['POST'])
@perm('zones', 'delete')
def zone_delete(id):
    z = db.session.get(Zone, id) or abort(404)
    if z.id not in [x.id for x in my_zones()]:
        abort(403)
    if z.wards:
        flash(tr('This zone has wards. Delete the wards first.'), 'error')
    else:
        db.session.delete(z)
        db.session.commit()
        flash(tr('Zone deleted.'), 'ok')
    return redirect(url_for('zones'))


# ---------------------------------------------------------------- wards
@app.route('/wards', methods=['GET', 'POST'])
@perm('wards', 'view')
def wards():
    edit = None
    if request.method == 'POST':
        wid = request.form.get('id', type=int)
        name = request.form.get('name', '').strip()[:100]
        zone_id = request.form.get('zone_id', type=int)
        if not name or not zone_id:
            flash(tr('Zone and ward name are required.'), 'error')
        elif int(zone_id) not in [z.id for z in my_zones()]:
            abort(403)
        elif wid:
            if not current_user.can('wards', 'edit'):
                abort(403)
            w = next((x for x in my_wards() if x.id == int(wid)), None) or abort(403)
            if Ward.query.filter(Ward.zone_id == int(zone_id), func.lower(Ward.name) == name.lower(), Ward.id != w.id).first():
                flash(tr('This ward already exists in this zone.'), 'error')
            else:
                w.name, w.zone_id = name, int(zone_id)
                db.session.commit()
                flash(tr('Ward updated.'), 'ok')
        else:
            if not current_user.can('wards', 'add'):
                abort(403)
            if Ward.query.filter(Ward.zone_id == int(zone_id), func.lower(Ward.name) == name.lower()).first():
                flash(tr('This ward already exists in this zone.'), 'error')
            else:
                db.session.add(Ward(name=name, zone_id=int(zone_id)))
                db.session.commit()
                flash(tr('Ward added.'), 'ok')
        return redirect(url_for('wards'))
    mine = my_wards()
    if request.args.get('edit'):
        edit = next((w for w in mine if w.id == request.args.get('edit', type=int)), None)
    counts = dict(db.session.query(Employee.ward_id, func.count(Employee.id)).group_by(Employee.ward_id).all())
    return render_template('wards.html', edit=edit, zones=my_zones(), wards=mine, counts=counts)


@app.route('/wards/<int:id>/delete', methods=['POST'])
@perm('wards', 'delete')
def ward_delete(id):
    w = db.session.get(Ward, id) or abort(404)
    if w.id not in [x.id for x in my_wards()]:
        abort(403)
    if db.session.query(Employee.id).filter_by(ward_id=w.id).first():
        flash(tr('This ward has employees. Remove or move them first.'), 'error')
    else:
        db.session.delete(w)
        db.session.commit()
        flash(tr('Ward deleted.'), 'ok')
    return redirect(url_for('wards'))


# ---------------------------------------------------------------- holidays
@app.route('/holidays', methods=['GET', 'POST'])
@perm('holidays', 'view')
def holidays():
    edit = None
    if request.method == 'POST':
        f = request.form
        d, name = parse_date(f.get('hdate')), f.get('name', '').strip()
        hid = f.get('id', type=int)
        if not d or not name:
            flash(tr('Please enter the holiday date and name.'), 'error')
        else:
            dup = holiday_q().filter_by(hdate=d).first()
            if hid:
                if not current_user.can('holidays', 'edit'):
                    abort(403)
                h = holiday_q().filter_by(id=int(hid)).first() or abort(404)
                if dup and dup.id != h.id:
                    flash(tr('A holiday already exists on this date.'), 'error')
                    return redirect(url_for('holidays', year=d.year))
                h.hdate, h.name = d, name
                db.session.commit()
                flash(tr('Holiday updated.'), 'ok')
            else:
                if not current_user.can('holidays', 'add'):
                    abort(403)
                if dup:
                    flash(tr('A holiday already exists on this date.'), 'error')
                else:
                    db.session.add(Holiday(hdate=d, name=name, project_id=cur_pid()))
                    db.session.commit()
                    flash(tr('Holiday added.'), 'ok')
            return redirect(url_for('holidays', year=d.year))
    year = request.args.get('year', type=int) or date.today().year
    if request.args.get('edit', type=int):
        edit = holiday_q().filter_by(id=request.args.get('edit', type=int)).first()
    rows = holiday_q().filter(Holiday.hdate.between(date(year, 1, 1), date(year, 12, 31))).order_by(Holiday.hdate).all()
    return render_template('holidays.html', rows=rows, edit=edit, year=year)


@app.route('/holidays/<int:id>/delete', methods=['POST'])
@perm('holidays', 'delete')
def holiday_delete(id):
    h = holiday_q().filter_by(id=id).first() or abort(404)
    y = h.hdate.year
    db.session.delete(h)
    db.session.commit()
    flash(tr('Holiday deleted.'), 'ok')
    return redirect(url_for('holidays', year=y))


# ---------------------------------------------------------------- employees
DESIGNATIONS = ['Driver', 'Helper', 'Trolleyman', 'Ward Manager', 'Ward Incharge', 'Sweeper']
CREW_ROLES = ('driver', 'helper')                 # may have a Vehicle No
ROUTE_ROLES = ('driver', 'helper', 'trolleyman')  # may have a Route ID
TRACKER_ROLES = ('trolleyman',)                   # may have a Tracker ID
VEH_RE = re.compile(r'^[A-Z0-9][A-Z0-9 \-]{2,19}$')


def role_of(designation):
    """'driver' / 'helper' for crew members, otherwise None (only they may have a vehicle)."""
    d = (designation or '').strip().lower()
    return d if d in CREW_ROLES else None


def desig_key(designation):
    d = re.sub(r'\s+', ' ', (designation or '').strip().lower())
    return 'trolleyman' if d in ('trolleyman', 'trollyman', 'trolley man') else d


def has_route(designation):
    return desig_key(designation) in ROUTE_ROLES


def has_tracker(designation):
    return desig_key(designation) in TRACKER_ROLES


def veh_key(no):
    return re.sub(r'[\s\-]+', '', (no or '').upper())


ROUTE_RE = re.compile(r'^[A-Z0-9][A-Z0-9 \-/]{0,19}$')


def route_key(no):
    return re.sub(r'[\s\-/]+', '', (no or '').upper())


def desig_text(e):
    """Designation, followed by the vehicle number for drivers / helpers: 'Driver - UP32 AB 1234'."""
    parts = [e.designation or '']
    v, r, t = getattr(e, 'vehicle', None), getattr(e, 'route', None), getattr(e, 'tracker', None)
    if v is not None:
        parts.append(v.vehicle_no)
    if t is not None:
        parts.append('%s %s' % (tr('Tracker'), t.tracker_no))
    if r is not None:
        parts.append('%s %s' % (tr('Route'), r.route_no))
    return ' - '.join(p for p in parts if p)


app.jinja_env.globals['desig_text'] = desig_text


def get_designation(f):
    if 'designation_sel' in f:
        sel = f.get('designation_sel', '').strip()
        return (f.get('designation_other', '').strip() if sel == '__other__' else sel)[:60]
    return f.get('designation', '').strip()[:60]


def desig_form_values(designation):
    d = (designation or '').strip()
    for x in DESIGNATIONS:
        if x.lower() == d.lower() or desig_key(x) == desig_key(d) == 'trolleyman':
            return x, ''
    return ('__other__', d) if d else ('', '')


def scope_vehicle(q):
    """A user only sees vehicles of his zones (and of his wards, when the vehicle belongs to a ward)."""
    if zones_limited():
        q = q.filter(Vehicle.zone_id.in_([z.id for z in my_zones()] or [0]))
    if not (current_user.is_super or current_user.all_wards):
        q = q.filter(db.or_(Vehicle.ward_id.is_(None), Vehicle.ward_id.in_([w.id for w in my_wards()] or [0])))
    return q


def make_pg(total, page, per_page):
    pages = max(1, -(-total // per_page))
    page = min(max(page, 1), pages)
    shown = sorted({1, pages} | {p for p in range(page - 2, page + 3) if 1 <= p <= pages})
    window = []
    for p in shown:
        if window and p - window[-1] > 1:
            window.append(None)
        window.append(p)
    return dict(page=page, pages=pages, per_page=per_page, total=total, window=window,
                first=(page - 1) * per_page + 1 if total else 0, last=min(page * per_page, total))


def scope_route(q):
    """Same rule as vehicles: only routes of the user's zones (and wards, when the route belongs to a ward)."""
    if zones_limited():
        q = q.filter(Route.zone_id.in_([z.id for z in my_zones()] or [0]))
    if not (current_user.is_super or current_user.all_wards):
        q = q.filter(db.or_(Route.ward_id.is_(None), Route.ward_id.in_([w.id for w in my_wards()] or [0])))
    return q


def scope_tracker(q):
    if zones_limited():
        q = q.filter(Tracker.zone_id.in_([z.id for z in my_zones()] or [0]))
    return q


def tracker_error(f, current_tracker_id=None):
    """Checks the Tracker ID chosen on the employee form. Returns an error text, or None when fine."""
    if not current_user.can('trackers', 'view'):
        return None
    tid = (f.get('tracker_id') or '').strip()
    if not tid or not has_tracker(get_designation(f)):
        return None
    if not tid.isdigit():
        return tr('Please choose a valid tracker.')
    tid = int(tid)
    t = scope_tracker(Tracker.query.filter_by(id=tid)).first()
    if t is None and tid != current_tracker_id:
        return tr('Please choose a valid tracker.')
    t = t or db.session.get(Tracker, tid)
    if t is None or t.zone_id != int(f['zone_id']):
        return tr('The selected tracker does not belong to the selected zone.')
    if not t.active and tid != current_tracker_id:
        return tr('This tracker is inactive. Choose an active tracker.')
    return None


def route_error(f, current_route_id=None):
    """Checks the Route ID chosen on the employee form. Returns an error text, or None when fine."""
    if not current_user.can('routes', 'view'):
        return None
    rid = (f.get('route_id') or '').strip()
    if not rid or not has_route(get_designation(f)):
        return None
    if not rid.isdigit():
        return tr('Please choose a valid route.')
    rid = int(rid)
    r = scope_route(Route.query.filter_by(id=rid)).first()
    if r is None and rid != current_route_id:
        return tr('Please choose a valid route.')
    r = r or db.session.get(Route, rid)
    if r is None or r.zone_id != int(f['zone_id']):
        return tr('The selected route does not belong to the selected zone.')
    if not r.active and rid != current_route_id:
        return tr('This route is inactive. Choose an active route.')
    return None


def vehicle_error(f, current_vehicle_id=None):
    """Checks the vehicle chosen on the employee form. Returns an error text, or None when fine."""
    if not current_user.can('vehicles', 'view'):
        return None
    vid = (f.get('vehicle_id') or '').strip()
    if not vid or role_of(get_designation(f)) is None:
        return None
    if not vid.isdigit():
        return tr('Please choose a valid vehicle.')
    vid = int(vid)
    v = scope_vehicle(Vehicle.query.filter_by(id=vid)).first()
    if v is None and vid != current_vehicle_id:
        return tr('Please choose a valid vehicle.')
    v = v or db.session.get(Vehicle, vid)
    if v is None or v.zone_id != int(f['zone_id']):
        return tr('The selected vehicle does not belong to the selected zone.')
    if not v.active and vid != current_vehicle_id:
        return tr('This vehicle is inactive. Choose an active vehicle.')
    return None


def fill_employee(e, f):
    e.name = f['name'].strip()
    e.father_name = f.get('father_name', '').strip()
    e.mobile = f.get('mobile', '').strip()
    e.designation = get_designation(f)
    if role_of(e.designation) is None:
        e.vehicle_id = None                      # only Driver and Helper can have a vehicle
    elif current_user.can('vehicles', 'view') and 'vehicle_id' in f:
        vid = (f.get('vehicle_id') or '').strip()
        e.vehicle_id = int(vid) if vid.isdigit() else None
    if not has_route(e.designation):
        e.route_id = None                        # only Driver, Helper and Trolleyman can have a route
    elif current_user.can('routes', 'view') and 'route_id' in f:
        rid = (f.get('route_id') or '').strip()
        e.route_id = int(rid) if rid.isdigit() else None
    if not has_tracker(e.designation):
        e.tracker_id = None                      # only Trolleyman has a tracker
    elif current_user.can('trackers', 'view') and 'tracker_id' in f:
        tid = (f.get('tracker_id') or '').strip()
        e.tracker_id = int(tid) if tid.isdigit() else None
    e.zone_id = int(f['zone_id'])
    e.ward_id = int(f['ward_id'])
    e.default_shift = f.get('default_shift', 'Day')
    e.default_work = f.get('default_work', 'Door to Door')
    e.joining_date = parse_date(f.get('joining_date'))
    e.active = f.get('active') == '1'


def employee_fields_error(f):
    """Required fields of the employee form (a half-filled or hand-made POST must give a message, not a crash)."""
    if not f.get('name', '').strip():
        return tr('Please enter the employee name.')
    if not (f.get('zone_id', '').strip().isdigit() and f.get('ward_id', '').strip().isdigit()):
        return tr('Please select the zone and the ward.')
    if f.get('default_shift', 'Day') not in SHIFTS:
        return tr('Please choose a valid shift.')
    return None


def emp_allowed(f):
    ward = next((w for w in my_wards() if w.id == int(f['ward_id'])), None)
    return (ward is not None and ward.zone_id == int(f['zone_id'])
            and int(f['zone_id']) in [z.id for z in my_zones()]
            and f.get('default_work') in my_works())


@app.route('/employees')
@perm('employees', 'view')
def employees():
    q = scope_emp(Employee.query)
    zone_id, ward_id, s = request.args.get('zone_id'), request.args.get('ward_id'), request.args.get('q', '').strip()
    zone_id = zone_id if (zone_id or '').isdigit() else ''
    ward_id = ward_id if (ward_id or '').isdigit() else ''
    if zone_id:
        q = q.filter_by(zone_id=int(zone_id))
    if ward_id:
        q = q.filter_by(ward_id=int(ward_id))
    if s:
        conds = [Employee.name.like('%' + s + '%'), Employee.code.like('%' + s + '%'),
                 Employee.mobile.like('%' + s + '%')]
        if veh_key(s):
            conds.append(Employee.vehicle.has(Vehicle.vkey.like('%' + veh_key(s) + '%')))
        if route_key(s):
            conds.append(Employee.route.has(Route.rkey.like('%' + route_key(s) + '%')))
        q = q.filter(db.or_(*conds))
    per_page = request.args.get('per_page', 25, type=int)
    if per_page not in (10, 25, 50, 100):
        per_page = 25
    total = q.count()
    pages = max(1, -(-total // per_page))
    page = min(max(request.args.get('page', 1, type=int), 1), pages)
    rows = q.options(joinedload(Employee.zone), joinedload(Employee.ward), joinedload(Employee.vehicle),
                          joinedload(Employee.route)).order_by(Employee.name) \
            .offset((page - 1) * per_page).limit(per_page).all()
    shown = sorted({1, pages} | {p for p in range(page - 2, page + 3) if 1 <= p <= pages})
    window = []
    for p in shown:
        if window and p - window[-1] > 1:
            window.append(None)          # gap -> "..."
        window.append(p)
    pg = dict(page=page, pages=pages, per_page=per_page, total=total, window=window,
              first=(page - 1) * per_page + 1 if total else 0, last=min(page * per_page, total))
    qs = {k: v for k, v in (('zone_id', zone_id), ('ward_id', ward_id), ('q', s), ('per_page', per_page)) if v}
    return render_template('employees.html', rows=rows, pg=pg, qs=qs,
                           zones=my_zones(), wards=my_wards(),
                           zone_id=zone_id, ward_id=ward_id, s=s)


def employee_month(e, y, m, nd):
    recs = scope_att(Attendance.query.filter(
        Attendance.employee_id == e.id,
        Attendance.att_date.between(date(y, m, 1), date(y, m, nd)))
    ).order_by(Attendance.att_date, Attendance.shift).all()
    counts = {st: sum(1 for r in recs if r.status == st) for st in STATUSES}
    days_worked = counts['Present'] + counts['Half Day'] * 0.5
    return recs, counts, days_worked


def employee_calendar(e, y, m, nd, recs):
    """Month calendar (Monday first) with attendance, Sundays and holidays."""
    hmap = {h.hdate: h.name for h in holiday_q().filter(Holiday.hdate.between(date(y, m, 1), date(y, m, nd)))}
    by_day = {}
    for r in recs:
        by_day.setdefault(r.att_date, []).append(r)
    today = date.today()
    weeks, week, info = [], [None] * date(y, m, 1).weekday(), {}
    for d in range(1, nd + 1):
        dt = date(y, m, d)
        rl = [dict(shift=tr(r.shift), status=tr(r.status), code=REV_CODES.get(r.status, ''),
                   work=tr(r.work_type or ''), loc=r.location or '', time=r.in_time or '', rem=r.remark or '')
              for r in by_day.get(dt, [])]
        sun, hol = dt.weekday() == 6, hmap.get(dt)
        cell = dict(num=d, iso=dt.isoformat(), sun=sun, hol=hol, today=dt == today, future=dt > today, recs=rl,
                    not_marked=(not rl and dt <= today and not sun and not hol
                                and (not e.joining_date or dt >= e.joining_date)))
        info[dt.isoformat()] = dict(date=dt.strftime('%d-%m-%Y'), day=day_label(dt), sun=sun, hol=hol or '',
                                    recs=rl, nm=cell['not_marked'])
        week.append(cell)
        if len(week) == 7:
            weeks.append(week)
            week = []
    if week:
        weeks.append(week + [None] * (7 - len(week)))
    sundays = sum(1 for d in range(1, nd + 1) if date(y, m, d).weekday() == 6)
    hol_extra = sum(1 for dt in hmap if dt.weekday() != 6)
    return weeks, info, dict(sundays=sundays, holidays=len(hmap), working=nd - sundays - hol_extra)


@app.route('/employees/<int:id>')
@perm('employees', 'view')
def employee_view(id):
    e = scope_emp(Employee.query.filter_by(id=id)).first() or abort(403)
    y, m, nd, days = month_info(request.args.get('month'))
    can_att = current_user.can('attendance', 'view')
    recs, counts, days_worked = employee_month(e, y, m, nd) if can_att else ([], {}, 0)
    weeks, info, dstats = employee_calendar(e, y, m, nd, recs) if can_att else ([], {}, {})
    hmap = {d['d']: d['hol'] for d in days if d['hol']}
    pm = '%04d-%02d' % ((y - 1, 12) if m == 1 else (y, m - 1))
    nm = '%04d-%02d' % ((y + 1, 1) if m == 12 else (y, m + 1))
    wd_labels = [day_label(date(2026, 10, 19 + i)) for i in range(7)]   # Mon..Sun
    return render_template('employee_view.html', e=e, recs=recs, counts=counts, days_worked=days_worked,
                           month='%04d-%02d' % (y, m), pm=pm, nm=nm, can_att=can_att, weeks=weeks, info=info,
                           dstats=dstats, hmap=hmap, wd_labels=wd_labels,
                           can_export=current_user.can('attendance', 'export'),
                           month_name='%s %d' % (month_label(m), y))


@app.route('/employees/<int:id>/export')
@perm('attendance', 'export')
def employee_export(id):
    e = scope_emp(Employee.query.filter_by(id=id)).first() or abort(403)
    y, m, nd, days = month_info(request.args.get('month'))
    recs, counts, days_worked = employee_month(e, y, m, nd)
    wb = Workbook()
    ws = wb.active
    ws.title = 'Attendance'
    ws.append(['%s - %s' % (company_name(), tr('Employee Attendance'))])
    ws['A1'].font = Font(bold=True, size=14)
    info = [(tr('Employee Code'), e.code), (tr('Name'), e.name), (tr("Father's Name"), e.father_name or ''),
            (tr('Designation'), e.designation or ''), (tr('Vehicle Number'), e.vehicle.vehicle_no if e.vehicle else ''),
            (tr('Route ID'), e.route.route_no if e.route else ''),
            (tr('Mobile'), e.mobile or ''),
            (tr('Zone'), e.zone.name), (tr('Ward'), e.ward.name), (tr('Month'), '%s %d' % (month_label(m), y))]
    for k, v in info:
        ws.append([k, v])
        ws.cell(row=ws.max_row, column=1).font = Font(bold=True)
    ws.append([])
    ws.append([tr(h) for h in ('Date', 'Day', 'Day Type', 'Shift', 'Status', 'Work Type', 'Location', 'In Time', 'Remark')])
    for c in ws[ws.max_row]:
        c.font = Font(bold=True, color='FFFFFF')
        c.fill = PatternFill('solid', fgColor='1F3A68')
        c.alignment = Alignment(horizontal='center')
    by_day = {}
    for r in recs:
        by_day.setdefault(r.att_date, []).append(r)
    hmap = {d['d']: d['hol'] for d in days if d['hol']}
    today = date.today()
    for dnum in range(1, nd + 1):
        dt = date(y, m, dnum)
        hol, sun = hmap.get(dnum), dt.weekday() == 6
        dtype = ('%s: %s' % (tr('Holiday'), hol)) if hol else (tr('Sunday') if sun else '')
        fill = PatternFill('solid', fgColor='F3E5F5' if hol else 'FFF3E0') if (hol or sun) else None
        rl = by_day.get(dt) or [None]
        for r in rl:
            if r:
                row = [dt.strftime('%d-%m-%Y'), day_label(dt), dtype, tr(r.shift), tr(r.status), tr(r.work_type or ''),
                       r.location, r.in_time, r.remark]
            else:
                nm = dt <= today and not sun and not hol and (not e.joining_date or dt >= e.joining_date)
                row = [dt.strftime('%d-%m-%Y'), day_label(dt), dtype, '', tr('Not Marked') if nm else '', '', '', '', '']
            ws.append(row)
            if fill:
                for c in ws[ws.max_row]:
                    c.fill = fill
    ws.append([])
    for st in STATUSES:
        ws.append([tr(st), counts[st]])
        ws.cell(row=ws.max_row, column=1).font = Font(bold=True)
    ws.append([tr('Days Worked'), days_worked])
    ws.cell(row=ws.max_row, column=1).font = Font(bold=True)
    for col, w in zip('ABCDEFGHI', [20, 24, 22, 10, 14, 15, 28, 10, 24]):
        ws.column_dimensions[col].width = w
    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)
    return send_file(buf, as_attachment=True, download_name='employee_%s_%04d-%02d.xlsx' % (e.code, y, m),
                     mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')


def employee_form_ctx(e):
    """Vehicle / Route / Tracker are picked with a search box that asks /lookup/<kind> (30 matches at a time),
    so the page no longer carries thousands of options.  Only the employee's current choice is sent."""
    can_veh = current_user.can('vehicles', 'view')
    can_rt = current_user.can('routes', 'view')
    can_trk = current_user.can('trackers', 'view')
    sel, other = desig_form_values(e.designation if e is not None else '')
    cur = lambda kind, o: dict(id=o.id, label=lookup_label(kind, o), zone=o.zone_id) if o is not None else None
    return dict(can_trackers=can_trk, can_vehicles=can_veh, can_routes=can_rt,
                cur_veh=cur('vehicle', e.vehicle) if (e is not None and can_veh) else None,
                cur_route=cur('route', e.route) if (e is not None and can_rt) else None,
                cur_trk=cur('tracker', e.tracker) if (e is not None and can_trk) else None,
                zones=my_zones(), wards=my_wards(), works=my_works(),
                desig_list=DESIGNATIONS, desig_sel=sel, desig_other=other)


@app.route('/employees/add', methods=['GET', 'POST'])
@perm('employees', 'add')
def employee_add():
    if request.method == 'POST':
        ferr = employee_fields_error(request.form)
        verr = None if ferr else (vehicle_error(request.form) or route_error(request.form) or tracker_error(request.form))
        if ferr:
            flash(ferr, 'error')
        elif not emp_allowed(request.form):
            flash(tr('You do not have access to add employees in this ward or work type.'), 'error')
        elif verr:
            flash(verr, 'error')
        else:
            e = Employee(code=next_code())
            fill_employee(e, request.form)
            db.session.add(e)
            db.session.commit()
            audit('employee-add', '%s %s' % (e.code, e.name))
            flash(tr('Employee added. Code:') + ' ' + e.code, 'ok')
            return redirect(url_for('employees'))
    return render_template('employee_form.html', e=None, code=next_code(), **employee_form_ctx(None))


@app.route('/employees/<int:id>/edit', methods=['GET', 'POST'])
@perm('employees', 'edit')
def employee_edit(id):
    e = scope_emp(Employee.query.filter_by(id=id)).first() or abort(403)
    if request.method == 'POST':
        ferr = employee_fields_error(request.form)
        verr = None if ferr else (vehicle_error(request.form, e.vehicle_id) or route_error(request.form, e.route_id) or tracker_error(request.form, e.tracker_id))
        if ferr:
            flash(ferr, 'error')
        elif not emp_allowed(request.form):
            flash(tr('You do not have access to keep an employee in this ward or work type.'), 'error')
        elif verr:
            flash(verr, 'error')
        else:
            fill_employee(e, request.form)
            db.session.commit()
            audit('employee-update', '%s %s' % (e.code, e.name))
            flash(tr('Employee updated.'), 'ok')
            return redirect(url_for('employees'))
    return render_template('employee_form.html', e=e, code=e.code, **employee_form_ctx(e))


@app.route('/employees/<int:id>/delete', methods=['POST'])
@perm('employees', 'delete')
def employee_delete(id):
    e = scope_emp(Employee.query.filter_by(id=id)).first() or abort(403)
    Attendance.query.filter_by(employee_id=id).delete()
    db.session.delete(e)
    db.session.commit()
    audit('employee-delete', '%s %s' % (e.code, e.name))
    flash(tr('Employee deleted.'), 'ok')
    return redirect(url_for('employees'))


# ---------------------------------------------------------------- attendance sheet (Excel style)
def safe_name(text_):
    """Part of a download file name: letters (any language), digits, - and _ only."""
    return re.sub(r'[^\w\-]+', '_', text_ or '', flags=re.UNICODE).strip('_') or 'file'


def month_info(s):
    try:
        y, m = map(int, (s or '').split('-'))
        date(y, m, 1)
    except (ValueError, TypeError):
        t = date.today()
        y, m = t.year, t.month
    nd = calendar.monthrange(y, m)[1]
    hol = {h.hdate.day: h.name for h in holiday_q().filter(Holiday.hdate.between(date(y, m, 1), date(y, m, nd)))}
    days = [{'d': d, 'wd': day_label(date(y, m, d)), 'sun': date(y, m, d).weekday() == 6,
             'hol': hol.get(d)} for d in range(1, nd + 1)]
    return y, m, nd, days


def load_sheet(ward_id, shift, wt, y, m, nd):
    first, last = date(y, m, 1), date(y, m, nd)
    emps = Employee.query.options(joinedload(Employee.vehicle), joinedload(Employee.route)).filter_by(ward_id=ward_id, active=True, default_work=wt) \
        .order_by(Employee.name).all()
    recs = Attendance.query.filter(Attendance.ward_id == ward_id, Attendance.shift == shift,
                                   Attendance.att_date.between(first, last)).all()
    # also show employees who already have entries under this work type
    have = {e.id for e in emps}
    extra = {r.employee_id for r in recs if r.work_type == wt and r.employee_id not in have}
    if extra:
        emps += Employee.query.options(joinedload(Employee.vehicle), joinedload(Employee.route)).filter(Employee.id.in_(extra)).order_by(Employee.name).all()
    ids = {e.id for e in emps}
    data = {}
    for r in recs:
        if r.employee_id in ids:
            data.setdefault(str(r.employee_id), {})[str(r.att_date.day)] = dict(
                s=r.status, loc=r.location or '', time=r.in_time or '', rem=r.remark or '', wt=r.work_type or wt)
    return emps, data


def sheet_args():
    a = request.args
    wards, works, shifts = my_wards(), my_works(), my_shifts()
    y, m, nd, days = month_info(a.get('month'))
    ward_id = a.get('ward_id', type=int)
    shift = a.get('shift') or (shifts[0] if shifts else '')
    wt = a.get('work_type') or (works[0] if works else '')
    valid = ward_id in [w.id for w in wards] and shift in shifts and wt in works
    return dict(wards=wards, works=works, shifts=shifts, y=y, m=m, nd=nd, days=days,
                ward_id=ward_id, shift=shift, wt=wt, valid=valid)


@app.route('/attendance')
@perm('attendance', 'view')
def attendance():
    s = sheet_args()
    ctx = dict(s, month='%04d-%02d' % (s['y'], s['m']), loaded=False)
    if s['valid']:
        emps, data = load_sheet(s['ward_id'], s['shift'], s['wt'], s['y'], s['m'], s['nd'])
        lock = locked_before()
        ctx.update(loaded=True, emps=[dict(id=e.id, code=e.code, name=e.name, father=e.father_name or '',
                              desig=e.designation or '',
                              veh=e.vehicle.vehicle_no if e.vehicle else '',
                              route=e.route.route_no if e.route else '') for e in emps],
                   can_view_emp=current_user.can('employees', 'view'),
                   data=data, lock=lock.isoformat() if lock else '',
                   flags=dict(add=current_user.can('attendance', 'add'),
                              edit=current_user.can('attendance', 'edit'),
                              delete=current_user.can('attendance', 'delete')),
                   can_export=current_user.can('attendance', 'export'))
    return render_template('attendance.html', **ctx)


@app.route('/attendance/save', methods=['POST'])
@perm('attendance', 'view')
def attendance_save():
    j = request.get_json(silent=True) or {}
    try:
        ward_id, shift, wt = int(j['ward_id']), j['shift'], j['work_type']
        y, m = map(int, j['month'].split('-'))
        date(y, m, 1)
        changes = list(j.get('changes', []))
    except Exception:
        return jsonify(error=tr('Invalid data')), 400
    if len(changes) > 6000:
        return jsonify(error=tr('Too many changes in one save. Please save in smaller parts.')), 413
    if ward_id not in [w.id for w in my_wards()] or shift not in my_shifts() or wt not in my_works():
        return jsonify(error=tr('You do not have access to this ward / shift / work type')), 403
    emp_ids = {r[0] for r in db.session.query(Employee.id).filter_by(ward_id=ward_id)}
    lock, today = locked_before(), date.today()
    # one query for everything that already exists (instead of one query per cell)
    existing = {(r.employee_id, r.att_date): r for r in Attendance.query.filter(
        Attendance.ward_id == ward_id, Attendance.shift == shift,
        Attendance.att_date.between(date(y, m, 1), date(y, m, calendar.monthrange(y, m)[1])))}
    emp_ids |= {k[0] for k in existing}          # employees moved to another ward but still shown on this sheet
    can_add, can_edit, can_del = (current_user.can('attendance', a) for a in ('add', 'edit', 'delete'))
    saved = skipped = 0
    for ch in changes:
        try:
            eid, d = int(ch['emp']), date(y, m, int(ch['day']))
        except Exception:
            skipped += 1
            continue
        if eid not in emp_ids or d > today or (lock and d < lock):
            skipped += 1
            continue
        status = ch.get('s') or ''
        rec = existing.get((eid, d))
        if rec is None:          # may exist under another ward (employee moved) - check once, rarely
            rec = Attendance.query.filter_by(att_date=d, employee_id=eid, shift=shift).first()
        if rec and rec.work_type not in (None, wt):
            skipped += 1
            continue
        if not status:
            if rec and can_del:
                db.session.delete(rec)
                saved += 1
            else:
                skipped += 1
            continue
        if status not in STATUSES:
            skipped += 1
            continue
        if rec is None:
            if not can_add:
                skipped += 1
                continue
            rec = Attendance(att_date=d, employee_id=eid, shift=shift)
            db.session.add(rec)
        elif not can_edit:
            skipped += 1
            continue
        rec.ward_id, rec.status, rec.work_type = ward_id, status, wt
        rec.location = str(ch.get('loc') or '')[:150]
        rec.in_time = str(ch.get('time') or '')[:8]
        rec.remark = str(ch.get('rem') or '')[:200]
        rec.marked_by = current_user.username
        saved += 1
    try:
        db.session.commit()
    except IntegrityError:        # two people saved the same cell at the same moment
        db.session.rollback()
        return jsonify(error=tr('Someone else saved at the same time. Please reload the sheet and try again.')), 409
    audit('attendance-save', 'ward=%s shift=%s work=%s month=%04d-%02d saved=%d skipped=%d' % (ward_id, shift, wt, y, m, saved, skipped))
    return jsonify(saved=saved, skipped=skipped)


# ---------------------------------------------------------------- daily attendance (one date at a time)
def daily_args(src):
    wards, works, shifts = my_wards(), my_works(), my_shifts()
    d = parse_date(src.get('date'), date.today())
    ward_id = src.get('ward_id', type=int) if hasattr(src, 'getlist') else None
    shift = src.get('shift') or (shifts[0] if shifts else '')
    wt = src.get('work_type') or (works[0] if works else '')
    valid = ward_id in [w.id for w in wards] and shift in shifts and wt in works
    return dict(wards=wards, works=works, shifts=shifts, d=d, ward_id=ward_id, shift=shift, wt=wt, valid=valid)


def daily_emps(ward_id, shift, wt, d):
    emps = Employee.query.options(joinedload(Employee.vehicle), joinedload(Employee.route), joinedload(Employee.tracker)) \
        .filter_by(ward_id=ward_id, active=True, default_work=wt).order_by(Employee.name).all()
    recs = {r.employee_id: r for r in Attendance.query.filter(
        Attendance.ward_id == ward_id, Attendance.shift == shift, Attendance.att_date == d)}
    have = {e.id for e in emps}
    extra = [i for i, r in recs.items() if r.work_type == wt and i not in have]
    if extra:
        emps += Employee.query.options(joinedload(Employee.vehicle), joinedload(Employee.route), joinedload(Employee.tracker)) \
            .filter(Employee.id.in_(extra)).order_by(Employee.name).all()
    return emps, recs


@app.route('/attendance/daily', methods=['GET', 'POST'])
@perm('attendance', 'view')
def attendance_daily():
    src = request.form if request.method == 'POST' else request.args
    a = daily_args(src)
    lock, today = locked_before(), date.today()
    editable = a['valid'] and a['d'] <= today and not (lock and a['d'] < lock)
    if request.method == 'POST':
        if not a['valid']:
            flash(tr('You do not have access to this ward / shift / work type'), 'error')
        elif not editable:
            flash(tr('This date cannot be edited.'), 'error')
        else:
            emps, recs = daily_emps(a['ward_id'], a['shift'], a['wt'], a['d'])
            can_add, can_edit, can_del = (current_user.can('attendance', x) for x in ('add', 'edit', 'delete'))
            saved = skipped = 0
            for e in emps:
                if 's_%d' % e.id not in request.form:
                    continue
                status = request.form.get('s_%d' % e.id, '')
                loc = request.form.get('loc_%d' % e.id, '')[:150]
                tm = request.form.get('time_%d' % e.id, '')[:8]
                rem = request.form.get('rem_%d' % e.id, '')[:200]
                rec = recs.get(e.id)
                if rec is None and status:
                    rec = Attendance.query.filter_by(att_date=a['d'], employee_id=e.id, shift=a['shift']).first()
                    if rec is not None and rec.work_type not in (None, a['wt']):
                        skipped += 1
                        continue
                if not status:
                    if rec is not None:
                        if can_del:
                            db.session.delete(rec)
                            saved += 1
                        else:
                            skipped += 1
                    continue
                if status not in STATUSES:
                    skipped += 1
                    continue
                if rec is None:
                    if not can_add:
                        skipped += 1
                        continue
                    rec = Attendance(att_date=a['d'], employee_id=e.id, shift=a['shift'])
                    db.session.add(rec)
                elif not can_edit:
                    skipped += 1
                    continue
                elif (rec.status, rec.location or '', rec.in_time or '', rec.remark or '') == (status, loc, tm, rem):
                    continue                     # nothing changed
                rec.ward_id, rec.status, rec.work_type = a['ward_id'], status, a['wt']
                rec.location, rec.in_time, rec.remark, rec.marked_by = loc, tm, rem, current_user.username
                saved += 1
            try:
                db.session.commit()
            except IntegrityError:
                db.session.rollback()
                flash(tr('Someone else saved at the same time. Please reload the sheet and try again.'), 'error')
                return redirect(url_for('attendance_daily', date=a['d'].isoformat(), ward_id=a['ward_id'], shift=a['shift'], work_type=a['wt']))
            audit('attendance-save', 'daily ward=%s shift=%s work=%s date=%s saved=%d skipped=%d' % (
                a['ward_id'], a['shift'], a['wt'], a['d'].isoformat(), saved, skipped))
            flash(tr('Attendance saved.') + ' (%d)' % saved + ((' ' + tr('Skipped') + ': %d' % skipped) if skipped else ''), 'ok')
        return redirect(url_for('attendance_daily', date=a['d'].isoformat(), ward_id=a['ward_id'], shift=a['shift'], work_type=a['wt']))
    ctx = dict(a, loaded=False, editable=editable, date_s=a['d'].isoformat(), lock=lock.isoformat() if lock else '')
    if a['valid']:
        emps, recs = daily_emps(a['ward_id'], a['shift'], a['wt'], a['d'])
        hol = holiday_q().filter_by(hdate=a['d']).first()
        ids = {e.id for e in emps}
        counts = {st: sum(1 for r in recs.values() if r.status == st and r.employee_id in ids) for st in STATUSES}
        ctx.update(loaded=True, emps=emps, recs=recs, counts=counts, holiday=hol.name if hol else '',
                   sunday=a['d'].weekday() == 6, marked=sum(counts.values()),
                   can_view_emp=current_user.can('employees', 'view'),
                   prev=(a['d'] - timedelta(days=1)).isoformat(),
                   next=(a['d'] + timedelta(days=1)).isoformat() if a['d'] < today else '')
    return render_template('attendance_daily.html', **ctx)


@app.route('/attendance/export')
@perm('attendance', 'export')
def attendance_export():
    s = sheet_args()
    if not s['valid']:
        abort(403)
    emps, data = load_sheet(s['ward_id'], s['shift'], s['wt'], s['y'], s['m'], s['nd'])
    ward = db.session.get(Ward, s['ward_id'])
    wb = Workbook()
    ws = wb.active
    ws.title = 'Attendance'
    nd = s['nd']
    ws.append(['%s - %s' % (company_name(), tr('Attendance Register'))])
    ws.append(['%s: %s | %s: %s | %s: %s | %s: %s | %s: %s %d' % (
        tr('Zone'), ward.zone.name, tr('Ward'), ward.name, tr('Shift'), tr(s['shift']),
        tr('Work Type'), tr(s['wt']), tr('Month'), month_label(s['m']), s['y'])])
    ws.append([])
    head = [tr('S.No'), tr('Code'), tr('Name'), tr("Father's Name"), tr('Designation')] + \
           [d['d'] for d in s['days']] + \
           ['P', 'A', 'L', 'H', 'W', tr('Total Days')]
    ws.append(head)
    thin = Side(style='thin', color='BBBBBB')
    for i, c in enumerate(ws[4]):
        c.font = Font(bold=True, color='FFFFFF')
        c.alignment = Alignment(horizontal='center')
        sun = 5 <= i < 5 + nd and s['days'][i - 5]['sun']
        holi = 5 <= i < 5 + nd and bool(s['days'][i - 5]['hol'])
        c.fill = PatternFill('solid', fgColor='8E44AD' if holi else ('F7941D' if sun else '1F3A68'))
    ws['A1'].font = Font(bold=True, size=14)
    fills = {'P': 'C8E6C9', 'A': 'FFCDD2', 'L': 'E0E0E0', 'H': 'FFE0B2', 'W': 'BBDEFB'}
    rev = {v: k for k, v in CODES.items()}
    for n, e in enumerate(emps, 1):
        row = [n, e.code, e.name, e.father_name or '', desig_text(e)]
        cnt = {k: 0 for k in CODES}
        for d in range(1, nd + 1):
            r = data.get(str(e.id), {}).get(str(d))
            code = rev.get(r['s'], '') if r else ''
            if code:
                cnt[code] += 1
            row.append(code)
        row += [cnt['P'], cnt['A'], cnt['L'], cnt['H'], cnt['W'], cnt['P'] + cnt['H'] * 0.5]
        ws.append(row)
        for i in range(nd):
            c = ws.cell(row=ws.max_row, column=6 + i)
            c.alignment = Alignment(horizontal='center')
            if c.value in fills:
                c.fill = PatternFill('solid', fgColor=fills[c.value])
    for row in ws.iter_rows(min_row=4, max_row=ws.max_row):
        for c in row:
            c.border = Border(left=thin, right=thin, top=thin, bottom=thin)
    ws.column_dimensions['A'].width = 6
    ws.column_dimensions['B'].width = 12
    ws.column_dimensions['C'].width = 26
    ws.column_dimensions['D'].width = 22
    ws.column_dimensions['E'].width = 20
    for i in range(nd):
        ws.column_dimensions[ws.cell(row=4, column=6 + i).column_letter].width = 4.2
    for i in range(6):
        ws.column_dimensions[ws.cell(row=4, column=6 + nd + i).column_letter].width = 8
    ws.freeze_panes = 'D5'
    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)
    return send_file(buf, as_attachment=True,
                     download_name='attendance_%s_%s_%04d-%02d.xlsx' % (
                         safe_name(ward.name), safe_name(s['wt']), s['y'], s['m']),
                     mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')


# ---------------------------------------------------------------- reports
def report_query():
    a = request.args
    d1 = parse_date(a.get('from'), date.today().replace(day=1))
    d2 = parse_date(a.get('to'), date.today())
    q = scope_att(Attendance.query).join(Employee, Attendance.employee_id == Employee.id) \
        .filter(Attendance.att_date.between(d1, d2))
    if a.get('zone_id', type=int):
        q = q.filter(Employee.zone_id == a.get('zone_id', type=int))
    if a.get('ward_id', type=int):
        q = q.filter(Attendance.ward_id == a.get('ward_id', type=int))
    for key, col in (('shift', Attendance.shift), ('work_type', Attendance.work_type),
                     ('status', Attendance.status)):
        if a.get(key):
            q = q.filter(col == a[key])
    return d1, d2, q.order_by(Attendance.att_date, Employee.name)


EXPORT_ROW_LIMIT = 200000


@app.route('/reports')
@perm('reports', 'view')
def reports():
    d1, d2, q = report_query()
    if request.args.get('download'):
        if not current_user.can('reports', 'export'):
            abort(403)
        from openpyxl.cell import WriteOnlyCell
        wb = Workbook(write_only=True)          # streams rows to disk: big exports do not eat memory
        ws = wb.create_sheet('Attendance')
        for col, w in zip('ABCDEFGHIJKLM', [12, 12, 24, 22, 20, 16, 16, 8, 11, 15, 28, 9, 24]):
            ws.column_dimensions[col].width = w
        title = WriteOnlyCell(ws, value='%s - %s (%s - %s)' % (company_name(), tr('Attendance Report'), d1, d2))
        title.font = Font(bold=True, size=13)
        ws.append([title])
        head = []
        for h in ('Date', 'Emp Code', 'Name', "Father's Name", 'Designation', 'Zone', 'Ward', 'Shift', 'Status',
                  'Work Type', 'Location', 'In Time', 'Remark'):
            c = WriteOnlyCell(ws, value=tr(h))
            c.font = Font(bold=True, color='FFFFFF')
            c.fill = PatternFill('solid', fgColor='1F3A68')
            c.alignment = Alignment(horizontal='center')
            head.append(c)
        ws.append(head)
        n = 0
        for r in q.options(joinedload(Attendance.employee).joinedload(Employee.zone),
                      joinedload(Attendance.employee).joinedload(Employee.vehicle),
                      joinedload(Attendance.employee).joinedload(Employee.route), joinedload(Attendance.ward)) \
                  .yield_per(2000).limit(EXPORT_ROW_LIMIT):
            ws.append([r.att_date.strftime('%d-%m-%Y'), r.employee.code, r.employee.name,
                       r.employee.father_name or '', desig_text(r.employee),
                       r.employee.zone.name, r.ward.name, tr(r.shift), tr(r.status), tr(r.work_type or ''),
                       r.location, r.in_time, r.remark])
            n += 1
        buf = io.BytesIO()
        wb.save(buf)
        buf.seek(0)
        audit('export-report', '%s to %s rows=%d' % (d1, d2, n))
        return send_file(buf, as_attachment=True,
                         download_name='attendance_%s_to_%s.xlsx' % (d1, d2),
                         mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    # screen view: counts come from the database, rows are shown 100 per page
    counts = dict(q.order_by(None).with_entities(Attendance.status, func.count(Attendance.id)).group_by(Attendance.status).all())
    summary = {st: counts.get(st, 0) for st in STATUSES}
    total = sum(summary.values())
    per_page = 100
    pages = max(1, -(-total // per_page))
    page = min(max(request.args.get('page', 1, type=int), 1), pages)
    rows = q.options(joinedload(Attendance.employee).joinedload(Employee.zone),
                      joinedload(Attendance.employee).joinedload(Employee.vehicle),
                      joinedload(Attendance.employee).joinedload(Employee.route), joinedload(Attendance.ward)) \
            .offset((page - 1) * per_page).limit(per_page).all()
    shown = sorted({1, pages} | {p for p in range(page - 2, page + 3) if 1 <= p <= pages})
    window = []
    for p in shown:
        if window and p - window[-1] > 1:
            window.append(None)
        window.append(p)
    qs = {k: v for k, v in request.args.items() if k not in ('page', 'download') and v}
    pg = dict(page=page, pages=pages, total=total, window=window, per_page=per_page,
              first=(page - 1) * per_page + 1 if total else 0, last=min(page * per_page, total))
    return render_template('reports.html', rows=rows, d1=d1, d2=d2, summary=summary, pg=pg, qs=qs,
                           zones=my_zones(), wards=my_wards(), works=my_works(),
                           shifts=my_shifts(), a=request.args)


# ---------------------------------------------------------------- ward reports (daily / weekly / monthly)
REV_CODES = {v: k for k, v in CODES.items()}
REPORT_TITLES = {'daily': 'Daily Attendance Report', 'weekly': 'Weekly Attendance Report',
                 'monthly': 'Monthly Attendance Report'}


def ward_report_params():
    a = request.args
    wards, works, shifts = my_wards(), my_works(), my_shifts()
    rtype = a.get('type') if a.get('type') in REPORT_TITLES else 'daily'
    d = parse_date(a.get('date'), date.today())
    y, m, nd, _days = month_info(a.get('month') or d.strftime('%Y-%m'))
    if rtype == 'daily':
        start = end = d
    elif rtype == 'weekly':
        start = d - timedelta(days=d.weekday())
        end = start + timedelta(days=6)
    else:
        start, end = date(y, m, 1), date(y, m, nd)
    ward_sel = a.get('ward_id', 'all')
    sel_wards = wards if ward_sel in ('all', '') else [w for w in wards if str(w.id) == ward_sel]
    shift = a.get('shift', '')
    if shift not in shifts:
        shift = ''
    if rtype != 'daily' and not shift:
        shift = shifts[0] if shifts else ''       # grids need one specific shift
    wt = a.get('work_type', '')
    if wt not in works:
        wt = ''
    if start.month == end.month and start.year == end.year:
        month_text = '%s %d' % (month_label(start.month), start.year)
    else:
        month_text = '%s %d - %s %d' % (month_label(start.month), start.year, month_label(end.month), end.year)
    if rtype == 'daily':
        period_text = '%s (%s)' % (start.strftime('%d-%m-%Y'), day_label(start))
    elif rtype == 'weekly':
        period_text = '%s - %s' % (start.strftime('%d-%m-%Y'), end.strftime('%d-%m-%Y'))
    else:
        period_text = month_text
    hmap = {h.hdate: h.name for h in holiday_q().filter(Holiday.hdate.between(start, end))}
    days = [{'date': start + timedelta(days=i), 'num': (start + timedelta(days=i)).day,
             'label': day_label(start + timedelta(days=i)),
             'sun': (start + timedelta(days=i)).weekday() == 6,
             'hol': hmap.get(start + timedelta(days=i))} for i in range((end - start).days + 1)]
    return dict(rtype=rtype, date=d, start=start, end=end, month='%04d-%02d' % (y, m), wards=wards, works=works,
                shifts=shifts, ward_sel=ward_sel, sel_wards=sel_wards, shift=shift, wt=wt, days=days,
                month_text=month_text, period_text=period_text, title=tr(REPORT_TITLES[rtype]),
                valid=bool(sel_wards) and (rtype == 'daily' or bool(shift)))


def _emp_opts():
    return (joinedload(Employee.vehicle), joinedload(Employee.route), joinedload(Employee.tracker))


def ward_report_sections(p):
    """Every ward of the report with ONE employee query and ONE attendance query (not two per ward)."""
    wards = p['sel_wards']
    if not wards:
        return []
    ids = [w.id for w in wards]
    eq = scope_emp(Employee.query.options(*_emp_opts()).filter(Employee.ward_id.in_(ids), Employee.active.is_(True)))
    if p['wt']:
        eq = eq.filter(Employee.default_work == p['wt'])
    emps_by, pool = {}, {}
    for e in eq.order_by(Employee.name).all():
        emps_by.setdefault(e.ward_id, []).append(e)
        pool[e.id] = e
    q = scope_att(Attendance.query).filter(Attendance.ward_id.in_(ids), Attendance.att_date.between(p['start'], p['end']))
    if p['shift']:
        q = q.filter(Attendance.shift == p['shift'])
    if p['wt']:
        q = q.filter(Attendance.work_type == p['wt'])
    recs_by = {}
    for r in q.order_by(Attendance.att_date, Attendance.shift).all():
        recs_by.setdefault(r.ward_id, []).append(r)
    missing = {r.employee_id for lst in recs_by.values() for r in lst} - set(pool)
    if missing:
        pool.update({e.id: e for e in Employee.query.options(*_emp_opts()).filter(Employee.id.in_(missing)).all()})
    out = []
    for w in wards:
        recs = recs_by.get(w.id, [])
        emps = list(emps_by.get(w.id, []))
        here = {e.id for e in emps}
        emps += [pool[i] for i in {r.employee_id for r in recs} - here if i in pool]
        out.append(ward_report_section(w, p, emps, recs))
    return out


def ward_report_section(ward, p, emps=None, recs=None):
    if emps is None:                                  # single ward on its own (not used by the report page any more)
        sec = ward_report_sections(dict(p, sel_wards=[ward]))
        return sec[0]
    emps.sort(key=lambda e: e.name.lower())
    sec = dict(ward=ward, zone=ward.zone.name, emp_count=len(emps))
    if p['rtype'] == 'daily':
        by_emp = {}
        for r in recs:
            by_emp.setdefault(r.employee_id, []).append(r)
        rows = []
        for e in emps:
            rs = by_emp.get(e.id)
            if rs:
                for r in rs:
                    rows.append(dict(e=e, status=r.status, shift=r.shift, work=r.work_type or e.default_work,
                                     loc=r.location or '', time=r.in_time or '', rem=r.remark or ''))
            elif not p['shift'] or e.default_shift == p['shift']:
                rows.append(dict(e=e, status='Not Marked', shift=e.default_shift, work=e.default_work,
                                 loc='', time='', rem=''))
        summary = {st: sum(1 for r in rows if r['status'] == st) for st in STATUSES + ['Not Marked']}
        sec.update(rows=rows, summary=summary)
    else:
        by = {(r.employee_id, r.att_date): r for r in recs}
        rows = []
        for e in emps:
            cells, cnt = [], {k: 0 for k in CODES}
            for d in p['days']:
                r = by.get((e.id, d['date']))
                code = REV_CODES.get(r.status, '') if r else ''
                if code:
                    cnt[code] += 1
                cells.append(code)
            rows.append(dict(e=e, cells=cells, cnt=cnt, days=cnt['P'] + cnt['H'] * 0.5))
        foot = [sum(1 for row in rows if row['cells'][i] == 'P') for i in range(len(p['days']))]
        sec.update(rows=rows, foot=foot)
    return sec


def fmt_num(x):
    return '%g' % x


app.jinja_env.filters['num'] = fmt_num


@app.route('/ward-reports')
@perm('reports', 'view')
def ward_reports():
    p = ward_report_params()
    sections = []
    if 'type' in request.args and p['valid']:
        if len(p['sel_wards']) > 60:
            flash(tr('Only the first 60 wards are shown. Choose a single ward or zone to see the rest.'), 'error')
            p['sel_wards'] = p['sel_wards'][:60]
        sections = ward_report_sections(p)
        if request.args.get('download'):
            if not current_user.can('reports', 'export'):
                abort(403)
            audit('export-ward-report', '%s %s wards=%d' % (p['rtype'], p['start'], len(sections)))
            return ward_report_xlsx(p, sections)
    return render_template('ward_reports.html', p=p, sections=sections, shown='type' in request.args,
                           now=datetime.now().strftime('%d-%m-%Y %H:%M'))


def ward_report_xlsx(p, sections):
    wb = Workbook()
    wb.remove(wb.active)
    thin = Side(style='thin', color='BBBBBB')
    fills = {'P': 'C8E6C9', 'A': 'FFCDD2', 'L': 'E0E0E0', 'H': 'FFE0B2', 'W': 'BBDEFB'}
    st_fill = dict(zip(STATUSES + ['Not Marked'], ['C8E6C9', 'FFCDD2', 'E0E0E0', 'FFE0B2', 'BBDEFB', 'FFF59D']))
    used = set()
    for sec in sections:
        base = ''.join(ch if ch not in '\\/*?:[]' else '_' for ch in sec['ward'].name)[:28] or 'Ward'
        name, n = base, 1
        while name in used:
            n += 1
            name = '%s_%d' % (base[:26], n)
        used.add(name)
        ws = wb.create_sheet(name)
        rows = []
        ws.append([])
        ws.append([])
        ws.append([])
        ws['C1'] = company_name()
        ws['C1'].font = Font(bold=True, size=15, color='1F3A68')
        ws['C2'] = p['title']
        ws['C2'].font = Font(bold=True, size=12)
        ws['C3'] = '%s: %s | %s: %s | %s: %s | %s: %s | %s: %s | %s: %s' % (
            tr('Ward'), sec['ward'].name, tr('Zone'), sec['zone'], tr('Month'), p['month_text'],
            tr('Period'), p['period_text'], tr('Shift'), tr(p['shift']) if p['shift'] else tr('All Shifts'),
            tr('Work Type'), tr(p['wt']) if p['wt'] else tr('All Work Types'))
        for r in (1, 2, 3):
            ws.row_dimensions[r].height = 24
        try:
            from openpyxl.drawing.image import Image as XLImage
            img = XLImage(os.path.join(app.root_path, 'static', 'logo.png'))
            w0, h0 = img.width, img.height
            img.height, img.width = 64, int(64 * w0 / h0)
            ws.add_image(img, 'A1')
        except Exception:
            pass
        ws.append([])
        if p['rtype'] == 'daily':
            head = [tr(h) for h in ('S.No', 'Code', 'Name', "Father's Name", 'Designation', 'Shift', 'Work Type',
                                    'Status', 'Location', 'In Time', 'Remark')]
            ws.append(head)
            hr = ws.max_row
            for i, r in enumerate(sec['rows'], 1):
                e = r['e']
                ws.append([i, e.code, e.name, e.father_name or '', desig_text(e), tr(r['shift']),
                           tr(r['work']), tr(r['status']), r['loc'], r['time'], r['rem']])
                ws.cell(row=ws.max_row, column=8).fill = PatternFill('solid', fgColor=st_fill[r['status']])
            ws.append([])
            for st, cnt in sec['summary'].items():
                ws.append(['', '', tr(st), cnt])
                ws.cell(row=ws.max_row, column=3).font = Font(bold=True)
            ws.append(['', '', tr('Total Employees'), sec['emp_count']])
            ws.cell(row=ws.max_row, column=3).font = Font(bold=True)
            last_col = len(head)
            widths = [6, 12, 26, 22, 20, 9, 15, 14, 28, 9, 24]
        else:
            nd = len(p['days'])
            lab = [('%s\n%d' % (d['label'], d['num'])) if p['rtype'] == 'weekly' else d['num'] for d in p['days']]
            head = [tr('S.No'), tr('Code'), tr('Name'), tr("Father's Name"), tr('Designation')] + lab + \
                   ['P', 'A', 'L', 'H', 'W', tr('Total Days')]
            ws.append(head)
            hr = ws.max_row
            for i, r in enumerate(sec['rows'], 1):
                e, cnt = r['e'], r['cnt']
                ws.append([i, e.code, e.name, e.father_name or '', desig_text(e)] + r['cells'] +
                          [cnt['P'], cnt['A'], cnt['L'], cnt['H'], cnt['W'], r['days']])
                for j, code in enumerate(r['cells']):
                    c = ws.cell(row=ws.max_row, column=6 + j)
                    c.alignment = Alignment(horizontal='center')
                    if code in fills:
                        c.fill = PatternFill('solid', fgColor=fills[code])
            ws.append(['', '', tr('Present per day'), '', ''] + [x or '' for x in sec['foot']])
            for c in ws[ws.max_row]:
                c.font = Font(bold=True)
                c.fill = PatternFill('solid', fgColor='EEF2F9')
                c.alignment = Alignment(horizontal='center') if c.column > 5 else Alignment()
            last_col = len(head)
            widths = [6, 12, 26, 22, 20] + [(7 if p['rtype'] == 'weekly' else 4.2)] * nd + [7] * 5 + [11]
        for i, c in enumerate(ws[hr]):
            c.font = Font(bold=True, color='FFFFFF')
            c.alignment = Alignment(horizontal='center', vertical='center', wrap_text=True)
            sun = p['rtype'] != 'daily' and 5 <= i < 5 + len(p['days']) and p['days'][i - 5]['sun']
            holi = p['rtype'] != 'daily' and 5 <= i < 5 + len(p['days']) and bool(p['days'][i - 5]['hol'])
            c.fill = PatternFill('solid', fgColor='8E44AD' if holi else ('F7941D' if sun else '1F3A68'))
        if p['rtype'] == 'weekly':
            ws.row_dimensions[hr].height = 32
        for row in ws.iter_rows(min_row=hr, max_row=ws.max_row, max_col=last_col):
            for c in row:
                c.border = Border(left=thin, right=thin, top=thin, bottom=thin)
        ws.append([])
        ws.append([])
        ncols = 11 if p['rtype'] == 'daily' else 11 + len(p['days'])
        pos = [3, 6, 9] if p['rtype'] == 'daily' else [3, 6 + max(2, len(p['days']) // 3), ncols - 4]
        sign = [''] * (max(pos) + 2)
        for idx, label in zip(pos, ('Prepared By', 'Verified By', 'Authorised Signatory')):
            sign[idx - 1] = '%s: ____________' % tr(label)
        ws.append(sign)
        for i, w in enumerate(widths):
            ws.column_dimensions[ws.cell(row=hr, column=i + 1).column_letter].width = w
        ws.freeze_panes = ws.cell(row=hr + 1, column=4)
        ws.page_setup.orientation = 'landscape'
        ws.page_setup.paperSize = ws.PAPERSIZE_A4
        ws.page_setup.fitToWidth = 1
        ws.page_setup.fitToHeight = 0
        ws.sheet_properties.pageSetUpPr.fitToPage = True
        ws.print_title_rows = '%d:%d' % (hr, hr)
        ws.oddFooter.center.text = '&P / &N'
    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)
    who = 'All_Wards' if len(sections) > 1 else sections[0]['ward'].name.replace(' ', '_')
    return send_file(buf, as_attachment=True,
                     download_name='%s_report_%s_%s.xlsx' % (p['rtype'], who, p['start'].strftime('%Y-%m-%d')),
                     mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')


# ---------------------------------------------------------------- vehicle master
def crew_map(ids, only_active=True):
    """{vehicle_id: {'driver': [...], 'helper': [...], 'other': [...]}} - only employees the user may see."""
    out = {i: {'driver': [], 'helper': [], 'other': []} for i in ids}
    if not ids:
        return out
    q = scope_emp(Employee.query.options(joinedload(Employee.vehicle), joinedload(Employee.route)).filter(Employee.vehicle_id.in_(ids)))
    if only_active:
        q = q.filter(Employee.active.is_(True))
    for e in q.order_by(Employee.name):
        out[e.vehicle_id][role_of(e.designation) or 'other'].append(e)
    return out


def vehicle_input(f, v=None):
    """Validate + normalise the vehicle form. Returns (values, error)."""
    no = ' '.join((f.get('vehicle_no') or '').upper().split())
    if not VEH_RE.match(no):
        return None, tr('Enter a valid vehicle number (letters, numbers, space or hyphen, 3 to 20 characters).')
    try:
        zid = int(f.get('zone_id') or 0)
    except ValueError:
        zid = 0
    if zid not in [z.id for z in my_zones()]:
        return None, tr('Please select a zone.')
    ward = None
    if (f.get('ward_id') or '').strip():
        ward = next((w for w in my_wards() if str(w.id) == f['ward_id'].strip()), None)
        if ward is None or ward.zone_id != zid:
            return None, tr('The selected ward does not belong to the selected zone.')
    key = veh_key(no)
    if Vehicle.query.filter(Vehicle.vkey == key, Vehicle.id != (v.id if v else 0)).first():
        return None, tr('This vehicle number already exists.')
    return dict(vehicle_no=no, vkey=key, vehicle_type=(f.get('vehicle_type') or '').strip()[:40],
                zone_id=zid, ward_id=ward.id if ward else None, active=f.get('active', '1') == '1'), None


@app.route('/vehicles')
@perm('vehicles', 'view')
def vehicles():
    q = scope_vehicle(Vehicle.query)
    zone_id, ward_id = request.args.get('zone_id', type=int), request.args.get('ward_id', type=int)
    status, s = request.args.get('status', ''), request.args.get('q', '').strip()
    if zone_id:
        q = q.filter(Vehicle.zone_id == zone_id)
    if ward_id:
        q = q.filter(Vehicle.ward_id == ward_id)
    if status in ('active', 'inactive'):
        q = q.filter(Vehicle.active.is_(status == 'active'))
    if s:
        conds = [Vehicle.vehicle_type.like('%' + s + '%'), Vehicle.crew.any(Employee.name.like('%' + s + '%'))]
        if veh_key(s):
            conds.append(Vehicle.vkey.like('%' + veh_key(s) + '%'))
        q = q.filter(db.or_(*conds))
    pg = make_pg(q.count(), request.args.get('page', 1, type=int), 25)
    rows = q.options(joinedload(Vehicle.zone), joinedload(Vehicle.ward)).order_by(Vehicle.vkey) \
            .offset((pg['page'] - 1) * 25).limit(25).all()
    qs = {k: v for k, v in (('zone_id', zone_id), ('ward_id', ward_id), ('status', status), ('q', s)) if v}
    return render_template('vehicles.html', rows=rows, crew=crew_map([v.id for v in rows]), pg=pg, qs=qs,
                           zones=my_zones(), wards=my_wards(), zone_id=zone_id, ward_id=ward_id, status=status, s=s)


@app.route('/vehicles/add', methods=['GET', 'POST'])
@perm('vehicles', 'add')
def vehicle_add():
    if request.method == 'POST':
        vals, err = vehicle_input(request.form)
        if err:
            flash(err, 'error')
        else:
            v = Vehicle(**vals)
            db.session.add(v)
            try:
                db.session.commit()
            except IntegrityError:
                db.session.rollback()
                flash(tr('This vehicle number already exists.'), 'error')
                return render_template('vehicle_form.html', v=None, zones=my_zones(), wards=my_wards())
            audit('vehicle-add', v.vehicle_no)
            flash(tr('Vehicle added.'), 'ok')
            return redirect(url_for('vehicle_view', id=v.id))
    return render_template('vehicle_form.html', v=None, zones=my_zones(), wards=my_wards())


@app.route('/vehicles/<int:id>/edit', methods=['GET', 'POST'])
@perm('vehicles', 'edit')
def vehicle_edit(id):
    v = scope_vehicle(Vehicle.query.filter_by(id=id)).first() or abort(403)
    if request.method == 'POST':
        vals, err = vehicle_input(request.form, v)
        if err:
            flash(err, 'error')
        else:
            for k, val in vals.items():
                setattr(v, k, val)
            if v.zone_id and Employee.query.filter(Employee.vehicle_id == v.id, Employee.zone_id != v.zone_id).first():
                db.session.rollback()
                flash(tr('Some crew members belong to another zone. Remove them from the vehicle before changing its zone.'), 'error')
            else:
                try:
                    db.session.commit()
                except IntegrityError:
                    db.session.rollback()
                    flash(tr('This vehicle number already exists.'), 'error')
                    return redirect(url_for('vehicle_edit', id=id))
                audit('vehicle-update', v.vehicle_no)
                flash(tr('Vehicle updated.'), 'ok')
                return redirect(url_for('vehicle_view', id=v.id))
    return render_template('vehicle_form.html', v=v, zones=my_zones(), wards=my_wards())


@app.route('/vehicles/<int:id>')
@perm('vehicles', 'view')
def vehicle_view(id):
    v = scope_vehicle(Vehicle.query.filter_by(id=id)).first() or abort(403)
    crew = crew_map([v.id], only_active=False)[v.id]
    eligible = []
    if current_user.can('vehicles', 'edit'):
        eq = scope_emp(Employee.query.options(joinedload(Employee.vehicle), joinedload(Employee.route)).filter(
            Employee.active.is_(True), Employee.zone_id == v.zone_id,
            func.lower(Employee.designation).in_(CREW_ROLES),
            db.or_(Employee.vehicle_id.is_(None), Employee.vehicle_id != v.id)))
        eligible = eq.order_by(Employee.name).limit(500).all()
    return render_template('vehicle_view.html', v=v, crew=crew, eligible=eligible,
                           total_crew=sum(len(x) for x in crew.values()))


@app.route('/vehicles/<int:id>/assign', methods=['POST'])
@perm('vehicles', 'edit')
def vehicle_assign(id):
    v = scope_vehicle(Vehicle.query.filter_by(id=id)).first() or abort(403)
    e = scope_emp(Employee.query.filter_by(id=request.form.get('employee_id', type=int) or 0)).first()
    if e is None or not e.active or role_of(e.designation) is None or e.zone_id != v.zone_id:
        flash(tr('This employee cannot be assigned to this vehicle.'), 'error')
    else:
        e.vehicle_id = v.id
        db.session.commit()
        audit('vehicle-assign', '%s <- %s %s' % (v.vehicle_no, e.code, e.name))
        flash(tr('Assigned to the vehicle.'), 'ok')
    return redirect(url_for('vehicle_view', id=id))


@app.route('/vehicles/<int:id>/unassign/<int:emp_id>', methods=['POST'])
@perm('vehicles', 'edit')
def vehicle_unassign(id, emp_id):
    v = scope_vehicle(Vehicle.query.filter_by(id=id)).first() or abort(403)
    e = scope_emp(Employee.query.filter_by(id=emp_id, vehicle_id=v.id)).first() or abort(403)
    e.vehicle_id = None
    db.session.commit()
    audit('vehicle-unassign', '%s -> %s %s' % (v.vehicle_no, e.code, e.name))
    flash(tr('Removed from the vehicle.'), 'ok')
    return redirect(url_for('vehicle_view', id=id))


@app.route('/vehicles/<int:id>/delete', methods=['POST'])
@perm('vehicles', 'delete')
def vehicle_delete(id):
    v = scope_vehicle(Vehicle.query.filter_by(id=id)).first() or abort(403)
    if db.session.query(Employee.id).filter_by(vehicle_id=v.id).first():
        flash(tr('This vehicle still has crew assigned. Open the vehicle and remove them first.'), 'error')
        return redirect(url_for('vehicle_view', id=id))
    no = v.vehicle_no
    db.session.delete(v)
    db.session.commit()
    audit('vehicle-delete', no)
    flash(tr('Vehicle deleted.'), 'ok')
    return redirect(url_for('vehicles'))


# ---------------------------------------------------------------- tracker master
def tracker_input(f, t=None):
    no = ' '.join((f.get('tracker_no') or '').upper().split())
    if not re.match(r'^[A-Z0-9][A-Z0-9 \-/_]{0,29}$', no):
        return None, tr('Enter a valid tracker ID (letters, numbers, space or hyphen, up to 30 characters).')
    try:
        zid = int(f.get('zone_id') or 0)
    except ValueError:
        zid = 0
    if zid not in [z.id for z in my_zones()]:
        return None, tr('Please select a zone.')
    key = re.sub(r'[\s\-/_]+', '', no)
    if Tracker.query.filter(Tracker.tkey == key, Tracker.id != (t.id if t else 0)).first():
        return None, tr('This tracker ID already exists.')
    return dict(tracker_no=no, tkey=key, zone_id=zid, active=f.get('active', '1') == '1'), None


@app.route('/trackers')
@perm('trackers', 'view')
def trackers():
    q = scope_tracker(Tracker.query)
    zone_id, status, s = request.args.get('zone_id', type=int), request.args.get('status', ''), request.args.get('q', '').strip()
    if zone_id:
        q = q.filter(Tracker.zone_id == zone_id)
    if status in ('active', 'inactive'):
        q = q.filter(Tracker.active.is_(status == 'active'))
    if s:
        q = q.filter(db.or_(Tracker.tkey.like('%' + re.sub(r'[\s\-/_]+', '', s.upper()) + '%'),
                            Tracker.crew.any(Employee.name.like('%' + s + '%'))))
    pg = make_pg(q.count(), request.args.get('page', 1, type=int), 25)
    rows = q.options(joinedload(Tracker.zone), joinedload(Tracker.crew)).order_by(Tracker.tkey) \
            .offset((pg['page'] - 1) * 25).limit(25).all()
    qs = {k: v for k, v in (('zone_id', zone_id), ('status', status), ('q', s)) if v}
    return render_template('trackers.html', rows=rows, pg=pg, qs=qs, zones=my_zones(), zone_id=zone_id, status=status, s=s)


@app.route('/trackers/add', methods=['GET', 'POST'])
@perm('trackers', 'add')
def tracker_add():
    if request.method == 'POST':
        vals, err = tracker_input(request.form)
        if err:
            flash(err, 'error')
        else:
            t = Tracker(**vals)
            db.session.add(t)
            try:
                db.session.commit()
            except IntegrityError:
                db.session.rollback()
                flash(tr('This tracker ID already exists.'), 'error')
                return render_template('tracker_form.html', t=None, zones=my_zones())
            audit('tracker-add', t.tracker_no)
            flash(tr('Tracker added.'), 'ok')
            return redirect(url_for('tracker_view', id=t.id))
    return render_template('tracker_form.html', t=None, zones=my_zones())


@app.route('/trackers/<int:id>')
@perm('trackers', 'view')
def tracker_view(id):
    t = scope_tracker(Tracker.query.filter_by(id=id)).first() or abort(403)
    crew = scope_emp(Employee.query.options(joinedload(Employee.ward), joinedload(Employee.route), joinedload(Employee.vehicle))
                     .filter(Employee.tracker_id == t.id)).order_by(Employee.name).all()
    eligible = []
    if current_user.can('trackers', 'edit'):
        eq = scope_emp(Employee.query.options(joinedload(Employee.tracker)).filter(
            Employee.active.is_(True), Employee.zone_id == t.zone_id,
            func.lower(Employee.designation).in_(TRACKER_ROLES + ('trollyman', 'trolley man')),
            db.or_(Employee.tracker_id.is_(None), Employee.tracker_id != t.id)))
        eligible = eq.order_by(Employee.name).limit(500).all()
    return render_template('tracker_view.html', t=t, crew=crew, eligible=eligible)


@app.route('/trackers/<int:id>/assign', methods=['POST'])
@perm('trackers', 'edit')
def tracker_assign(id):
    t = scope_tracker(Tracker.query.filter_by(id=id)).first() or abort(403)
    e = scope_emp(Employee.query.filter_by(id=request.form.get('employee_id', type=int) or 0)).first()
    if e is None or not e.active or not has_tracker(e.designation) or e.zone_id != t.zone_id:
        flash(tr('This employee cannot be assigned to this tracker.'), 'error')
    elif not t.active:
        flash(tr('This tracker is inactive. Choose an active tracker.'), 'error')
    else:
        e.tracker_id = t.id
        db.session.commit()
        audit('tracker-assign', '%s <- %s %s' % (t.tracker_no, e.code, e.name))
        flash(tr('Assigned to the tracker.'), 'ok')
    return redirect(url_for('tracker_view', id=id))


@app.route('/trackers/<int:id>/unassign/<int:emp_id>', methods=['POST'])
@perm('trackers', 'edit')
def tracker_unassign(id, emp_id):
    t = scope_tracker(Tracker.query.filter_by(id=id)).first() or abort(403)
    e = scope_emp(Employee.query.filter_by(id=emp_id, tracker_id=t.id)).first() or abort(403)
    e.tracker_id = None
    db.session.commit()
    audit('tracker-unassign', '%s -> %s %s' % (t.tracker_no, e.code, e.name))
    flash(tr('Removed from the tracker.'), 'ok')
    return redirect(url_for('tracker_view', id=id))


@app.route('/trackers/<int:id>/edit', methods=['GET', 'POST'])
@perm('trackers', 'edit')
def tracker_edit(id):
    t = scope_tracker(Tracker.query.filter_by(id=id)).first() or abort(403)
    if request.method == 'POST':
        vals, err = tracker_input(request.form, t)
        if err:
            flash(err, 'error')
        elif vals['zone_id'] != t.zone_id and Employee.query.filter(Employee.tracker_id == t.id, Employee.zone_id != vals['zone_id']).first():
            flash(tr('Some trolleymen belong to another zone. Remove them from the tracker before changing its zone.'), 'error')
        else:
            for k, val in vals.items():
                setattr(t, k, val)
            try:
                db.session.commit()
            except IntegrityError:
                db.session.rollback()
                flash(tr('This tracker ID already exists.'), 'error')
                return redirect(url_for('tracker_edit', id=id))
            audit('tracker-update', t.tracker_no)
            flash(tr('Tracker updated.'), 'ok')
            return redirect(url_for('tracker_view', id=t.id))
    return render_template('tracker_form.html', t=t, zones=my_zones())


@app.route('/trackers/<int:id>/delete', methods=['POST'])
@perm('trackers', 'delete')
def tracker_delete(id):
    t = scope_tracker(Tracker.query.filter_by(id=id)).first() or abort(403)
    if db.session.query(Employee.id).filter_by(tracker_id=t.id).first():
        flash(tr('This tracker is still assigned to employees. Change their Tracker ID first.'), 'error')
        return redirect(url_for('tracker_view', id=id))
    no = t.tracker_no
    db.session.delete(t)
    db.session.commit()
    audit('tracker-delete', no)
    flash(tr('Tracker deleted.'), 'ok')
    return redirect(url_for('trackers'))


# ---------------------------------------------------------------- route master (same idea as routes)
def route_crew_map(ids, only_active=True):
    """{route_id: {'driver': [...], 'helper': [...], 'other': [...]}} - only employees the user may see."""
    out = {i: {'driver': [], 'helper': [], 'other': []} for i in ids}
    if not ids:
        return out
    q = scope_emp(Employee.query.options(joinedload(Employee.vehicle), joinedload(Employee.route)).filter(Employee.route_id.in_(ids)))
    if only_active:
        q = q.filter(Employee.active.is_(True))
    for e in q.order_by(Employee.name):
        out[e.route_id][role_of(e.designation) or 'other'].append(e)
    return out


def route_input(f, v=None):
    """Validate + normalise the route form. Returns (values, error)."""
    no = ' '.join((f.get('route_no') or '').upper().split())
    if not ROUTE_RE.match(no):
        return None, tr('Enter a valid Route ID (letters, numbers, space, hyphen or slash, up to 20 characters).')
    try:
        zid = int(f.get('zone_id') or 0)
    except ValueError:
        zid = 0
    if zid not in [z.id for z in my_zones()]:
        return None, tr('Please select a zone.')
    ward = None
    if (f.get('ward_id') or '').strip():
        ward = next((w for w in my_wards() if str(w.id) == f['ward_id'].strip()), None)
        if ward is None or ward.zone_id != zid:
            return None, tr('The selected ward does not belong to the selected zone.')
    key = route_key(no)
    if Route.query.filter(Route.project_id == cur_pid(), Route.rkey == key, Route.id != (v.id if v else 0)).first():
        return None, tr('This Route ID already exists.')
    return dict(route_no=no, rkey=key, route_name=(f.get('route_name') or '').strip()[:80],
                zone_id=zid, ward_id=ward.id if ward else None, active=f.get('active', '1') == '1'), None


@app.route('/routes')
@perm('routes', 'view')
def routes():
    q = scope_route(Route.query)
    zone_id, ward_id = request.args.get('zone_id', type=int), request.args.get('ward_id', type=int)
    status, s = request.args.get('status', ''), request.args.get('q', '').strip()
    if zone_id:
        q = q.filter(Route.zone_id == zone_id)
    if ward_id:
        q = q.filter(Route.ward_id == ward_id)
    if status in ('active', 'inactive'):
        q = q.filter(Route.active.is_(status == 'active'))
    if s:
        conds = [Route.route_name.like('%' + s + '%'), Route.crew.any(Employee.name.like('%' + s + '%'))]
        if route_key(s):
            conds.append(Route.rkey.like('%' + route_key(s) + '%'))
        q = q.filter(db.or_(*conds))
    pg = make_pg(q.count(), request.args.get('page', 1, type=int), 25)
    rows = q.options(joinedload(Route.zone), joinedload(Route.ward)).order_by(Route.rkey) \
            .offset((pg['page'] - 1) * 25).limit(25).all()
    qs = {k: v for k, v in (('zone_id', zone_id), ('ward_id', ward_id), ('status', status), ('q', s)) if v}
    return render_template('routes.html', rows=rows, crew=route_crew_map([v.id for v in rows]), pg=pg, qs=qs,
                           zones=my_zones(), wards=my_wards(), zone_id=zone_id, ward_id=ward_id, status=status, s=s)


@app.route('/routes/add', methods=['GET', 'POST'])
@perm('routes', 'add')
def route_add():
    if request.method == 'POST':
        vals, err = route_input(request.form)
        if err:
            flash(err, 'error')
        else:
            v = Route(**vals)
            db.session.add(v)
            try:
                db.session.commit()
            except IntegrityError:
                db.session.rollback()
                flash(tr('This Route ID already exists.'), 'error')
                return render_template('route_form.html', v=None, zones=my_zones(), wards=my_wards())
            audit('route-add', v.route_no)
            flash(tr('Route added.'), 'ok')
            return redirect(url_for('route_view', id=v.id))
    return render_template('route_form.html', v=None, zones=my_zones(), wards=my_wards())


@app.route('/routes/<int:id>/edit', methods=['GET', 'POST'])
@perm('routes', 'edit')
def route_edit(id):
    v = scope_route(Route.query.filter_by(id=id)).first() or abort(403)
    if request.method == 'POST':
        vals, err = route_input(request.form, v)
        if err:
            flash(err, 'error')
        else:
            for k, val in vals.items():
                setattr(v, k, val)
            if v.zone_id and Employee.query.filter(Employee.route_id == v.id, Employee.zone_id != v.zone_id).first():
                db.session.rollback()
                flash(tr('Some crew members belong to another zone. Remove them from the route before changing its zone.'), 'error')
            else:
                try:
                    db.session.commit()
                except IntegrityError:
                    db.session.rollback()
                    flash(tr('This Route ID already exists.'), 'error')
                    return redirect(url_for('route_edit', id=id))
                audit('route-update', v.route_no)
                flash(tr('Route updated.'), 'ok')
                return redirect(url_for('route_view', id=v.id))
    return render_template('route_form.html', v=v, zones=my_zones(), wards=my_wards())


@app.route('/routes/<int:id>')
@perm('routes', 'view')
def route_view(id):
    v = scope_route(Route.query.filter_by(id=id)).first() or abort(403)
    crew = route_crew_map([v.id], only_active=False)[v.id]
    eligible = []
    if current_user.can('routes', 'edit'):
        eq = scope_emp(Employee.query.options(joinedload(Employee.vehicle), joinedload(Employee.route)).filter(
            Employee.active.is_(True), Employee.zone_id == v.zone_id,
            func.lower(Employee.designation).in_(ROUTE_ROLES + ('trollyman',)),
            db.or_(Employee.route_id.is_(None), Employee.route_id != v.id)))
        eligible = eq.order_by(Employee.name).limit(500).all()
    return render_template('route_view.html', v=v, crew=crew, eligible=eligible,
                           total_crew=sum(len(x) for x in crew.values()))


@app.route('/routes/<int:id>/assign', methods=['POST'])
@perm('routes', 'edit')
def route_assign(id):
    v = scope_route(Route.query.filter_by(id=id)).first() or abort(403)
    e = scope_emp(Employee.query.filter_by(id=request.form.get('employee_id', type=int) or 0)).first()
    if e is None or not e.active or not has_route(e.designation) or e.zone_id != v.zone_id:
        flash(tr('This employee cannot be assigned to this route.'), 'error')
    else:
        e.route_id = v.id
        db.session.commit()
        audit('route-assign', '%s <- %s %s' % (v.route_no, e.code, e.name))
        flash(tr('Assigned to the route.'), 'ok')
    return redirect(url_for('route_view', id=id))


@app.route('/routes/<int:id>/unassign/<int:emp_id>', methods=['POST'])
@perm('routes', 'edit')
def route_unassign(id, emp_id):
    v = scope_route(Route.query.filter_by(id=id)).first() or abort(403)
    e = scope_emp(Employee.query.filter_by(id=emp_id, route_id=v.id)).first() or abort(403)
    e.route_id = None
    db.session.commit()
    audit('route-unassign', '%s -> %s %s' % (v.route_no, e.code, e.name))
    flash(tr('Removed from the route.'), 'ok')
    return redirect(url_for('route_view', id=id))


@app.route('/routes/<int:id>/delete', methods=['POST'])
@perm('routes', 'delete')
def route_delete(id):
    v = scope_route(Route.query.filter_by(id=id)).first() or abort(403)
    if db.session.query(Employee.id).filter_by(route_id=v.id).first():
        flash(tr('This route still has crew assigned. Open the route and remove them first.'), 'error')
        return redirect(url_for('route_view', id=id))
    no = v.route_no
    db.session.delete(v)
    db.session.commit()
    audit('route-delete', no)
    flash(tr('Route deleted.'), 'ok')
    return redirect(url_for('routes'))


@app.route('/audit')
@super_only
def audit_log():
    q = AuditLog.query.filter(db.or_(AuditLog.project_id == cur_pid(), AuditLog.project_id.is_(None)))
    user, action = request.args.get('user', '').strip(), request.args.get('action', '').strip()
    if user:
        q = q.filter(AuditLog.username == user)
    if action:
        q = q.filter(AuditLog.action == action)
    total = q.count()
    per_page = 50
    pages = max(1, -(-total // per_page))
    page = min(max(request.args.get('page', 1, type=int), 1), pages)
    rows = q.order_by(AuditLog.id.desc()).offset((page - 1) * per_page).limit(per_page).all()
    actions = [r[0] for r in db.session.query(AuditLog.action).distinct().order_by(AuditLog.action)]
    qs = {k: v for k, v in (('user', user), ('action', action)) if v}
    return render_template('audit.html', rows=rows, page=page, pages=pages, total=total, qs=qs, actions=actions,
                           user=user, action=action, offset=(page - 1) * per_page)


# ---------------------------------------------------------------- users
def save_access(u, f):
    pids = {int(x) for x in f.getlist('project') if x.isdigit()} & {p.id for p in Project.query.all()}
    UserProject.query.filter_by(user_id=u.id).delete()
    for pid in pids:
        db.session.add(UserProject(user_id=u.id, project_id=pid))
    Permission.query.filter_by(user_id=u.id).delete()
    for m, _ in MODULES:
        p = Permission(user_id=u.id, module=m)
        for act in ACTIONS:
            setattr(p, 'can_' + act, ('perm_%s_%s' % (m, act)) in f)
        db.session.add(p)
    UserScope.query.filter_by(user_id=u.id).delete()
    for kind, field, universe in (('zones', 'zone', [str(z.id) for z in Zone.query.all()]),
                                  ('wards', 'ward', [str(w.id) for w in Ward.query.all()]),
                                  ('works', 'work', WORK_TYPES), ('shifts', 'shift', SHIFTS)):
        every = f.get('all_' + kind) == '1'
        setattr(u, 'all_' + kind, every)
        if not every:
            for v in f.getlist(field):
                if v in universe:
                    db.session.add(UserScope(user_id=u.id, kind=kind, value=v))
    try:
        u.backdate_days = int(f['backdate_days']) if f.get('backdate_days', '').strip() else None
    except ValueError:
        u.backdate_days = None


def user_form_ctx(u):
    return dict(u=u, zones=Zone.query.join(Project, Zone.project_id == Project.id).order_by(Project.name, Zone.name).all(),
                projects=Project.query.order_by(Project.name).all(), my_pids=u.project_ids if u else set(),
                sel={k: {s.value for s in u.scopes if s.kind == k} for k in ('zones', 'wards', 'works', 'shifts')} if u else
                {'zones': set(), 'wards': set(), 'works': set(), 'shifts': set()})


@app.route('/users')
@super_only
def users():
    return render_template('users.html', rows=User.query.order_by(User.username).all(),
                           project_names={p.id: p.name for p in Project.query.all()})


@app.route('/users/add', methods=['GET', 'POST'])
@super_only
def user_add():
    if request.method == 'POST':
        f = request.form
        uname, fname = f.get('username', '').strip()[:50], f.get('full_name', '').strip()[:100]
        if not uname or not fname:
            flash(tr('Username and full name are required.'), 'error')
        elif User.query.filter_by(username=uname).first():
            flash(tr('This username already exists.'), 'error')
        elif f.get('role') != 'super_admin' and not f.getlist('project'):
            flash(tr('Please select at least one project for this user.'), 'error')
        elif not valid_password(f.get('password', '')):
            flash(tr(PW_RULE), 'error')
        else:
            u = User(username=uname, full_name=fname,
                     password_hash=generate_password_hash(f['password']),
                     role='super_admin' if f.get('role') == 'super_admin' else 'user', is_active_user=f.get('active') == '1',
                     must_change=f.get('must_change') == '1')
            db.session.add(u)
            db.session.flush()
            save_access(u, f)
            db.session.commit()
            audit('user-create', 'user=' + u.username)
            flash(tr('User created.'), 'ok')
            return redirect(url_for('users'))
    return render_template('user_form.html', **user_form_ctx(None))


@app.route('/users/<int:id>/edit', methods=['GET', 'POST'])
@super_only
def user_edit(id):
    u = db.session.get(User, id) or abort(404)
    if request.method == 'POST':
        f = request.form
        u.full_name = f.get('full_name', '').strip()[:100] or u.full_name
        if u.id != current_user.id:
            u.role = 'super_admin' if f.get('role') == 'super_admin' else 'user'
            u.is_active_user = f.get('active') == '1'
        if not u.is_super and not f.getlist('project'):
            db.session.rollback()
            flash(tr('Please select at least one project for this user.'), 'error')
            return render_template('user_form.html', **user_form_ctx(u))
        if f.get('password'):
            if not valid_password(f['password']):
                db.session.rollback()
                flash(tr(PW_RULE), 'error')
                return render_template('user_form.html', **user_form_ctx(u))
            u.password_hash = generate_password_hash(f['password'])
        save_access(u, f)
        db.session.commit()
        audit('user-update', 'user=' + u.username)
        flash(tr('User updated.'), 'ok')
        return redirect(url_for('users'))
    return render_template('user_form.html', **user_form_ctx(u))


@app.route('/users/<int:id>/reset-password', methods=['GET', 'POST'])
@super_only
def user_reset_password(id):
    u = db.session.get(User, id) or abort(404)
    if request.method == 'POST':
        f = request.form
        if not valid_password(f.get('new', '')):
            flash(tr(PW_RULE), 'error')
        elif f['new'] != f.get('confirm', ''):
            flash(tr('New password and confirmation do not match.'), 'error')
        else:
            u.password_hash = generate_password_hash(f['new'])
            u.must_change = f.get('must_change') == '1'
            db.session.commit()
            audit('password-reset', 'user=' + u.username)
            flash(tr('Password reset successfully for user:') + ' ' + u.username, 'ok')
            return redirect(url_for('users'))
    return render_template('reset_password.html', u=u)


@app.route('/users/<int:id>/delete', methods=['POST'])
@super_only
def user_delete(id):
    u = db.session.get(User, id) or abort(404)
    if u.id == current_user.id:
        flash(tr('You cannot delete your own account.'), 'error')
    else:
        db.session.delete(u)
        db.session.commit()
        audit('user-delete', 'user=' + u.username)
        flash(tr('User deleted.'), 'ok')
    return redirect(url_for('users'))


# ---------------------------------------------------------------- search boxes (vehicle / route / tracker)
LOOKUP_LIMIT = 30
LOOKUPS = {
    'vehicle': (Vehicle, 'vkey', 'vehicles', veh_key, scope_vehicle),
    'route': (Route, 'rkey', 'routes', route_key, scope_route),
    'tracker': (Tracker, 'tkey', 'trackers', lambda n: re.sub(r'[\s\-/_]+', '', (n or '').upper()), scope_tracker),
}


def lookup_label(kind, o):
    if kind == 'vehicle':
        return o.vehicle_no + (' (%s)' % o.vehicle_type if o.vehicle_type else '')
    if kind == 'route':
        return o.route_no + (' (%s)' % o.route_name if o.route_name else '')
    return o.tracker_no


@app.route('/lookup/<kind>')
@login_required
def lookup(kind):
    """Type a few digits / letters, get at most 30 matching active vehicles / routes / trackers of the user's project,
    zone and ward scope (best matches - those that START with the text - first)."""
    spec = LOOKUPS.get(kind) or abort(404)
    model, keycol, module, keyfn, scope = spec
    if not current_user.can(module, 'view'):
        abort(403)
    col = getattr(model, keycol)
    q = scope(model.query.filter(model.active.is_(True)))
    zid = request.args.get('zone_id', type=int)
    if zid:
        q = q.filter(model.zone_id == zid)
    key = keyfn(request.args.get('q', '')[:40])
    if key:
        q = q.filter(col.contains(key, autoescape=True)).order_by(db.case((col.startswith(key, autoescape=True), 0), else_=1), col)
    else:
        q = q.order_by(col)
    rows = q.options(joinedload(model.zone)).limit(LOOKUP_LIMIT + 1).all()
    return jsonify(items=[dict(id=o.id, label=lookup_label(kind, o), zone=o.zone_id, sub=o.zone.name)
                          for o in rows[:LOOKUP_LIMIT]], more=len(rows) > LOOKUP_LIMIT)


# ---------------------------------------------------------------- projects
@app.route('/projects', methods=['GET', 'POST'])
@super_only
def projects():
    edit = None
    if request.method == 'POST':
        f = request.form
        pid = f.get('id', type=int)
        name = ' '.join(f.get('name', '').split())[:60]
        prefix = re.sub(r'[^A-Z0-9]', '', f.get('code_prefix', '').upper())[:8] or ('LE' + name[:1].upper())
        active = f.get('active', '1') == '1'
        if not name:
            flash(tr('Please enter the project name.'), 'error')
        elif Project.query.filter(func.lower(Project.name) == name.lower(), Project.id != (pid or 0)).first():
            flash(tr('This project already exists.'), 'error')
        elif pid:
            p = db.session.get(Project, pid) or abort(404)
            if not active and not Project.query.filter(Project.active.is_(True), Project.id != p.id).first():
                flash(tr('At least one project must stay active.'), 'error')
            else:
                p.name, p.code_prefix, p.active = name, prefix, active
                db.session.commit()
                audit('project-update', 'project=' + name)
                flash(tr('Project updated.'), 'ok')
        else:
            db.session.add(Project(name=name, code_prefix=prefix, active=active))
            db.session.commit()
            audit('project-create', 'project=' + name)
            flash(tr('Project added.'), 'ok')
        return redirect(url_for('projects'))
    rows = Project.query.order_by(Project.name).all()
    if request.args.get('edit', type=int):
        edit = next((p for p in rows if p.id == request.args.get('edit', type=int)), None)
    info = {}
    for p in rows:
        zids = [z[0] for z in db.session.query(Zone.id).filter(Zone.project_id == p.id)]
        info[p.id] = dict(zones=len(zids),
                          wards=db.session.query(func.count(Ward.id)).filter(Ward.zone_id.in_(zids or [0])).scalar(),
                          emps=db.session.query(func.count(Employee.id)).filter(Employee.zone_id.in_(zids or [0])).scalar(),
                          users=UserProject.query.filter_by(project_id=p.id).count())
    return render_template('projects.html', rows=rows, edit=edit, info=info,
                           admins=User.query.filter_by(role='super_admin').count())


@app.route('/projects/<int:id>/delete', methods=['POST'])
@super_only
def project_delete(id):
    p = db.session.get(Project, id) or abort(404)
    if Project.query.count() <= 1:
        flash(tr('The last project cannot be deleted.'), 'error')
    elif Zone.query.filter_by(project_id=p.id).first():
        flash(tr('This project has data (zones). Delete its zones, wards and employees first.'), 'error')
    else:
        name = p.name
        UserProject.query.filter_by(project_id=p.id).delete()
        Holiday.query.filter_by(project_id=p.id).delete()
        Route.query.filter_by(project_id=p.id).delete()
        db.session.delete(p)
        db.session.commit()
        audit('project-delete', 'project=' + name)
        flash(tr('Project deleted.'), 'ok')
    return redirect(url_for('projects'))


# ---------------------------------------------------------------- setup / auto-migrate
def _default_sql(col, dialect):
    """SQL literal of a column's plain Python default, or None."""
    d = col.default
    if d is None or not getattr(d, 'is_scalar', False) or d.arg is None:
        return None
    return str(expression.literal(d.arg, col.type).compile(dialect=dialect, compile_kwargs={'literal_binds': True}))


def add_missing_columns():
    """Upgrade an older database: add every column that the models have but the table does not
    (create_all() only creates missing TABLES).  Safe to run on every start."""
    insp = inspect(db.engine)
    dialect = db.engine.dialect
    quote = dialect.identifier_preparer.quote
    tables = set(insp.get_table_names())
    for table in db.metadata.sorted_tables:
        if table.name not in tables:
            continue
        have = {c['name'] for c in insp.get_columns(table.name)}
        for col in table.columns:
            if col.name in have:
                continue
            ddl = 'ALTER TABLE %s ADD COLUMN %s %s' % (quote(table.name), quote(col.name), col.type.compile(dialect=dialect))
            dflt = _default_sql(col, dialect)
            if dflt is not None:
                ddl += ' DEFAULT ' + dflt
            try:
                db.session.execute(text(ddl))
                db.session.commit()
                app.logger.warning('Database upgrade: added column %s.%s', table.name, col.name)
            except SQLAlchemyError:          # another worker added it a moment ago
                db.session.rollback()
    backfill_keys()


def backfill_keys():
    """Rows that existed before the unique *key* columns were added: fill the key from the visible number."""
    for table, src, key, fn in (('vehicle', 'vehicle_no', 'vkey', veh_key), ('route', 'route_no', 'rkey', route_key),
                                ('tracker', 'tracker_no', 'tkey', lambda n: re.sub(r'[\s\-/_]+', '', (n or '').upper()))):
        try:
            rows = db.session.execute(text('SELECT id, %s FROM %s WHERE %s IS NULL' % (src, table, key))).fetchall()
            for rid, no in rows:
                db.session.execute(text('UPDATE %s SET %s = :k WHERE id = :i' % (table, key)), {'k': fn(no) or 'ID%s' % rid, 'i': rid})
            db.session.commit()
        except SQLAlchemyError:
            db.session.rollback()


def add_missing_indexes():
    """create_all() does not add indexes to tables that already exist (upgrades) - do it here."""
    insp = inspect(db.engine)
    for table in db.metadata.sorted_tables:
        have = {i['name'] for i in insp.get_indexes(table.name)}
        for idx in table.indexes:
            if idx.name and idx.name not in have:
                try:
                    idx.create(db.engine)
                except SQLAlchemyError:
                    app.logger.warning('could not create index %s', idx.name)


def seed_route_master_if_empty():
    """Restore the bundled Route Master seed into the active DATA_DIR database if routes are missing.
    This fixes deployments where the app is launched against a different/older attendance.db.
    Existing route records are never overwritten.
    """
    try:
        pid = _FIRST_PID[0]
        if Route.query.filter_by(project_id=pid).count():
            return
        seed_path = os.path.join(BASE_DIR, 'route_master_seed.json')
        if not os.path.isfile(seed_path):
            app.logger.error('Route Master seed file missing: %s', seed_path)
            return
        with open(seed_path, encoding='utf-8') as fh:
            records = json.load(fh)
        inserted = 0
        for item in records:
            # Find the zone and ward by their names, not by database-specific numeric IDs.
            zone = Zone.query.filter(Zone.name == item['zone_name'], Zone.project_id == pid).first()
            ward = Ward.query.join(Zone).filter(Ward.name == item['ward_name'], Zone.project_id == pid).first()
            if ward:
                zone = db.session.get(Zone, ward.zone_id)
            if not zone or (item.get('ward_name') and not ward):
                app.logger.warning('Skipped route seed %s: zone/ward not found', item.get('route_no'))
                continue
            key = item['rkey']
            if Route.query.filter_by(rkey=key, project_id=pid).first():
                continue
            db.session.add(Route(project_id=pid, route_no=item['route_no'], rkey=key,
                               route_name=item.get('route_name') or 'n/a',
                               zone_id=zone.id, ward_id=ward.id if ward else None,
                               active=bool(item.get('active', True))))
            inserted += 1
        db.session.commit()
        app.logger.warning('Route Master startup repair inserted %s routes into %s', inserted, DB_URL)
    except Exception:
        db.session.rollback()
        app.logger.exception('Route Master startup repair failed')

def ensure_projects():
    """First start after the upgrade: create the default project (Lucknow) and give it all existing data and users."""
    first_run = Project.query.first() is None
    if first_run:
        try:
            db.session.add(Project(name='Lucknow', code_prefix='LEL', active=True))
            db.session.commit()
        except IntegrityError:                   # two workers started at the same time
            db.session.rollback()
    p = Project.query.order_by(Project.id).first()
    _FIRST_PID[0] = p.id
    for table in ('zone', 'holiday', 'route') + (('audit_log',) if first_run else ()):
        db.session.execute(text('UPDATE %s SET project_id = :p WHERE project_id IS NULL' % table), {'p': p.id})
    if not UserProject.query.first():
        for u in User.query.filter(User.role != 'super_admin').all():
            db.session.add(UserProject(user_id=u.id, project_id=p.id))
    db.session.commit()


def _sqlite_rebuild(table):
    """SQLite cannot drop a UNIQUE constraint: copy the table into a new one that follows the model."""
    tmp = table.name + '__new'
    old_cols = {r[1] for r in db.session.execute(text('PRAGMA table_info("%s")' % table.name))}
    db.session.commit()
    cols = ', '.join('"%s"' % c.name for c in table.columns if c.name in old_cols)
    raw = db.engine.raw_connection()
    drv = getattr(raw, 'driver_connection', None) or raw.connection
    saved = drv.isolation_level
    try:
        drv.isolation_level = None                # we control the transaction ourselves
        cur = raw.cursor()
        fk = cur.execute('PRAGMA foreign_keys').fetchone()[0]
        cur.execute('PRAGMA foreign_keys=OFF')
        cur.execute('BEGIN')
        try:
            t2 = table.to_metadata(db.metadata, name=tmp)
            db.metadata.remove(t2)
            cur.execute('DROP TABLE IF EXISTS "%s"' % tmp)
            cur.execute(str(CreateTable(t2).compile(dialect=db.engine.dialect)))
            cur.execute('INSERT INTO "%s" (%s) SELECT %s FROM "%s"' % (tmp, cols, cols, table.name))
            cur.execute('DROP TABLE "%s"' % table.name)
            cur.execute('ALTER TABLE "%s" RENAME TO "%s"' % (tmp, table.name))
            cur.execute('COMMIT')
        except Exception:
            cur.execute('ROLLBACK')
            raise
        finally:
            cur.execute('PRAGMA foreign_keys=%d' % fk)
    finally:
        drv.isolation_level = saved
        raw.close()
    for idx in table.indexes:
        try:
            idx.create(db.engine, checkfirst=True)
        except SQLAlchemyError:
            pass
    app.logger.warning('Database upgrade: rebuilt table %s (unique per project)', table.name)


def migrate_unique_constraints():
    """Zone name, Route ID and Holiday date were unique for the whole database; they are now unique per project."""
    if db.engine.dialect.name != 'sqlite':
        return                                    # MySQL / PostgreSQL: see README (drop the old unique key by hand)
    insp = inspect(db.engine)
    for table, col in ((Zone.__table__, 'name'), (Route.__table__, 'rkey')):
        old = [u for u in insp.get_unique_constraints(table.name) if u['column_names'] == [col]]
        old += [i for i in insp.get_indexes(table.name) if i.get('unique') and i['column_names'] == [col]]
        if old:
            _sqlite_rebuild(table)
    idx = {i['name']: i for i in insp.get_indexes('holiday')}
    uq = {u['name'] for u in insp.get_unique_constraints('holiday')}
    if idx.get('ix_holiday_hdate', {}).get('unique'):
        db.session.execute(text('DROP INDEX ix_holiday_hdate'))
        db.session.execute(text('CREATE INDEX ix_holiday_hdate ON holiday (hdate)'))
    if 'uq_holiday_proj_date' not in uq and 'uq_holiday_proj_date' not in idx:
        db.session.execute(text('CREATE UNIQUE INDEX uq_holiday_proj_date ON holiday (project_id, hdate)'))
    db.session.commit()


def init_db():
    db.create_all()
    add_missing_columns()
    ensure_projects()
    migrate_unique_constraints()
    add_missing_indexes()
    seed_route_master_if_empty()
    try:
        if not User.query.filter_by(role='super_admin').first():
            db.session.add(User(username='admin', full_name='Super Admin', role='super_admin',
                                password_hash=generate_password_hash('admin123'), must_change=True))
            db.session.commit()
            print('Super Admin created: username=admin  password=admin123  (you must change it at first login)')
    except IntegrityError:                       # two workers started at the same time
        db.session.rollback()


with app.app_context():
    init_db()

if __name__ == '__main__':
    # Development only. For real use start the production server:  python serve.py
    print('NOTE: this is the development server. Use "python serve.py" for production.')
    app.run(host='0.0.0.0', port=5000, debug=False, threaded=True)
