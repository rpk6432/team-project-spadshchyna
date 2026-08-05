import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape

from config import settings
from tasks import app

_templates = Environment(
    loader=FileSystemLoader(Path(__file__).resolve().parent / "templates"),
    autoescape=select_autoescape(["html"]),
)


def _send_email(to: str, subject: str, template_name: str, **ctx: object) -> None:
    logo_url = f"{settings.s3_public_url}/{settings.s3_bucket}/static/logo.png"
    ctx["logo_url"] = logo_url
    html = _templates.get_template(f"{template_name}.html").render(**ctx)
    text = _templates.get_template(f"{template_name}.txt").render(**ctx)

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = settings.smtp_from
    msg["To"] = to
    msg.attach(MIMEText(text, "plain"))
    msg.attach(MIMEText(html, "html"))

    with smtplib.SMTP(settings.smtp_host, settings.smtp_port) as server:
        server.sendmail(settings.smtp_from, to, msg.as_string())


@app.task(autoretry_for=(Exception,), retry_backoff=True, max_retries=5)
def send_welcome_email(email: str, first_name: str) -> None:
    _send_email(
        to=email,
        subject="Welcome to Spadshchyna!",
        template_name="welcome",
        first_name=first_name,
    )


@app.task(autoretry_for=(Exception,), retry_backoff=True, max_retries=5)
def send_booking_confirmed(
    email: str,
    first_name: str,
    homestead_name: str,
    check_in: str,
    check_out: str,
    total: int,
) -> None:
    _send_email(
        to=email,
        subject="Your booking is confirmed!",
        template_name="booking_confirmed",
        first_name=first_name,
        homestead_name=homestead_name,
        check_in=check_in,
        check_out=check_out,
        total=total,
    )


@app.task(autoretry_for=(Exception,), retry_backoff=True, max_retries=5)
def send_reset_code_email(email: str, first_name: str, code: str) -> None:
    _send_email(
        to=email,
        subject="Your password reset code",
        template_name="reset_password",
        first_name=first_name,
        code=code,
    )
