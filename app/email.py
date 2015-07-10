from threading import Thread
from flask import current_app, render_template
from flask.ext.mail import Message
from app import mail


def send_message(app, msg):
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


def send_email(to, subject, template, **kwargs):
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
