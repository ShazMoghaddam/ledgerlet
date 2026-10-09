"""The sample data must produce exactly the figures the design boards show."""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from scripts.seed_demo import seed
from tests.auth import ISSUER, headers

API = "/api/v1"


def test_sample_data_matches_the_designs(client: TestClient, db_session: Session) -> None:
    seed(db_session, ISSUER, "demo")

    summary = client.get(
        f"{API}/tax/summary", params={"tax_year": 2026, "quarter": 2}, headers=headers("demo")
    ).json()
    assert summary["totals"] == {
        "income": "12000.00",
        "expenses": "1816.40",
        "residential_finance_costs": "2940.00",
        "profit": "10183.60",
    }
    by_property = {p["nickname"]: p for p in summary["properties"]}
    assert by_property["Elm Court"]["totals"]["expenses"] == "1336.40"
    assert by_property["Oak Road"]["totals"]["expenses"] == "480.00"
    assert by_property["Oak Road"]["totals"]["income"] == "4800.00"
    assert sum(p["transaction_count"] for p in summary["properties"]) == 29

    page = client.get(f"{API}/transactions", headers=headers("demo")).json()
    assert (page["total"], page["money_in"], page["money_out"]) == (29, "12000.00", "4756.40")
    assert page["items"][0]["description"] == "Boiler service"


def test_seeding_twice_adds_nothing(client: TestClient, db_session: Session) -> None:
    seed(db_session, ISSUER, "demo")
    with pytest.raises(SystemExit):
        seed(db_session, ISSUER, "demo")
    page = client.get(f"{API}/transactions", headers=headers("demo")).json()
    assert page["total"] == 29
