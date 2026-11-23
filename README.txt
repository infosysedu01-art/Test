Lion Enviro - Ward Wise Attendance Management System   v4.8 (multi-project)  (English edition)

QUICK START
1) Stop any old copy first (Ctrl+C in its window) - otherwise the old version keeps running.
2) pip install -r requirements.txt
3) Windows: double-click start_server.bat      |      any system: python serve.py
4) Open http://localhost:5000   (sidebar bottom shows: v4.8 - Bootstrap 5.2.3)
5) First login: username = admin   password = admin123   -> the app forces you to set a new strong password.

NEW (v4.3): a clean logo + spinner loader is shown on page load, employee add / edit / update / delete,
attendance save and report / Excel downloads.

NEW (v4.3): Vehicle Master (add / edit / view / delete) and a Vehicle Number on Driver and Helper employees.
The Vehicle option appears in the Employee form only when the designation is Driver or Helper. The vehicle is shown
beside Driver / Helper in the attendance sheet, reports and Excel files. Give the 'Vehicle' permission in
Users & Access to the people who may use it - nobody else sees the menu or the pages.

NEW (v4.3): Route Master (Route ID) - add / edit / view / delete - and a Route ID on Driver and Helper employees,
exactly like the Vehicle Master. The route is shown beside the vehicle in the attendance sheet, reports and Excel.
Give the 'Route' permission in Users & Access only to the people who may use it.

Read DEPLOYMENT.txt  (one PC / central server, security, sizing, backup, checklist).
Run  python selftest.py  once: every line must say PASS (uses a temporary database, your data is untouched).

Language: opens in English; the English / हिन्दी switch in the header changes it any time (DEFAULT_LANG in app.py).
UI: Bootstrap 5.2.3 + Bootstrap Icons are bundled in static/vendor - works fully offline.


NEW (v4.5): MULTI-PROJECT.  One application, many projects (Lucknow, Barabanki, Kashi ...).
 * Sidebar > Administration > Projects (Super Admin only): add / rename / disable / delete projects. The company name is
   "Lion Enviro <project name>" everywhere (top bar, login, reports, Excel files). The "Employee Code Prefix" gives codes like LEB00001.
 * Every project has its own zones, wards, employees, vehicles, routes, trackers, holidays and attendance. Nothing is shared.
 * Users & Access > Project Access: tick the project(s) a user may open. A Super Admin can open every project.
 * Login is in two steps: type the username -> the app checks it and shows the user's project(s) -> only then the password box appears.
   An unknown username (or one with no project) never gets a password box.
 * The top bar has a project switcher (for users with more than one project).
 * First start after the upgrade: your existing data becomes project "Lucknow" (prefix LEL) and existing users get access to it.
   Zone name, Route ID and Holiday date are now unique PER PROJECT (SQLite is converted automatically; on MySQL/PostgreSQL drop the
   old unique key on zone.name and route.rkey by hand). Vehicle numbers and Tracker IDs stay unique across all projects.


NEW (v4.6): FASTER + NEW LOADER.
 * Loader: a thin orange/navy progress bar on every page change, and a glass card with the logo ring only when something takes
   longer than ~0.25 s (save, delete, big report, Excel download). Fast pages show no overlay at all - the old loader always held
   the page for about 0.7 s. A double click on Save / Delete can no longer submit twice.
 * Fewer database queries: Dashboard 52 -> 22, Ward Reports (all wards) 170 -> 20, every page about 4 fewer.
 * Attendance sheet builds about 3x faster (150+ employees), logo 322 KB -> 18 KB, static files cached for a year (versioned),
   SQLite memory-mapped reads.


NEW (v4.7): SEARCH BOXES for Vehicle Number, Route ID and Tracker ID on the employee form.
 * Designation Driver / Helper -> Vehicle Number + Route ID;  Trolleyman -> Route ID + Tracker ID.
 * Click the box to see the first 30, or type a few digits / letters (any part of the number) - the list narrows at once.
   Arrow keys + Enter, Esc and the x button work; matches that START with your text come first.
 * The list is searched on the server (30 at a time), so 5,000+ vehicles do not slow the page; the form page is also lighter.
 * Only items of the current project, the chosen zone and the user's own zone / ward access are offered.


NEW (v4.8): LOGIN PAGE LAYOUT.
 * The card stays in the same place when the password step opens (it used to jump), and 1366x768 laptops and phones need no scrolling.
 * Soft brand background and tinted left panel, transparent logo (no white box), bigger touch-size fields and Login button,
   "Next" is an arrow-only button on phones, narrow 320 px phones and short landscape screens fit, no keyboard pop-up on phones at open,
   the password step fades in, the page keeps the username after a wrong password.
