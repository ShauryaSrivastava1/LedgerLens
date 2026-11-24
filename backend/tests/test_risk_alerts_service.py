import datetime
from decimal import Decimal

from app import models
from app.services.risk_alerts import check_shareholding_alerts, check_report_alerts


def _company(db_session, symbol="ALERTCO"):
    c = models.Company(symbol=symbol, name=f"{symbol} Ltd")
    db_session.add(c)
    db_session.commit()
    db_session.refresh(c)
    return c


def _shareholding(company_id, pledge, promoter, date):
    return models.ShareholdingPattern(
        company_id=company_id, period_end_date=date, pledge_pct=Decimal(str(pledge)),
        promoter_holding_pct=Decimal(str(promoter)),
    )


def test_no_alert_without_previous_record(db_session):
    company = _company(db_session)
    new = _shareholding(company.id, 5, 70, datetime.date(2025, 3, 31))
    alerts = check_shareholding_alerts(db_session, company, new, None)
    assert alerts == []


def test_pledge_increase_triggers_alert(db_session):
    company = _company(db_session)
    previous = _shareholding(company.id, 1.0, 70, datetime.date(2024, 3, 31))
    new = _shareholding(company.id, 6.0, 70, datetime.date(2025, 3, 31))
    alerts = check_shareholding_alerts(db_session, company, new, previous)
    assert len(alerts) == 1
    assert alerts[0].alert_type == models.RiskAlertType.PLEDGE_INCREASE
    assert alerts[0].severity == models.RiskAlertSeverity.HIGH  # delta >= 5


def test_small_pledge_increase_below_threshold_no_alert(db_session):
    company = _company(db_session)
    previous = _shareholding(company.id, 1.0, 70, datetime.date(2024, 3, 31))
    new = _shareholding(company.id, 1.2, 70, datetime.date(2025, 3, 31))
    alerts = check_shareholding_alerts(db_session, company, new, previous)
    assert alerts == []


def test_promoter_holding_decrease_triggers_alert(db_session):
    company = _company(db_session)
    previous = _shareholding(company.id, 0, 72.0, datetime.date(2024, 3, 31))
    new = _shareholding(company.id, 0, 68.0, datetime.date(2025, 3, 31))
    alerts = check_shareholding_alerts(db_session, company, new, previous)
    assert len(alerts) == 1
    assert alerts[0].alert_type == models.RiskAlertType.PROMOTER_HOLDING_DECREASE


def test_both_alerts_can_fire_together(db_session):
    company = _company(db_session)
    previous = _shareholding(company.id, 1.0, 72.0, datetime.date(2024, 3, 31))
    new = _shareholding(company.id, 8.0, 68.0, datetime.date(2025, 3, 31))
    alerts = check_shareholding_alerts(db_session, company, new, previous)
    types = {a.alert_type for a in alerts}
    assert types == {models.RiskAlertType.PLEDGE_INCREASE, models.RiskAlertType.PROMOTER_HOLDING_DECREASE}


def _report(company_id, overall, governance, generated_at):
    return models.AIReport(
        company_id=company_id, llm_provider="fake", llm_model="fake", overall_score=Decimal(str(overall)),
        governance_score=Decimal(str(governance)), confidence_score=Decimal("0.5"), summary="test",
        generated_at=generated_at,
    )


def test_governance_score_drop_triggers_alert(db_session):
    company = _company(db_session)
    previous = _report(company.id, 70, 80, datetime.datetime(2025, 1, 1))
    new = _report(company.id, 70, 60, datetime.datetime(2025, 6, 1))  # dropped 20
    alerts = check_report_alerts(db_session, company, new, previous)
    governance_alerts = [a for a in alerts if a.alert_type == models.RiskAlertType.GOVERNANCE_SCORE_DROP]
    assert len(governance_alerts) == 1
    assert governance_alerts[0].severity == models.RiskAlertSeverity.HIGH  # delta >= 20


def test_overall_score_drop_triggers_alert(db_session):
    company = _company(db_session)
    previous = _report(company.id, 75, 80, datetime.datetime(2025, 1, 1))
    new = _report(company.id, 60, 80, datetime.datetime(2025, 6, 1))  # dropped 15
    alerts = check_report_alerts(db_session, company, new, previous)
    overall_alerts = [a for a in alerts if a.alert_type == models.RiskAlertType.OVERALL_SCORE_DROP]
    assert len(overall_alerts) == 1


def test_score_improvement_triggers_no_alert(db_session):
    company = _company(db_session)
    previous = _report(company.id, 60, 60, datetime.datetime(2025, 1, 1))
    new = _report(company.id, 80, 80, datetime.datetime(2025, 6, 1))
    alerts = check_report_alerts(db_session, company, new, previous)
    assert alerts == []
