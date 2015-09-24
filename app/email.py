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


from threading import Thread
from flask import current_app, render_template
from flask.ext.mail import Message
from app import mail


def send_message(app, msg):  # pragma: no cover
    """Send a message via Flask-Mail.

    Note:
        This function should only be called from within a function that will
        run it within its own thread or process, as it is slow and will cause
        whatever Flask app instance it is run through to hang until finished
        sending the email.

    Args:
        app (Flask): The Flask application instance we need the context
            from for context-specific elements of the message to send.
        msg (Message): The Flask-Mail Message object we are sending.
    """
    with app.app_context():
        mail.send(msg)


def send_email(to, subject, template, **kwargs):  # pragma: no cover
    """Send an email via Flask-Mail in a separate thread.

    This function handles formatting the email to send, and spawning a new
    thread to send the message in, so as to avoid bogging down the Flask
    instance that requested to send an email.

    Args:
        to (List[str]): Email addresses to send the message to.
        subject (str): Subject line of email.
        template (str): Name of template to use to format the message.

    Returns:
        thr (Thread): The thread the message is sent in.
    """
    app = current_app._get_current_object()
    msg = Message(
        app.config['EMAIL_SUBJECT_PREFIX'] + subject,
        sender=app.config['INFO_EMAIL'],
        recipients=[to])
    msg.body = render_template(template + '.txt', **kwargs)
    msg.html = render_template(template + '.html', **kwargs)
    thr = Thread(target=send_message, args=[app, msg])
    thr.start()
    return thr
