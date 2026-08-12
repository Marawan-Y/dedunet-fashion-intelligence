"""What each commerce mode must tell a customer about itself.

Post-acceptance issue A. The storefront's top banner was a fixed sentence in the markup:

    "Prototype storefront. Preview only -- nothing here is available to purchase, and no
     real order is placed or card charged."

Human acceptance ran the whole sandbox journey -- synthetic stock, a cart, a declined
payment, a successful one, a fulfilment -- underneath a banner insisting that nothing was
available to purchase. The transaction behaviour was right; the disclosure was false.

The mode is authoritative and lives here, so the wording lives here too. These tests are
about the CONTENT of the disclosure rather than about any one surface rendering it: if
`describe()` is wrong, both clients are wrong, and no amount of DOM testing would catch it.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.commerce import modes
from app.main import app

client = TestClient(app)

MODE_ENDPOINT = "/api/v1/commerce/mode"


def get_mode(monkeypatch, value: str | None) -> dict:
    """The endpoint's answer with `COMMERCE_MODE` set to `value`."""

    if value is None:
        monkeypatch.delenv("COMMERCE_MODE", raising=False)
    else:
        monkeypatch.setenv("COMMERCE_MODE", value)
    response = client.get(MODE_ENDPOINT)
    assert response.status_code == 200, response.text
    return response.json()


# --------------------------------------------------- preview says preview, and only that


def test_preview_mode_states_that_nothing_can_be_purchased(monkeypatch):
    body = get_mode(monkeypatch, modes.BRAND_PREVIEW)

    assert body["mode"] == "BRAND_PREVIEW_MODE"
    assert body["headline"] == "Preview only."
    assert "Nothing here is available to purchase." in body["detail"]
    assert "No order or payment can be completed." in body["detail"]
    assert body["purchasable"] is False
    assert body["payments"] == "none"


def test_preview_mode_does_not_mention_a_payment_adapter(monkeypatch):
    """A mode where no payment call is reachable must not describe how payments work.

    The mobile client's fixed notice used to say payments "run against a sandbox adapter",
    which in preview mode invites a customer to try one.
    """

    text = " ".join(get_mode(monkeypatch, modes.BRAND_PREVIEW)["detail"]).lower()

    assert "sandbox" not in text
    assert "adapter" not in text


# ------------------------------------------- commerce-test says sandbox, and says it plainly


def test_commerce_test_mode_states_that_it_is_a_test(monkeypatch):
    body = get_mode(monkeypatch, modes.COMMERCE_TEST)

    assert body["mode"] == "COMMERCE_TEST_MODE"
    assert body["headline"] == "Internal commerce test mode."
    assert body["purchasable"] is True
    assert body["payments"] == "sandbox"


def test_commerce_test_mode_discloses_synthetic_stock_and_sandbox_payment(monkeypatch):
    detail = get_mode(monkeypatch, modes.COMMERCE_TEST)["detail"]

    assert "Only synthetic test inventory is available." in detail
    assert "Payments use the sandbox adapter." in detail
    assert "No real card is charged." in detail
    assert "No real stock or fulfilment is involved." in detail


def test_commerce_test_mode_never_claims_a_real_payment_or_shipment(monkeypatch):
    """The one sentence this mode must never be able to produce.

    A test order that reads as a real purchase is the failure this whole programme is
    arranged against -- it is the same defect the admin TEST ORDER label closed, one surface
    earlier.
    """

    body = get_mode(monkeypatch, modes.COMMERCE_TEST)
    text = (body["headline"] + " " + " ".join(body["detail"])).lower()

    for claim in ("your card has been charged", "your order will ship", "real payment"):
        assert claim not in text

    # "real" may appear only in a negation.
    for sentence in body["detail"]:
        if "real" in sentence.lower():
            assert sentence.lower().startswith("no real"), sentence

    assert body["payments"] != "real"
    assert body["public_commerce_enabled"] is False


def test_the_test_mode_disclosure_is_not_hidden_behind_a_euphemism(monkeypatch):
    """It must be recognisable as a test at a glance, not softened into marketing."""

    body = get_mode(monkeypatch, modes.COMMERCE_TEST)
    assert "test" in body["headline"].lower()


# --------------------------------------------------- the two modes may not share sentences


def test_no_sentence_is_reused_between_the_two_modes(monkeypatch):
    """A shared line is how "no card is charged" ends up on a screen where one could be.

    This is the guard against the copy collapsing back into one message: if a future edit
    makes both modes say the same thing, the disclosure stops distinguishing them and the
    original defect is back in a new form.
    """

    preview = get_mode(monkeypatch, modes.BRAND_PREVIEW)
    commerce_test = get_mode(monkeypatch, modes.COMMERCE_TEST)

    assert preview["headline"] != commerce_test["headline"]
    shared = set(preview["detail"]) & set(commerce_test["detail"])
    assert not shared, f"modes share disclosure sentences: {sorted(shared)}"


def test_the_two_modes_disagree_about_whether_anything_can_be_bought(monkeypatch):
    """The flags, not only the prose. A client may assert on either."""

    preview = get_mode(monkeypatch, modes.BRAND_PREVIEW)
    commerce_test = get_mode(monkeypatch, modes.COMMERCE_TEST)

    assert preview["purchasable"] != commerce_test["purchasable"]
    assert preview["payments"] != commerce_test["payments"]


def test_preview_copy_never_appears_in_test_mode(monkeypatch):
    """Specifically the sentence human acceptance saw on screen during a sandbox purchase."""

    detail = get_mode(monkeypatch, modes.COMMERCE_TEST)["detail"]
    assert "Nothing here is available to purchase." not in detail
    assert "No order or payment can be completed." not in detail


# ------------------------------------------------- refused and unknown modes are their own


def test_public_commerce_mode_reports_blocked_rather_than_ordinary_commerce(monkeypatch):
    """`current_mode()` refuses it. The disclosure must not silently become a working mode.

    Answering 200 with a BLOCKED body rather than 500 is deliberate: a client that receives
    an unexplained error keeps whatever its markup shipped with, which is the defect being
    closed. The refusal itself is unchanged and asserted below.
    """

    body = get_mode(monkeypatch, "PUBLIC_COMMERCE_MODE")

    assert body["mode"] is None
    assert body["purchasable"] is False
    assert body["payments"] == "none"
    assert body["public_commerce_enabled"] is False
    assert "Nothing here is available to purchase." in body["detail"]


def test_the_blocked_disclosure_is_not_the_preview_disclosure(monkeypatch):
    """"Preview only" would be a lie about a deployment that is simply misconfigured."""

    blocked = get_mode(monkeypatch, "PUBLIC_COMMERCE_MODE")
    preview = get_mode(monkeypatch, modes.BRAND_PREVIEW)

    assert blocked["headline"] != preview["headline"]
    assert blocked["headline"] == "Commerce is unavailable."


def test_an_unknown_mode_is_reported_as_blocked_not_guessed(monkeypatch):
    body = get_mode(monkeypatch, "SOMETHING_ELSE")

    assert body["mode"] is None
    assert body["purchasable"] is False


def test_reporting_a_blocked_mode_does_not_make_it_reachable(monkeypatch):
    """The endpoint answers; the guard still refuses. Disclosure is not authorisation."""

    monkeypatch.setenv("COMMERCE_MODE", "PUBLIC_COMMERCE_MODE")

    assert client.get(MODE_ENDPOINT).status_code == 200
    with pytest.raises(modes.CommerceModeError, match="cannot be enabled by configuration"):
        modes.current_mode()
    with pytest.raises(modes.CommerceModeError):
        modes.assert_purchasable(sellable=True, product_name="Anything")
    assert modes.public_commerce_enabled() is False


def test_public_commerce_is_never_reported_as_enabled(monkeypatch):
    for value in (modes.BRAND_PREVIEW, modes.COMMERCE_TEST, "PUBLIC_COMMERCE_MODE", "NONSENSE"):
        assert get_mode(monkeypatch, value)["public_commerce_enabled"] is False


# ------------------------------------------------------------------------- shape and access


def test_the_default_mode_is_reported_when_none_is_configured(monkeypatch):
    """An empty `COMMERCE_MODE` applies `DEFAULT_MODE`; the banner must follow it."""

    body = get_mode(monkeypatch, None)
    assert body["mode"] == modes.DEFAULT_MODE


def test_the_disclosure_needs_no_authentication(monkeypatch):
    """A visitor must be told what this is before signing in, or there is no point to it."""

    monkeypatch.setenv("COMMERCE_MODE", modes.BRAND_PREVIEW)
    response = client.get(MODE_ENDPOINT)  # no Authorization header
    assert response.status_code == 200
    assert response.json()["mode"] == "BRAND_PREVIEW_MODE"


def test_every_mode_returns_a_renderable_disclosure(monkeypatch):
    """No mode may produce an empty headline or an empty detail list.

    A client that receives one falls back to its shipped text, so an empty disclosure is a
    silent regression rather than a visible one.
    """

    for value in (modes.BRAND_PREVIEW, modes.COMMERCE_TEST, "PUBLIC_COMMERCE_MODE"):
        body = get_mode(monkeypatch, value)
        assert body["headline"].strip()
        assert body["detail"], value
        assert all(isinstance(line, str) and line.strip() for line in body["detail"])


def test_describe_is_used_by_the_endpoint_rather_than_reimplemented(monkeypatch):
    """One author for the disclosure. Two would drift, which is the defect one level up."""

    monkeypatch.setenv("COMMERCE_MODE", modes.COMMERCE_TEST)
    assert client.get(MODE_ENDPOINT).json() == modes.describe(modes.COMMERCE_TEST)
