"""Notifications."""
def send_email(to, subject, body, mailer): return mailer.send(to, subject, body)
def send_sms(to, msg, sms): return sms.send(to, msg)
