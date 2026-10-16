"""Alert channels: console, email (SMTP) and Microsoft Teams incoming webhooks.

Every channel is configured from environment variables, and a channel whose variables are
missing is simply not enabled, so the same code runs locally (console only) and in production.
"""

from __future__ import annotations

import logging
import os
import smtplib
from collections.abc import Sequence
from email.message import EmailMessage
from typing import Protocol

import requests

from opsmon.anomaly import Anomaly
from opsmon.runner import MonitorResult

log = logging.getLogger(__name__)


class AlertChannel(Protocol):
    def send(self, subject: str, body: str) -> None: ...


class ConsoleAlert:
    def send(self, subject: str, body: str) -> None:
        log.warning("%s\n%s", subject, body)


class EmailAlert:
    def __init__(
        self,
        host: str,
        port: int,
        user: str,
        password: str,
        sender: str,
        recipients: Sequence[str],
    ) -> None:
        self.host = host
        self.port = port
        self.user = user
        self.password = password
        self.sender = sender
        self.recipients = list(recipients)

    def send(self, subject: str, body: str) -> None:
        msg = EmailMessage()
        msg["Subject"] = subject
        msg["From"] = self.sender
        msg["To"] = ", ".join(self.recipients)
        msg.set_content(body)
        with smtplib.SMTP(self.host, self.port, timeout=30) as smtp:
            smtp.starttls()
            if self.user:
                smtp.login(self.user, self.password)
            smtp.send_message(msg)


class TeamsWebhookAlert:
    def __init__(self, url: str) -> None:
        self.url = url

    def send(self, subject: str, body: str) -> None:
        text = f"**{subject}**\n\n" + body.replace("\n", "  \n")
        response = requests.post(self.url, json={"text": text}, timeout=15)
        response.raise_for_status()


def channels_from_env() -> list[AlertChannel]:
    channels: list[AlertChannel] = [ConsoleAlert()]
    host = os.getenv("SMTP_HOST")
    recipients = [r.strip() for r in os.getenv("ALERT_EMAIL_TO", "").split(",") if r.strip()]
    if host and recipients:
        channels.append(
            EmailAlert(
                host=host,
                port=int(os.getenv("SMTP_PORT", "587")),
                user=os.getenv("SMTP_USER", ""),
                password=os.getenv("SMTP_PASSWORD", ""),
                sender=os.getenv("ALERT_EMAIL_FROM") or os.getenv("SMTP_USER", ""),
                recipients=recipients,
            )
        )
    webhook = os.getenv("TEAMS_WEBHOOK_URL")
    if webhook:
        channels.append(TeamsWebhookAlert(webhook))
    return channels


def build_alert(
    anomalies: Sequence[Anomaly], failed: Sequence[MonitorResult]
) -> tuple[str, str] | None:
    """Return ``(subject, body)`` describing what needs attention, or ``None`` if all is well."""
    if not anomalies and not failed:
        return None
    critical = sum(1 for a in anomalies if a.severity == "critical")
    parts = []
    if anomalies:
        parts.append(f"{len(anomalies)} anomal{'y' if len(anomalies) == 1 else 'ies'}")
    if failed:
        parts.append(f"{len(failed)} failed monitor{'' if len(failed) == 1 else 's'}")
    level = "CRITICAL" if critical or failed else "WARNING"
    subject = f"[{level}] Payments ops monitor: {', '.join(parts)}"

    lines: list[str] = []
    if anomalies:
        lines.append("Anomalies:")
        lines.extend(f"  - {a.describe()}" for a in anomalies)
    if failed:
        lines.append("Failed monitors:")
        lines.extend(f"  - {r.name}: {r.error}" for r in failed)
    return subject, "\n".join(lines)


def dispatch(channels: Sequence[AlertChannel], subject: str, body: str) -> int:
    """Send to every channel; one broken channel must not silence the others."""
    delivered = 0
    for channel in channels:
        try:
            channel.send(subject, body)
            delivered += 1
        except Exception:
            log.exception("Alert channel %s failed", type(channel).__name__)
    return delivered
