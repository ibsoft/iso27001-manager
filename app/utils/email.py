from flask_mail import Message
from flask import render_template, current_app
from app.extensions import mail


def send_email(to, subject, html_body):
    try:
        msg = Message(subject, recipients=[to], html=html_body)
        mail.send(msg)
        return True
    except Exception as e:
        current_app.logger.error(f"Failed to send email to {to}: {e}")
        return False
