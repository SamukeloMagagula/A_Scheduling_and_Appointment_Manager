# Scheduling & Time Management — Backend

Flask + SQLAlchemy + MariaDB. JSON API only; the HTML pages in the
project root stay as they are and get wired up with small JS files in a
later step.

## Layout

    backend/
      app.py              Flask app factory and entry point
      config.py           reads .env
      db.py               SQLAlchemy engine + session
      models.py           ORM models (mirror of schema.sql)
      auth.py             stub current_user; swap for real login later
      logging_helpers.py  one-line audit helper
      blueprints/
        entries.py        time entries (owner-only writes)
        users.py          /api/me, user search
        teams.py          team calendar week
        department.py     department overview
        timesheet.py      monthly timesheet + CSV export
        customers.py      admin-only customer CRUD
        projects.py       admin-only project CRUD
        logs.py           activity log (manager/admin)
      schema.sql          MariaDB DDL
      requirements.txt
      .env.example

## Database setup

1. Install MariaDB.
2. Create a MariaDB user the app will connect as:

       CREATE USER 'scheduling_app'@'localhost' IDENTIFIED BY '<pick one>';
       GRANT ALL PRIVILEGES ON scheduling_manager.* TO 'scheduling_app'@'localhost';
       FLUSH PRIVILEGES;

3. Create the schema and tables:

       mysql -u root -p < schema.sql

4. Insert at least one department, team and user so the stub login works:

       USE scheduling_manager;
       INSERT INTO departments (name) VALUES ('Engineering');
       INSERT INTO teams (name, department_id) VALUES ('Core', 1);
       INSERT INTO users (email, name, role, team_id)
           VALUES ('you@example.com', 'Your Name', 'admin', 1);

   Note the id of that first user — put it in `.env` as `STUB_USER_ID`.

## Running

    cd backend
    python -m venv .venv
    .venv\Scripts\activate         (PowerShell: .venv\Scripts\Activate.ps1)
    pip install -r requirements.txt
    copy .env.example .env         (then edit DB_* and STUB_USER_ID)
    python app.py

Open http://127.0.0.1:5000/ — the static pages render, and the JSON API
lives under http://127.0.0.1:5000/api/.

## API quick reference

Reads are open to any logged-in user. Writes are owner- or role-checked.

    GET    /api/me

    GET    /api/entries?user_id=&from=YYYY-MM-DD&to=YYYY-MM-DD
    POST   /api/entries                   {date,start,end,type,project_id?,customer_id?,notes?}
    PATCH  /api/entries/<id>              (owner only)
    DELETE /api/entries/<id>              (owner only)

    GET    /api/users?team_id=&q=

    GET    /api/teams
    GET    /api/teams/<id>/week?start=YYYY-MM-DD

    GET    /api/department

    GET    /api/timesheet?user_id=&month=YYYY-MM
    GET    /api/timesheet/export.csv?user_id=&month=YYYY-MM

    GET    /api/customers?active=1
    POST   /api/customers                 (admin only) {name}
    PATCH  /api/customers/<id>            (admin only)
    DELETE /api/customers/<id>            (admin only, soft-delete)

    GET    /api/projects?active=1
    POST   /api/projects                  (admin only) {name}
    PATCH  /api/projects/<id>             (admin only)
    DELETE /api/projects/<id>             (admin only, soft-delete)

    GET    /api/logs?limit=200&q=         (manager/admin only)

### Business rules

- A user's entries cannot overlap on the same day (409 on conflict).
- `end_time > start_time` is enforced both in Python and as a CHECK in the DB.
- Deleting a customer or project soft-deactivates it; historical entries keep the link.
- Every write appends one row to `activity_log`.

## Replacing the stub auth

`backend/auth.py` is the only file that knows who the current user is.
Replace `_load_stub_user` with a session cookie reader when login is
built; nothing else in the code needs changing.
