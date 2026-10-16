from opsmon.alerts import build_alert, dispatch
from opsmon.anomaly import Anomaly
from opsmon.runner import MonitorResult


def test_no_alert_when_everything_is_fine():
    assert build_alert([], []) is None


def test_alert_lists_anomalies_and_failures():
    anomaly = Anomaly("not_success_spike", "ROCKET", 150, 2.5, 60.0, "critical")
    failed = MonitorResult("money_flow_daily", False, error="OperationalError: timeout")

    subject, body = build_alert([anomaly], [failed])

    assert subject.startswith("[CRITICAL]")
    assert "1 anomaly" in subject and "1 failed monitor" in subject
    assert "ROCKET" in body and "money_flow_daily" in body


def test_warning_only_alert():
    anomaly = Anomaly("rule", "NPSB", 40, 20, 2.0, "warning")

    subject, _ = build_alert([anomaly], [])

    assert subject.startswith("[WARNING]")


def test_dispatch_survives_a_broken_channel():
    sent = []

    class Broken:
        def send(self, subject, body):
            raise ConnectionError("smtp down")

    class Recorder:
        def send(self, subject, body):
            sent.append(subject)

    delivered = dispatch([Broken(), Recorder()], "subject", "body")

    assert delivered == 1
    assert sent == ["subject"]
