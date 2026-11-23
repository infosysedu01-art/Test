import os, tempfile
os.environ['DATA_DIR'] = tempfile.mkdtemp()      # the test runs on a throw-away database
os.environ.pop('DATABASE_URL', None)
# Run:  python selftest.py   -> every line must say PASS
import re, io, gzip, json, sys
from datetime import date, timedelta
import openpyxl
import app as m
m.DEFAULT_LANG = 'en'      # the checks look for English texts
t=date.today(); mon=t.strftime('%Y-%m')
class C:
    """behaves like a browser: refreshes its CSRF token from every response"""
    def __init__(s): s.c=m.app.test_client(); s.tok=None
    def _sync(s):
        with s.c.session_transaction() as ss: s.tok=ss.get('_csrf') or s.tok
    def get(s,*a,**k): r=s.c.get(*a,**k); s._sync(); return r
    def post(s,url,data=None,json_=None,notoken=False,**k):
        if s.tok is None: s.get('/login')
        if json_ is not None: r=s.c.post(url,json=json_,headers={'X-CSRF-Token':'' if notoken else s.tok},**k)
        else:
            d=dict(data or {})
            if not notoken: d['_csrf']=s.tok
            r=s.c.post(url,data=d,**k)
        s._sync(); return r
fails=[]
def ok(label,cond):
    print(('PASS ' if cond else 'FAIL ')+label)
    if not cond: fails.append(label)
a=C()
r=a.post('/login',{'username':'admin','password':'admin123'},notoken=True,follow_redirects=True); ok('login POST without CSRF token is rejected', b'expired' in r.data.lower())
r=a.post('/login',{'username':'admin','password':'admin123'}); ok('login with token ok (302)', r.status_code==302)
r=a.get('/dashboard'); ok('forced password change redirect', r.status_code==302 and 'change-password' in r.headers['Location'])
a.get('/change-password')
r=a.post('/change-password',{'current':'admin123','new':'short1','confirm':'short1'}); ok('weak password (6 chars) rejected', b'at least 8' in r.data)
r=a.post('/change-password',{'current':'admin123','new':'onlyletters','confirm':'onlyletters'}); ok('letters-only password rejected', b'at least 8' in r.data)
r=a.post('/change-password',{'current':'admin123','new':'Admin@2026','confirm':'Admin@2026'}); ok('strong password accepted', r.status_code==302)
r=a.get('/dashboard'); h=r.headers
ok('security headers', all(k in h for k in ('Content-Security-Policy','X-Frame-Options','X-Content-Type-Options','Referrer-Policy')) and h['X-Frame-Options']=='DENY' and h['Cache-Control']=='no-store')
sc=C().get('/login').headers.get('Set-Cookie',''); ok('session cookie HttpOnly + SameSite', 'HttpOnly' in sc and 'SameSite=Lax' in sc)
r=a.c.get('/dashboard',headers={'Accept-Encoding':'gzip'}); ok('gzip html (%d bytes)'%len(r.data), r.headers.get('Content-Encoding')=='gzip' and b'Dashboard' in gzip.decompress(r.data))
r=a.c.get('/static/vendor/bootstrap/bootstrap.min.css?v=4.0',headers={'Accept-Encoding':'gzip'}); ok('gzip static css (%d bytes)'%len(r.data), r.headers.get('Content-Encoding')=='gzip' and len(r.data)<60000 and gzip.decompress(r.data).startswith(b'@charset'))
r=a.c.get('/static/app.css?v=4.0'); ok('static cache header', 'max-age' in r.headers.get('Cache-Control',''))
r=m.app.test_client().get('/healthz'); ok('healthz', r.status_code==200 and r.json['status']=='ok')
r=a.get('/nope'); ok('404 friendly page', r.status_code==404 and b'Page not found' in r.data)
a.post('/zones',{'name':'Zone 1'}); a.post('/zones',{'name':'Zone 2'}); a.post('/wards',{'name':'Ward A','zone_id':1}); a.post('/wards',{'name':'Ward C','zone_id':2})
for i in range(1,31):
    a.post('/employees/add',{'name':'Emp %03d'%i,'father_name':'F%d'%i,'designation':'Sweeper','zone_id':1,'ward_id':1,'default_shift':'Day','default_work':'Sweeping','active':'1','joining_date':'2026-01-01'})
a.post('/employees/add',{'name':'Zone2 Emp','zone_id':2,'ward_id':2,'default_shift':'Day','default_work':'Sweeping','active':'1'})
days=list(range(1,t.day+1))
ch=[{'emp':e,'day':d,'s':'Present' if (e+d)%7 else 'Absent','loc':'Gomti Nagar','time':'06:00'} for e in range(1,31) for d in days]
r=a.post('/attendance/save',json_={'ward_id':1,'shift':'Day','work_type':'Sweeping','month':mon,'changes':ch}); ok('batch save %d cells -> %s'%(len(ch),r.json), r.status_code==200 and r.json['saved']+r.json['skipped']==len(ch))
# older month too, so the paging checks do not depend on today's day-of-month
pm=(t.replace(day=1)-timedelta(days=1)); pmon=pm.strftime('%Y-%m')
a.post('/attendance/save',json_={'ward_id':1,'shift':'Day','work_type':'Sweeping','month':pmon,'changes':[{'emp':e,'day':d,'s':'Present'} for e in range(1,31) for d in range(1,pm.day+1)]})
r=a.post('/attendance/save',json_={'ward_id':1,'shift':'Day','work_type':'Sweeping','month':mon,'changes':ch[:3]},notoken=True); ok('save without CSRF header rejected (400 json)', r.status_code==400 and 'error' in r.json)
r=a.post('/attendance/save',json_={'ward_id':1,'shift':'Day','work_type':'Sweeping','month':mon,'changes':[{'emp':1,'day':1,'s':'Present'}]*7000}); ok('oversize save rejected (413)', r.status_code==413)
r=a.get(f'/attendance?month={mon}&ward_id=1&shift=Day&work_type=Sweeping'); ok('sheet loads', r.status_code==200 and b'Emp 030' in r.data)
r=a.get('/reports?from=2026-01-01&to=2026-12-31'); b=r.data.decode(); mm=re.search(r'Showing (\d+) to (\d+) of (\d+) records',b)
total=int(mm.group(3)) if mm else 0
ok('reports paged 100 rows '+str(mm.groups() if mm else None), mm and total>=100 and int(mm.group(2))==100 and 'page-link' in b)
r=a.get('/reports?from=2026-01-01&to=2026-12-31&page=3'); mm=re.search(r'Showing (\d+) to (\d+)',r.data.decode()); ok('reports page 3 starts at 201', mm and mm.group(1)=='201')
r=a.get('/reports?from=2026-01-01&to=2026-12-31&download=1'); ws=openpyxl.load_workbook(io.BytesIO(r.data)).active; ok('streamed excel rows=%d (db total %d)'%(ws.max_row-2,total), ws.max_row-2==total)
for u in (f'/attendance/export?month={mon}&ward_id=1&shift=Day&work_type=Sweeping','/employees/1/export?month='+mon,f'/ward-reports?type=monthly&month={mon}&ward_id=all&shift=Day&download=1'):
    ok('xlsx '+u[:30], a.get(u).status_code==200)
b2=C()
for i in range(6): b2.post('/login',{'username':'ghost','password':'bad'})
r=b2.post('/login',{'username':'ghost','password':'bad'}); ok('lockout after 6 bad attempts for that username', b'Too many failed' in r.data)
r=b2.post('/login',{'username':'admin','password':'wrong'}); ok('other username is not locked by that', b'Incorrect' in r.data)
b=a.get('/audit').data.decode(); ok('audit log has login-failed / attendance-save / password-change', all(x in b for x in ('login-failed','attendance-save','password-change')))
ok('audit filter', 'ghost' in a.get('/audit?action=login-failed&user=ghost').data.decode())
r=a.post('/employees/31/delete',notoken=True,follow_redirects=True); ok('delete without CSRF blocked', b'expired' in r.data)
ok('employee still exists', b'Zone2 Emp' in a.get('/employees?q=Zone2').data)
r=a.post('/employees/31/delete',follow_redirects=True); ok('delete with token works', b'Employee deleted' in r.data)
r=C().post('/login?next=//evil.com',{'username':'admin','password':'Admin@2026'}); ok('no open redirect', 'evil.com' not in r.headers.get('Location',''))
a.post('/users/add',{'username':'z2','full_name':'Z2','password':'Secret123','role':'user','project':'1','active':'1','zone':'2','all_wards':'1','all_works':'1','all_shifts':'1','perm_employees_view':'on','perm_wards_view':'on','perm_zones_view':'on'})
u=C(); u.post('/login',{'username':'z2','password':'Secret123'})
zz=u.get('/zones').data
ok('zone user sees only zone 2 and cannot open zone-1 employee', b'Zone 2' in zz and b'Zone 1' not in zz and u.get('/employees/1').status_code==403)
ok('non-admin cannot open audit/users', u.get('/audit').status_code==403 and u.get('/users').status_code==403)
pages=['/dashboard','/zones','/wards','/employees','/employees/1','/employees/add','/holidays',f'/attendance?month={mon}&ward_id=1&shift=Day&work_type=Sweeping','/ward-reports?type=monthly','/reports','/users','/users/add','/audit','/change-password']
for lang in ('en','hi'):
    m.DEFAULT_LANG=lang; z=C(); z.post('/login',{'username':'admin','password':'Admin@2026'}); z.get('/dashboard')
    bad=[(p,z.get(p).status_code) for p in pages if z.get(p).status_code!=200]; ok(lang+' all pages 200 '+str(bad), not bad)
m.DEFAULT_LANG='en'
# ---- animation loader is present everywhere and its files are served ----
for pg in ('/dashboard','/zones','/employees','/reports',f'/attendance?month={mon}&ward_id=1&shift=Day&work_type=Sweeping'):
    b=a.get(pg).data
    ok('loader markup + script on '+pg[:12], b'id="appLoader"' in b and b'loader.js?v=' in b and b.count(b'class="al-ring"')==1 and b'id="topBar"' in b)
ok('login page has loader', b'id="appLoader"' in C().get('/login').data)
ok('loader.js served + cached', a.get('/static/loader.js').status_code==200 and 'max-age' in a.get('/static/loader.js').headers.get('Cache-Control',''))

# ================= vehicle master + driver / helper vehicle assignment =================
em=lambda b: b.decode('utf-8','ignore') if isinstance(b,bytes) else b
r=a.get('/vehicles'); ok('vehicles page opens (admin)', r.status_code==200 and b'Vehicle Master' in r.data)
r=a.post('/vehicles/add',{'vehicle_no':'up32  ab 1234','vehicle_type':'Auto Tipper','zone_id':'1','ward_id':'1','active':'1'}); ok('add vehicle (302)', r.status_code==302)
vid=int(re.search(r'/vehicles/(\d+)',r.headers['Location']).group(1))
ok('number is normalised to UP32 AB 1234', b'UP32 AB 1234' in a.get('/vehicles').data)
r=a.post('/vehicles/add',{'vehicle_no':'UP32-AB-1234','zone_id':'1','active':'1'},follow_redirects=True); ok('same number in another spelling is rejected', b'already exists' in r.data)
r=a.post('/vehicles/add',{'vehicle_no':'@@','zone_id':'1','active':'1'},follow_redirects=True); ok('invalid number rejected', b'valid vehicle number' in r.data)
r=a.post('/vehicles/add',{'vehicle_no':'UP32 CD 5678','vehicle_type':'Compactor','zone_id':'1','active':'1'}); vid2=int(re.search(r'/vehicles/(\d+)',r.headers['Location']).group(1))
r=a.post('/vehicles/add',{'vehicle_no':'UP78 ZZ 0001','zone_id':'2','active':'1'}); vidz2=int(re.search(r'/vehicles/(\d+)',r.headers['Location']).group(1))
r=a.post('/vehicles/add',{'vehicle_no':'UP78 WARD C','zone_id':'1','ward_id':'2','active':'1'},follow_redirects=True); ok('ward from another zone rejected', b'does not belong' in r.data)
fm=a.get('/employees/add').data.decode()
ok('employee form: designation list + vehicle select (hidden until Driver/Helper)', 'name="designation_sel"' in fm and 'id="vehSel"' in fm and b'UP32 AB 1234' in a.get('/lookup/vehicle?q=234').data and 'id="vehBox" style="display:none"' in fm)
def addemp(name,sel,veh=None,other='',zone='1',ward='1'):
    d={'name':name,'zone_id':zone,'ward_id':ward,'designation_sel':sel,'designation_other':other,'default_shift':'Day','default_work':'Sweeping','active':'1'}
    if veh: d['vehicle_id']=str(veh)
    return a.post('/employees/add',d,follow_redirects=True)
addemp('Drv One','Driver',vid); addemp('Hlp One','Helper',vid); addemp('Hlp Two','__other__',vid,other='helper')
r=addemp('Sup One','Supervisor',vid)       # a supervisor must NOT keep a vehicle even if the field is sent
r=addemp('Drv Zone2','Driver',vid,zone='2',ward='2'); ok('vehicle of another zone rejected for the employee', b'does not belong to the selected zone' in r.data)
def emp_by(name):
    with m.app.app_context(): e=m.Employee.query.filter_by(name=name).first(); return (e.id,e.designation,e.vehicle_id) if e else None
ok('driver + helper saved with the vehicle', emp_by('Drv One')[2]==vid and emp_by('Hlp One')[2]==vid and emp_by('Hlp Two')[1]=='helper' and emp_by('Hlp Two')[2]==vid)
ok('supervisor never keeps a vehicle (server rule)', emp_by('Sup One')[2] is None)
ok('employee of other zone not created', emp_by('Drv Zone2') is None)
b=a.get('/vehicles').data.decode(); ok('vehicle list shows driver and helpers', 'Drv One' in b and 'Hlp One' in b and 'Hlp Two' in b)
ok('vehicle without crew shows "No driver"/"No helper"', 'No driver' in b and 'No helper' in b)
b=a.get(f'/vehicles/{vid}').data.decode(); ok('vehicle view page lists drivers and helpers', 'Drv One' in b and 'Hlp One' in b and 'Sup One' not in b)
b=a.get(f'/employees?q=UP32AB').data.decode(); ok('employees searchable by vehicle number', 'Drv One' in b and 'Sup One' not in b and 'UP32 AB 1234' in b)
b=a.get('/employees/%d'%emp_by('Drv One')[0]).data.decode(); ok('employee view shows the vehicle', 'UP32 AB 1234' in b)
# attendance sheet + excel + reports show the vehicle next to designation
ch=[{'emp':emp_by('Drv One')[0],'day':t.day,'s':'Present'},{'emp':emp_by('Hlp One')[0],'day':t.day,'s':'Present'}]
a.post('/attendance/save',json_={'ward_id':1,'shift':'Day','work_type':'Sweeping','month':mon,'changes':ch})
b=a.get(f'/attendance?month={mon}&ward_id=1&shift=Day&work_type=Sweeping').data.decode(); ok('attendance sheet data carries the vehicle (shown beside Driver/Helper)', '"veh": "UP32 AB 1234"' in b and '"desig": "Driver"' in b and 'vbadge' in b)
ws=openpyxl.load_workbook(io.BytesIO(a.get(f'/attendance/export?month={mon}&ward_id=1&shift=Day&work_type=Sweeping').data)).active
col=[[c.value for c in row] for row in ws.iter_rows(min_row=5,max_col=5)]; ok('attendance Excel: "Driver - UP32 AB 1234"', any(r[4]=='Driver - UP32 AB 1234' for r in col) and any(r[4]=='Helper - UP32 AB 1234' for r in col) and any(r[4]=='Supervisor' or r[4]=='Sweeper' for r in col))
ws=openpyxl.load_workbook(io.BytesIO(a.get(f'/ward-reports?type=monthly&month={mon}&ward_id=1&shift=Day&download=1').data)).active
ok('ward report Excel shows the vehicle', any('UP32 AB 1234' in str(c.value) for row in ws.iter_rows(min_row=5,max_col=5) for c in row))
ok('ward report page shows the vehicle', 'UP32 AB 1234' in a.get(f'/ward-reports?type=daily&date={t}&ward_id=1&shift=Day').data.decode())
ok('reports page shows the vehicle', 'UP32 AB 1234' in a.get('/reports?from=%s&to=%s&shift=Day'%(t,t)).data.decode())
# correcting mistakes: edit number, unassign, assign (move), delete rules
r=a.post(f'/vehicles/{vid}/edit',{'vehicle_no':'UP32 AB 9999','vehicle_type':'Auto Tipper','zone_id':'1','ward_id':'1','active':'1'}); ok('vehicle edit (302)', r.status_code==302)
ok('new number appears in employee list', 'UP32 AB 9999' in a.get('/employees?q=Drv').data.decode() and 'UP32 AB 1234' not in a.get('/employees?q=Drv').data.decode())
r=a.post(f'/vehicles/{vid}/delete',follow_redirects=True); ok('delete blocked while crew is assigned', b'still has crew' in r.data)
r=a.post(f'/vehicles/{vid}/unassign/{emp_by("Hlp Two")[0]}',follow_redirects=True); ok('remove helper from vehicle', b'Removed from the vehicle' in r.data and emp_by('Hlp Two')[2] is None)
r=a.post(f'/vehicles/{vid2}/assign',{'employee_id':emp_by('Hlp One')[0]},follow_redirects=True); ok('assign (move) helper to the other vehicle', b'Assigned to the vehicle' in r.data and emp_by('Hlp One')[2]==vid2)
r=a.post(f'/vehicles/{vid2}/assign',{'employee_id':emp_by('Sup One')[0]},follow_redirects=True); ok('supervisor cannot be assigned to a vehicle', b'cannot be assigned' in r.data)
# designation change clears the vehicle
d=a.get('/employees/%d/edit'%emp_by('Drv One')[0]).data.decode(); ok('edit form pre-selects Driver + the vehicle', 'value="Driver" selected' in d and 'class="form-control combo-in" id="vehIn"' in d and 'value="UP32 AB 9999' in d)
a.post('/employees/%d/edit'%emp_by('Drv One')[0],{'name':'Drv One','zone_id':'1','ward_id':'1','designation_sel':'Supervisor','vehicle_id':str(vid),'default_shift':'Day','default_work':'Sweeping','active':'1'})
ok('driver changed to Supervisor loses the vehicle', emp_by('Drv One')[2] is None)
a.post(f'/vehicles/{vid2}/unassign/{emp_by("Hlp One")[0]}')
r=a.post(f'/vehicles/{vid2}/delete',follow_redirects=True); ok('empty vehicle can be deleted', b'Vehicle deleted' in r.data)
# permissions: nobody gets vehicle access unless granted
a.post('/users/add',{'username':'nov','full_name':'No Vehicle','password':'Secret123','role':'user','project':'1','active':'1','all_zones':'1','all_wards':'1','all_works':'1','all_shifts':'1','perm_employees_view':'on','perm_employees_add':'on','perm_employees_edit':'on'})
a.post('/users/add',{'username':'vw','full_name':'View Vehicle','password':'Secret123','role':'user','project':'1','active':'1','all_zones':'1','all_wards':'1','all_works':'1','all_shifts':'1','perm_employees_view':'on','perm_vehicles_view':'on'})
a.post('/users/add',{'username':'vz2','full_name':'Zone2 Vehicle','password':'Secret123','role':'user','project':'1','active':'1','zone':'2','all_wards':'1','all_works':'1','all_shifts':'1','perm_vehicles_view':'on','perm_vehicles_add':'on','perm_vehicles_edit':'on','perm_vehicles_delete':'on','perm_employees_view':'on'})
n=C(); n.post('/login',{'username':'nov','password':'Secret123'}); n.get('/dashboard')
r=n.get('/vehicles',follow_redirects=True); ok('user WITHOUT vehicle permission is refused (list)', b'Vehicle Master' not in r.data and b'do not have access' in r.data)
ok('... and refused for view/add/edit/delete urls', all(n.get(u).status_code in (302,403) for u in (f'/vehicles/{vid}','/vehicles/add',f'/vehicles/{vid}/edit')) and n.post(f'/vehicles/{vid}/delete').status_code in (302,403))
ok('... no Vehicles menu', b'bi-truck' not in n.get('/dashboard').data)
ef=n.get('/employees/add').data.decode(); ok('employee form of that user has no vehicle field', 'id="vehSel"' not in ef and 'name="designation_sel"' in ef)
# he edits the driver "Hlp One" is unassigned; use a fresh driver with vehicle: keep Driver -> vehicle stays untouched
a.post('/employees/add',{'name':'Drv Keep','zone_id':'1','ward_id':'1','designation_sel':'Driver','vehicle_id':str(vid),'default_shift':'Day','default_work':'Sweeping','active':'1'})
kid=emp_by('Drv Keep')[0]
n.post('/employees/%d/edit'%kid,{'name':'Drv Keep','zone_id':'1','ward_id':'1','designation_sel':'Driver','mobile':'9999999999','default_shift':'Day','default_work':'Sweeping','active':'1'})
ok('editing a driver without vehicle permission keeps his vehicle', emp_by('Drv Keep')[2]==vid)
v_=C(); v_.post('/login',{'username':'vw','password':'Secret123'}); v_.get('/dashboard')
ok('view-only user sees vehicles', b'UP32 AB 9999' in v_.get('/vehicles').data and v_.get(f'/vehicles/{vid}').status_code==200)
vv=v_.get(f'/vehicles/{vid}').data
ok('view-only user has no Add/Edit/Delete/Remove/Assign', b'/vehicles/add' not in v_.get('/vehicles').data and b'/edit' not in vv and b'unassign' not in vv and b'/assign' not in vv)
ok('view-only user cannot add / edit / delete / assign', v_.post('/vehicles/add',{'vehicle_no':'UP00 XX 0000','zone_id':'1'}).status_code in (302,403) and v_.post(f'/vehicles/{vid}/assign',{'employee_id':kid}).status_code in (302,403))
with m.app.app_context(): ok('nothing was created by the view-only user', m.Vehicle.query.filter_by(vkey='UP00XX0000').first() is None)
z=C(); z.post('/login',{'username':'vz2','password':'Secret123'}); z.get('/dashboard'); zb=z.get('/vehicles').data.decode()
ok('zone-2 user sees only zone-2 vehicles', 'UP78 ZZ 0001' in zb and 'UP32 AB 9999' not in zb)
ok('zone-2 user cannot open a zone-1 vehicle', z.get(f'/vehicles/{vid}').status_code==403 and z.post(f'/vehicles/{vid}/delete').status_code==403 and z.get(f'/vehicles/{vid}/edit').status_code==403)
ok('zone-2 user can add a vehicle only in his zone', z.post('/vehicles/add',{'vehicle_no':'UP78 NEW 1','zone_id':'1','active':'1'},follow_redirects=True).data.count(b'Please select a zone')>=1)
m.DEFAULT_LANG='hi'; h=C(); h.post('/login',{'username':'admin','password':'Admin@2026'}); h.get('/dashboard')
ok('hindi vehicle pages', all(h.get(u).status_code==200 for u in ('/vehicles',f'/vehicles/{vid}','/vehicles/add','/employees/add')) and 'वाहन' in h.get('/vehicles').data.decode('utf-8'))
m.DEFAULT_LANG='en'
ok('audit trail has vehicle actions', all(x in a.get('/audit').data.decode() for x in ('vehicle-add','vehicle-update','vehicle-assign','vehicle-unassign','vehicle-delete')))

# ================= route master + Route ID on drivers / helpers (same rules as vehicles) =================
r=a.get('/routes'); ok('routes page opens (admin)', r.status_code==200 and b'Route Master' in r.data)
ok('route ID pattern accepts R-12, R/12, ROUTE 5, 7 and rejects @@ and backslash', all(m.ROUTE_RE.match(x) for x in ('R-12','R/12','ROUTE 5','7')) and not m.ROUTE_RE.match('@@') and not m.ROUTE_RE.match('A\\B') and m.route_key('r - 12/a')=='R12A')
r=a.post('/routes/add',{'route_no':'r-12','route_name':'Gomti Nagar Main Road','zone_id':'1','ward_id':'1','active':'1'}); ok('add route (302)', r.status_code==302)
rid=int(re.search(r'/routes/(\d+)',r.headers['Location']).group(1))
ok('Route ID normalised to R-12', b'R-12' in a.get('/routes').data and b'Gomti Nagar Main Road' in a.get('/routes').data)
r=a.post('/routes/add',{'route_no':'R 12','zone_id':'1','active':'1'},follow_redirects=True); ok('same Route ID in another spelling is rejected', b'already exists' in r.data)
r=a.post('/routes/add',{'route_no':'@@','zone_id':'1','active':'1'},follow_redirects=True); ok('invalid Route ID rejected', b'valid Route ID' in r.data)
r=a.post('/routes/add',{'route_no':'R-20','zone_id':'1','active':'1'}); rid2=int(re.search(r'/routes/(\d+)',r.headers['Location']).group(1))
r=a.post('/routes/add',{'route_no':'R-90','zone_id':'2','active':'1'}); ridz2=int(re.search(r'/routes/(\d+)',r.headers['Location']).group(1))
fm=a.get('/employees/add').data.decode(); ok('employee form has Route ID select (hidden until Driver/Helper)', 'id="routeSel"' in fm and b'R-12' in a.get('/lookup/route?q=12').data and 'id="routeBox" style="display:none"' in fm)
def addemp2(name,sel,veh=None,route=None,other='',zone='1',ward='1'):
    d={'name':name,'zone_id':zone,'ward_id':ward,'designation_sel':sel,'designation_other':other,'default_shift':'Day','default_work':'Sweeping','active':'1'}
    if veh: d['vehicle_id']=str(veh)
    if route: d['route_id']=str(route)
    return a.post('/employees/add',d,follow_redirects=True)
def emp2(name):
    with m.app.app_context(): e=m.Employee.query.filter_by(name=name).first(); return (e.id,e.designation,e.vehicle_id,e.route_id) if e else None
addemp2('RDrv','Driver',vid,rid); addemp2('RHlp','Helper',None,rid); addemp2('RHlp2','__other__',None,rid,other='HELPER'); addemp2('RSup','Supervisor',vid,rid)
r=addemp2('RZone2','Driver',None,rid,zone='2',ward='2'); ok('route of another zone rejected for the employee', b'does not belong to the selected zone' in r.data and emp2('RZone2') is None)
ok('driver has BOTH vehicle and route; helper has route only', emp2('RDrv')[2]==vid and emp2('RDrv')[3]==rid and emp2('RHlp')[2] is None and emp2('RHlp')[3]==rid and emp2('RHlp2')[3]==rid)
ok('supervisor never keeps vehicle or route (server rule)', emp2('RSup')[2] is None and emp2('RSup')[3] is None)
b=a.get('/routes').data.decode(); ok('route list shows driver + helpers, and "No driver" for an empty route', 'RDrv' in b and 'RHlp' in b and 'No driver' in b)
b=a.get(f'/routes/{rid}').data.decode(); ok('route view lists drivers and helpers with their vehicle', 'RDrv' in b and 'RHlp' in b and 'RSup' not in b and 'UP32 AB 9999' in b)
b=a.get(f'/vehicles/{vid}').data.decode(); ok('vehicle view shows the crew route', 'RDrv' in b and 'R-12' in b)
b=a.get('/employees?q=R12').data.decode(); ok('employees searchable by Route ID', 'RDrv' in b and 'RSup' not in b)
b=a.get('/employees/%d'%emp2('RDrv')[0]).data.decode(); ok('employee view shows vehicle and route', 'UP32 AB 9999' in b and 'R-12' in b)
ch=[{'emp':emp2('RDrv')[0],'day':t.day,'s':'Present'},{'emp':emp2('RHlp')[0],'day':t.day,'s':'Present'}]
a.post('/attendance/save',json_={'ward_id':1,'shift':'Day','work_type':'Sweeping','month':mon,'changes':ch})
b=a.get(f'/attendance?month={mon}&ward_id=1&shift=Day&work_type=Sweeping').data.decode(); ok('attendance sheet data carries vehicle + route', '"route": "R-12"' in b and 'rbadge' in b)
ws=openpyxl.load_workbook(io.BytesIO(a.get(f'/attendance/export?month={mon}&ward_id=1&shift=Day&work_type=Sweeping').data)).active
col=[r[4] for r in ([[c.value for c in row] for row in ws.iter_rows(min_row=5,max_col=5)])]
ok('attendance Excel: "Driver - UP32 AB 9999 - Route R-12" and "Helper - Route R-12"', 'Driver - UP32 AB 9999 - Route R-12' in col and 'Helper - Route R-12' in col)
ws=openpyxl.load_workbook(io.BytesIO(a.get(f'/ward-reports?type=monthly&month={mon}&ward_id=1&shift=Day&download=1').data)).active
ok('ward report Excel shows the route', any('Route R-12' in str(c.value) for row in ws.iter_rows(min_row=5,max_col=5) for c in row))
ok('reports page shows the route', 'Route R-12' in a.get('/reports?from=%s&to=%s&shift=Day'%(t,t)).data.decode())
r=a.post(f'/routes/{rid}/edit',{'route_no':'R-12A','route_name':'Gomti Nagar','zone_id':'1','ward_id':'1','active':'1'}); ok('route edit (302)', r.status_code==302)
ok('new Route ID appears everywhere', 'R-12A' in a.get('/employees?q=RDrv').data.decode() and 'Route R-12A' not in ''.join(str(x) for x in []))
r=a.post(f'/routes/{rid}/delete',follow_redirects=True); ok('route delete blocked while crew is assigned', b'still has crew' in r.data)
r=a.post(f'/routes/{rid}/unassign/{emp2("RHlp2")[0]}',follow_redirects=True); ok('remove helper from route', b'Removed from the route' in r.data and emp2('RHlp2')[3] is None)
r=a.post(f'/routes/{rid2}/assign',{'employee_id':emp2('RHlp')[0]},follow_redirects=True); ok('assign (move) helper to another route', b'Assigned to the route' in r.data and emp2('RHlp')[3]==rid2)
r=a.post(f'/routes/{rid2}/assign',{'employee_id':emp2('RSup')[0]},follow_redirects=True); ok('supervisor cannot be assigned to a route', b'cannot be assigned' in r.data)
a.post('/employees/%d/edit'%emp2('RDrv')[0],{'name':'RDrv','zone_id':'1','ward_id':'1','designation_sel':'Clerk','vehicle_id':str(vid),'route_id':str(rid),'default_shift':'Day','default_work':'Sweeping','active':'1'})
ok('driver changed to Clerk loses vehicle AND route', emp2('RDrv')[2] is None and emp2('RDrv')[3] is None)
a.post(f'/routes/{rid2}/unassign/{emp2("RHlp")[0]}'); a.post(f'/routes/{rid}/unassign/{emp2("RHlp2")[0]}')
r=a.post(f'/routes/{rid2}/delete',follow_redirects=True); ok('empty route can be deleted', b'Route deleted' in r.data)
# permissions
a.post('/users/add',{'username':'norte','full_name':'No Route','password':'Secret123','role':'user','project':'1','active':'1','all_zones':'1','all_wards':'1','all_works':'1','all_shifts':'1','perm_employees_view':'on','perm_employees_add':'on','perm_employees_edit':'on','perm_vehicles_view':'on'})
a.post('/users/add',{'username':'rview','full_name':'Route View','password':'Secret123','role':'user','project':'1','active':'1','all_zones':'1','all_wards':'1','all_works':'1','all_shifts':'1','perm_employees_view':'on','perm_routes_view':'on'})
a.post('/users/add',{'username':'rz2','full_name':'Zone2 Route','password':'Secret123','role':'user','project':'1','active':'1','zone':'2','all_wards':'1','all_works':'1','all_shifts':'1','perm_routes_view':'on','perm_routes_add':'on','perm_routes_edit':'on','perm_routes_delete':'on','perm_employees_view':'on'})
n=C(); n.post('/login',{'username':'norte','password':'Secret123'}); n.get('/dashboard')
r=n.get('/routes',follow_redirects=True); ok('user WITHOUT route permission is refused', b'Route Master' not in r.data and b'do not have access' in r.data)
ok('... for view/add/edit/delete urls too', all(n.get(u).status_code in (302,403) for u in (f'/routes/{rid}','/routes/add',f'/routes/{rid}/edit')) and n.post(f'/routes/{rid}/delete').status_code in (302,403))
ok('... no Routes menu, but he still has the Vehicles menu he was given', b'bi-signpost-split' not in n.get('/dashboard').data and b'bi-truck' in n.get('/dashboard').data)
ef=n.get('/employees/add').data.decode(); ok('his employee form has the vehicle select but no route select', 'id="vehSel"' in ef and 'id="routeSel"' not in ef)
a.post('/employees/add',{'name':'RKeep','zone_id':'1','ward_id':'1','designation_sel':'Driver','vehicle_id':str(vid),'route_id':str(rid),'default_shift':'Day','default_work':'Sweeping','active':'1'}); kid=emp2('RKeep')[0]
n.post('/employees/%d/edit'%kid,{'name':'RKeep','zone_id':'1','ward_id':'1','designation_sel':'Driver','vehicle_id':str(vid),'mobile':'9999999999','default_shift':'Day','default_work':'Sweeping','active':'1'})
ok('editing without route permission keeps the route', emp2('RKeep')[3]==rid)
v_=C(); v_.post('/login',{'username':'rview','password':'Secret123'}); v_.get('/dashboard')
ok('view-only user sees routes', b'R-12A' in v_.get('/routes').data and v_.get(f'/routes/{rid}').status_code==200)
vv=v_.get(f'/routes/{rid}').data
ok('view-only user has no Add/Edit/Delete/Remove/Assign', b'/routes/add' not in v_.get('/routes').data and b'/edit' not in vv and b'unassign' not in vv and b'/assign' not in vv)
ok('view-only user cannot add / assign', v_.post('/routes/add',{'route_no':'X-1','zone_id':'1'}).status_code in (302,403) and v_.post(f'/routes/{rid}/assign',{'employee_id':kid}).status_code in (302,403))
with m.app.app_context(): ok('nothing created by the view-only user', m.Route.query.filter_by(rkey='X1').first() is None)
z=C(); z.post('/login',{'username':'rz2','password':'Secret123'}); z.get('/dashboard'); zb=z.get('/routes').data.decode()
ok('zone-2 user sees only zone-2 routes', 'R-90' in zb and 'R-12A' not in zb)
ok('zone-2 user cannot open a zone-1 route', z.get(f'/routes/{rid}').status_code==403 and z.post(f'/routes/{rid}/delete').status_code==403 and z.get(f'/routes/{rid}/edit').status_code==403)
m.DEFAULT_LANG='hi'; h=C(); h.post('/login',{'username':'admin','password':'Admin@2026'}); h.get('/dashboard')
ok('hindi route pages', all(h.get(u).status_code==200 for u in ('/routes',f'/routes/{rid}','/routes/add','/employees/add')) and 'रूट' in h.get('/routes').data.decode('utf-8'))
m.DEFAULT_LANG='en'
ok('audit trail has route actions', all(x in a.get('/audit').data.decode() for x in ('route-add','route-update','route-assign','route-unassign','route-delete')))

# ---------------------------------------------------------------- multi-project
print('--- projects')
def J(c,u): return c.post('/login/check',{'username':u}).get_json()
with m.app.app_context():
    zname=m.Zone.query.filter_by(project_id=1).first().name; e1=m.Employee.query.first(); e1id,e1name=e1.id,e1.name; nz1=m.Zone.query.count()
ok('default project Lucknow exists, company name follows it', 'Lion Enviro Lucknow' in a.get('/dashboard').data.decode())
ok('projects page', a.get('/projects').status_code==200 and b'Lucknow' in a.get('/projects').data)
r=a.post('/projects',{'name':'Barabanki','code_prefix':'leb','active':'1'},follow_redirects=True); ok('add project Barabanki', b'Project added' in r.data)
r=a.post('/projects',{'name':'barabanki','active':'1'},follow_redirects=True); ok('duplicate project name refused', b'already exists' in r.data)
a.post('/projects',{'name':'Kashi','code_prefix':'LEK','active':'1'})
ok('login check: admin has every project', [p['name'] for p in J(C(),'admin')['projects']]==['Barabanki','Kashi','Lucknow'])
ok('login check: unknown user -> no password box', J(C(),'ghost')=={'found':False})
ok('login check: z2 belongs to Lucknow only', [p['name'] for p in J(C(),'z2')['projects']]==['Lucknow'])
ok('login page has project + 2-step markup', all(x in C().get('/login').data for x in (b'id="proj"',b'id="step2"',b'/login/check')))
r=a.post('/users/add',{'username':'noproj','full_name':'No Proj','password':'Secret123','role':'user','active':'1','all_zones':'1','all_wards':'1','all_works':'1','all_shifts':'1'},follow_redirects=True)
ok('normal user without a project is refused', b'at least one project' in r.data)
a.post('/users/add',{'username':'bu','full_name':'Bara User','password':'Secret123','role':'user','project':'2','active':'1','all_zones':'1','all_wards':'1','all_works':'1','all_shifts':'1','perm_employees_view':'on','perm_employees_add':'on','perm_zones_view':'on','perm_zones_add':'on','perm_wards_view':'on','perm_wards_add':'on','perm_holidays_view':'on','perm_holidays_add':'on'})
ok('login check: bu belongs to Barabanki only', [p['name'] for p in J(C(),'bu')['projects']]==['Barabanki'])
ok('users list shows the project', b'Barabanki' in a.get('/users').data)

a.post('/project/switch',{'project_id':'2'}); d=a.get('/dashboard').data.decode()
import re as _re
ttl=_re.search(r'<title>(.*?)</title>',d).group(1)
ok('switch to Barabanki: company name changes', 'Lion Enviro Barabanki' in ttl and 'Lucknow' not in ttl and 'Lion Enviro Barabanki' in d)
zp=a.get('/zones').data.decode(); ok('Barabanki starts empty (no Lucknow zones)', zname not in zp and 'No records found' in zp)
ok('same zone name allowed in another project', b'Zone added' in a.post('/zones',{'name':zname},follow_redirects=True).data)
with m.app.app_context(): zb=m.Zone.query.filter_by(project_id=2).first().id
a.post('/wards',{'name':'B-Ward 1','zone_id':str(zb)})
with m.app.app_context(): wb=m.Ward.query.filter_by(zone_id=zb).first().id
r=a.post('/employees/add',{'name':'Bara Emp','zone_id':str(zb),'ward_id':str(wb),'designation':'Sweeper','default_shift':'Day','default_work':'Door to Door','active':'1'},follow_redirects=True)
with m.app.app_context(): be=m.Employee.query.filter_by(name='Bara Emp').first()
ok('employee added in Barabanki gets the project code prefix', be is not None and be.code.startswith('LEB'))
ok('Barabanki list shows only its own employee', b'Bara Emp' in a.get('/employees').data and e1name.encode() not in a.get('/employees').data)
ok('Lucknow employee is not reachable from Barabanki', a.get('/employees/%d'%e1id).status_code in (403,404))
ok('same holiday date allowed in two projects', b'Holiday added' in a.post('/holidays',{'hdate':'2026-12-25','name':'Christmas B'},follow_redirects=True).data)
with m.app.app_context():
    from sqlalchemy.exc import IntegrityError
    rk=m.Route.query.first()
    try:
        m.db.session.add(m.Route(project_id=2,route_no=rk.route_no,rkey=rk.rkey,zone_id=zb)); m.db.session.commit(); same=True
    except IntegrityError:
        m.db.session.rollback(); same=False
ok('same Route ID allowed in two projects', same)
a.post('/project/switch',{'project_id':'1'})
ok('back in Lucknow: no Barabanki data', b'Bara Emp' not in a.get('/employees').data and b'Christmas B' not in a.get('/holidays?year=2026').data and 'Lion Enviro Lucknow' in a.get('/dashboard').data.decode())
with m.app.app_context(): ok('Lucknow zone count unchanged', m.Zone.query.filter_by(project_id=1).count()==nz1)

b=C()
r=b.post('/login',{'username':'bu','password':'Secret123','project_id':'1'},follow_redirects=True); ok('bu cannot enter Lucknow', b'do not have access' in r.data and b'Logout' not in r.data)
r=b.post('/login',{'username':'bu','password':'Secret123','project_id':'2'}); ok('bu logs in to Barabanki', r.status_code==302)
d=b.get('/dashboard').data.decode(); ok('bu sees Barabanki company name', 'Lion Enviro Barabanki' in d)
ok('bu cannot open a Lucknow employee', b.get('/employees/%d'%e1id).status_code in (403,404))
ok('bu cannot switch to Lucknow', b.post('/project/switch',{'project_id':'1'}).status_code==403)
ok('bu cannot open Projects / Users', b.get('/projects').status_code==403 and b.get('/users').status_code==403)
ok('bu sees only Barabanki zone', zname in b.get('/zones').data.decode() and b'B-Ward' not in b.get('/zones').data and b.get('/wards').status_code==200)
ok('project delete is refused while it has data', b'has data' in a.post('/projects/2/delete',follow_redirects=True).data)
ok('empty project can be deleted', b'Project deleted' in a.post('/projects/3/delete',follow_redirects=True).data)

# ---------------------------------------------------------------- search boxes (vehicle / route / tracker)
print('--- lookup')
L=lambda c,u:c.get(u).get_json()
with m.app.app_context():
    zid1=m.Zone.query.filter_by(project_id=1).first().id
    m.db.session.add(m.Vehicle(vehicle_no='UP99 XY 4321',vkey='UP99XY4321',zone_id=zid1,active=True))
    m.db.session.add(m.Route(route_no='RT-4321',rkey='RT4321',zone_id=zid1,active=True)); m.db.session.commit()
ok('lookup finds a vehicle by a few digits', any(i['label'].startswith('UP99 XY 4321') for i in L(a,'/lookup/vehicle?q=4321')['items']))
ok('lookup finds a route by part of the ID', any(i['label'].startswith('RT-4321') for i in L(a,'/lookup/route?q=4321')['items']))
ok('lookup: no match gives an empty list', L(a,'/lookup/vehicle?q=zzzz9')['items']==[])
ok('lookup: % / _ typed by the user are not wildcards', L(a,'/lookup/vehicle?q=%25')['items']==[] and L(a,'/lookup/vehicle?q=_')['items']==[])
ok('lookup: zone filter', L(a,'/lookup/vehicle?q=&zone_id=999999')['items']==[])
ok('lookup: zone-2 user cannot find a zone-1 vehicle', b'UP99 XY 4321' not in z.get('/lookup/vehicle?q=4321').data)
a.post('/users/add',{'username':'novt','full_name':'No Veh','password':'Secret123','role':'user','project':'1','active':'1','all_zones':'1','all_wards':'1','all_works':'1','all_shifts':'1','perm_employees_view':'on'})
nv=C(); nv.post('/login',{'username':'novt','password':'Secret123'})
ok('lookup: user without vehicle permission is refused', nv.get('/lookup/vehicle').status_code==403 and nv.get('/lookup/route').status_code==403 and nv.get('/lookup/tracker').status_code==403)
ok('lookup: not logged in / unknown kind', C().get('/lookup/vehicle').status_code in (302,401) and a.get('/lookup/bogus').status_code==404)
with m.app.app_context():
    for k in range(45): m.db.session.add(m.Vehicle(vehicle_no='ZZ%03d'%k,vkey='ZZ%03d'%k,zone_id=zid1,active=True))
    m.db.session.commit()
big=L(a,'/lookup/vehicle?q=ZZ'); one=L(a,'/lookup/vehicle?q=ZZ044')
ok('lookup: big list returns only 30 + "more" flag', len(big['items'])==30 and big['more'] is True)
ok('lookup: typing more digits narrows it to one', [i['label'] for i in one['items']]==['ZZ044'] and one['more'] is False)
ok('lookup: best (starts-with) matches come first', L(a,'/lookup/vehicle?q=ZZ04')['items'][0]['label'].startswith('ZZ04'))
a.post('/project/switch',{'project_id':'2'}); ok('lookup: another project sees none of them', L(a,'/lookup/vehicle?q=ZZ')['items']==[]); a.post('/project/switch',{'project_id':'1'})
fm=a.get('/employees/add').data.decode()
ok('employee form is light: no vehicle option list in the page', 'ZZ044' not in fm and 'class="combo"' in fm and 'combo.js?v=' in fm)
ok('combo.js served', a.get('/static/combo.js').status_code==200)
with m.app.app_context():
    m.Vehicle.query.filter(m.Vehicle.vkey.like('ZZ%')).delete(synchronize_session=False); m.Vehicle.query.filter_by(vkey='UP99XY4321').delete(); m.Route.query.filter_by(rkey='RT4321').delete(); m.db.session.commit()

print('\nFAILED:',fails if fails else 'none')
