# -*- coding: utf-8 -*-
# This file is part of SGS-Flask.

# SGS-Flask is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# SGS-Flask is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

# Copyright Swallowtail Garden Seeds, Inc

"""
wsgi

This is the module used to run sgs-flask in production mode via uWSGI.

Notes:
    On Environment Variables:

    Since a separate environment is created when running via uWSGI, environment
    variables must be set within that environment, which can only be done here
    or in the sgs-flask.ini file. Since that means storing sensitive data
    (such as the SQL database password) in plaintext is unavoidable, the
    environment variables should be set via ~.config/sgs_envs.json which at
    least stores that data in a place unlikely to be accessible to anyone who
    has not gained access to the account running sgs-flask.

    The layout for sgs_envs.json is as follows, replacing values in <>:

    {
        "SGS_SERVER_NAME": "<domain of server>";
        "SGS_DATABASE_URI": "<uri of database>";
    }

    Initial Setup Needed:

    (Note: These instructions assume you are using Ubuntu Server 16.04 LTS)

    Several things must be set up before you can actually run sgs-flask via
    uWSGI. First, you need a systemd unit for running uWSGI:

    Create/edit the file /etc/systemd/system/sgs-flask.service

    The file should be as follows, replacing values in <>:

    [Unit]
    Description=uWSGI instance for sgs-flask
    After=network.target

    [Service]
    User=<username>
    Group=www-data
    WorkingDirectory=/<path>/<to>/sgs-flask
    Environment="PATH=/<path>/<to>/sgs-flask/venv/bin"
    ExecStart=/<path>/<to>/sgs-flask/venv/bin/uwsgi --need-app 
        --backtrace-depth=100 --ini sgs-flask.ini

    [Install]
    WantedBy=multi-user.target

    (Note: the ExecStart bit is continued and indented to fit the docstring,
    but it should all be on the same line.)
    With that file created, you should be able to run sgs-flask with the
    command `sudo systemctl start sgs-flask`. Be sure to check the status
    of the new service to make sure it is running and there are no errors with
    the command `systemctl status sgs-flask`.


    Once it works, you will need to configure nginx to use it. Create/edit the
    file /etc/nginx/sites-available/sgs-flask.

    The file should be as follows, replacing values in <>:

    server {
        listen 80;
        server_name <domain of server>;

        location /static {
            alias /<path>/<to>/sgs-flask/app/static;
        }

        location / {
            include uwsgi_params;
            uwsgi_pass unix:/<path>/<to>/sgs-flask/sgs-flask.sock;
        }
    }

    You'll also need to symlink it into sites-enabled like so:
    `sudo ln -s /etc/nginx/sites-available/sgs-flask /etc/nginx/sites-enabled`

    Now you should test using `sudo nginx -t`, and if it looks okay you can
    restart nginx with `sudo systemctl restart nginx`.

    Now if all went well, you should be able to access sgs-flask from a web
    browser at the domain provided!
    """


import json
import os
from pathlib import Path
import sys

sgs_envs_file = Path(Path.home(), '.config', 'sgs_envs.json')

try:
    with sgs_envs_file.open('r', encoding='utf-8') as ifile:
        envs = json.loads(ifile.read())
except FileNotFoundError:
    raise FileNotFoundError(
        'The file "{}" is needed to run sgs-flask in production mode! Please '
        'see sgs-flask/wsgi.py for details on what should be in that file.'
        .format(sgs_envs_file)
    )

for k, v in envs.items():
    os.environ[k] = v

# A database URI must be set otherwise there can be no database!
if 'SGS_DATABASE_URI' not in os.environ:
    raise ValueError(
        'No database URI has been set! Please make sure SGS_DATABASE_URI is '
        'set in the file "{}"!'.format(sgs_envs_file)
    )

from app import create_app

app = create_app('production')

if __name__ == '__main__':
    app.run()
