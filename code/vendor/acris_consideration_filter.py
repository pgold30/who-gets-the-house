"""acris_consideration_filter — flag ACRIS deeds whose recorded consideration is
set by a legal rule rather than negotiated.

Usage
-----
    from acris_consideration_filter import classify_parties
    events = classify_parties(parties_df)   # columns: document_id, party_type, name
    # -> one row per document: event, amount_is_market, lender_grantee, ...

    python acris_consideration_filter.py "WELLS FARGO BANK, NA" "NGUYEN, LOAN"

Event taxonomy (Table 1 of the paper)
-------------------------------------
  LENDER_ACQ_REFEREE  referee's deed to a lender or agency: foreclosure
                      take-back; amount is the (credit) bid
  LENDER_ACQ_OTHER    non-referee grantor -> lender: deed in lieu or
                      post-foreclosure conveyance; NY Tax Law 1401(d) counts
                      the debt discharged as consideration
  LENDER_TO_LENDER    lender -> lender or agency (servicer to trust, bank to
                      Fannie Mae, HUD claim conveyance)
  AUCTION_THIRD_PARTY referee's deed to a non-lender: competitive auction bid
  LENDER_RESALE       lender -> non-lender: REO liquidation, a market sale
  ORDINARY            none of the above

`amount_is_market` is False for the first three. Third-party auctions are
flagged separately; whether they belong in a price index is the user's choice.

Design rules, learned the hard way
----------------------------------
* No single ambiguous word is a token. A bare N.A. matched Korean and Chinese
  surnames ("CHEN, NA"); a bare LOAN matches the Vietnamese given name
  ("NGUYEN, LOAN"); CHASE, AURORA, SELENE, CARRINGTON and BAYVIEW are names
  of people or streets. Each is used only inside an institutional phrase.
* A name written "SURNAME, GIVEN" whose surname is itself a token ("BANK,
  MICHAEL") is treated as a person unless a corporate marker is present.
* `narrow` tokens are the default. `broad` adds generic finance words
  (FUNDING, FINANCE, CAPITAL...) and series-code patterns; it raises recall
  and lowers precision. Both are reported in the paper.
"""
import re
import sys

__version__ = "1.1.0"


def normalize(name):
    s = (name or "").upper().replace("&", " AND ").replace(".", "")
    return re.sub(r"\s+", " ", re.sub(r"[^A-Z0-9, ]", " ", s)).strip()


def _rx(words):
    return re.compile(r"\b(?:" + "|".join(words) + r")\b")


AGENCY = _rx([
    r"FANNIE MAE", r"FEDERAL NATIONAL MORTGAGE", r"FREDDIE MAC",
    r"FEDERAL HOME LOAN MORTGAGE", r"GOVERNMENT NATIONAL MORTGAGE",
    r"SECRETARY OF (?:THE )?(?:DEPARTMENT OF )?(?:HOUSING|HUD)",
    r"HOUSING AND URBAN DEVELOPMENT", r"SECRETARY OF VETERANS",
    r"VETERANS AFFAIRS", r"FEDERAL DEPOSIT INSURANCE"])

BANK = _rx([
    r"BANK", r"BANCORP", r"BANKING", r"SAVINGS", r"NATIONAL ASSOCIATION", r"FSB",
    r"CREDIT UNION", r"MORTGAGE", r"[A-Z]+MORTGAGE", r"MTG", r"SERVICING",
    r"SERVICER", r"HOME LOANS?", r"LOAN SERVIC[A-Z]*", r"LOAN TRUST",
    r"(?:SAVINGS|INVESTMENT|BUILDING) AND LOAN", r"LENDING",
    r"LOANS?,? (?:CORP|CORPORATION|COMPANY|CO|INC|LLC|ASSOCIATION|SERVICES|FUND|ACQUISITION)"])

SECURITIZATION = _rx([
    r"CERTIFICATE ?HOLDERS", r"PASS ?THROUGH", r"ASSET ?BACKED",
    r"LEGAL TITLE TRUST", r"PARTICIPATION TRUST", r"REMIC", r"SECURITIZATION",
    r"REO"])

NAMED = _rx([
    r"NATIONSTAR", r"OCWEN", r"SELENE FINANCE", r"BAYVIEW (?:LOAN|ASSET|FINANCIAL)",
    r"MTGLQ", r"RUSHMORE LOAN", r"SHELLPOINT", r"NEWREZ", r"DITECH", r"SETERUS",
    r"GREEN TREE", r"LAKEVIEW LOAN", r"CALIBER HOME", r"PENNYMAC", r"PHH MORTGAGE", r"GMAC",
    r"COUNTRYWIDE", r"WASHINGTON MUTUAL", r"WILMINGTON TRUST", r"CHRISTIANA TRUST",
    r"WELLS FARGO", r"HSBC", r"CITIBANK", r"CITIGROUP", r"CITICORP", r"JPMORGAN",
    r"JP MORGAN", r"CHASE (?:HOME|MANHATTAN)", r"INDYMAC", r"ONEWEST",
    r"AURORA LOAN", r"OPTION ONE", r"AMERIQUEST", r"LITTON LOAN",
    r"HOMEWARD RESIDENTIAL", r"VRMTG", r"VENTURES TRUST", r"LSF\d+", r"EMIGRANT",
    r"TRUIST", r"SUNTRUST", r"SANTANDER", r"HUDSON CITY",
    # lender REO subsidiaries and consumer lenders found by the cents audit
    r"HOMESALES,? INC", r"LIQUIDATION PROPERTIES", r"PROPERTY ASSET MANAGEMENT",
    r"RETAINED REALTY", r"RESIDENTIAL FUNDING", r"HOMECOMINGS FINANCIAL",
    r"BENEFICIAL HOMEOWNER", r"HOUSEHOLD FINANCE", r"CITIFINANCIAL", r"KONDAUR"])

# Lien-holders that take title by foreclosing a lien: NYC tax-lien trusts and
# condominium boards (common charges). Counted only on a referee's deed, since
# a board can also buy a unit at market under a right of first refusal.
LIEN = _rx([r"NYCTL", r"TAX LIEN", r"BOARD OF MANAGERS"])

BROAD = _rx([
    r"FUNDING", r"FINANCE", r"FINANCIAL", r"CAPITAL", r"ASSET", r"ASSETS",
    r"INVESTORS? TRUST", r"MASTER TRUST", r"AS TRUSTEE FOR", r"SERIES (?:19|20)\d\d",
    r"(?:19|20)\d\d [A-Z]{1,5} ?\d{1,2}"])

REFEREE = _rx([r"REFEREE", r"REFERE", r"REFREE", r"AS REF", r"SHERIFF"])

CORP_MARK = _rx([r"INC", r"LLC", r"CORP", r"CORPORATION", r"COMPANY", r"CO", r"LP",
                 r"NA", r"N A", r"NATIONAL ASSOCIATION", r"FSB", r"TRUST",
                 r"TRUSTEE", r"ASSOCIATION", r"FUND", r"SOCIETY", r"AS"])

STRONG = (("agency", AGENCY), ("bank_servicer", BANK),
          ("securitization", SECURITIZATION), ("named_servicer", NAMED))


INSTITUTIONAL = _rx([r"SUCCESSOR", r"MERGER", r"MORT", r"MORTGAGE", r"LOAN", r"BANK",
                     r"FA", r"TRUST", r"SERIES", r"CERTIFICATES?", r"HOLDERS"])


def _is_person(norm, token):
    """'BANK, MICHAEL': the only lender token is the surname of a person.

    Requires a one-word surname equal to the token and a short, digit-free
    given-name part with no corporate or institutional word in it.
    """
    if "," not in norm:
        return False
    sur, given = (x.strip() for x in norm.split(",", 1))
    return (sur == token and " " not in sur and len(given.split()) <= 4
            and not re.search(r"\d", given) and not CORP_MARK.search(given)
            and not INSTITUTIONAL.search(given) and given not in ("NA", "N A"))


def lender_match(name, broad=False):
    """(category, token) if `name` is a lender/servicer/agency, else None."""
    n = normalize(name)
    for cat, rx in STRONG + ((("broad", BROAD),) if broad else ()):
        m = rx.search(n)
        if m and not _is_person(n, m.group(0)):
            return cat, m.group(0)
    return None


def is_referee(name):
    return REFEREE.search(normalize(name)) is not None


NONMARKET = {"LENDER_ACQ_REFEREE", "LENDER_ACQ_OTHER", "LENDER_TO_LENDER"}


def classify_deed(grantors, grantees, broad=False):
    """Event label for one deed from its party-1 and party-2 names."""
    lg = any(lender_match(x, broad) for x in grantees)
    lr = any(lender_match(x, broad) for x in grantors)
    ref = any(is_referee(x) for x in grantors)
    lg = lg or (ref and any(LIEN.search(normalize(x)) for x in grantees))
    if ref:
        ev = "LENDER_ACQ_REFEREE" if lg else "AUCTION_THIRD_PARTY"
    elif lg:
        ev = "LENDER_TO_LENDER" if lr else "LENDER_ACQ_OTHER"
    elif lr:
        ev = "LENDER_RESALE"
    else:
        ev = "ORDINARY"
    return dict(event=ev, amount_is_market=ev not in NONMARKET,
                lender_grantee=lg, lender_grantor=lr, referee_grantor=ref)


def classify_parties(parties, broad=False):
    """Vectorised classify_deed over an ACRIS Parties frame.

    `parties` needs document_id, party_type ('1' grantor, '2' grantee), name.
    Names are classified once each (there are far fewer names than rows).
    """
    import pandas as pd
    p = parties[["document_id", "party_type", "name"]].copy()
    uniq = pd.Series(p["name"].unique())
    lm = uniq.map(lambda x: lender_match(x, broad))
    table = pd.DataFrame({"name": uniq,
                          "lender": lm.notna().to_numpy(),
                          "lender_cat": lm.map(lambda v: v[0] if v else None),
                          "referee": uniq.map(is_referee).to_numpy(),
                          "lien": uniq.map(lambda x: LIEN.search(normalize(x)) is not None).to_numpy()})
    p = p.merge(table, on="name", how="left")
    g2 = p[p["party_type"] == "2"].groupby("document_id")
    g1 = p[p["party_type"] == "1"].groupby("document_id")
    out = pd.DataFrame({
        "lender_grantee": g2["lender"].any(),
        "lender_grantor": g1["lender"].any(),
        "referee_grantor": g1["referee"].any(),
        "lien_grantee": g2["lien"].any(),
        "grantee_cat": g2["lender_cat"].first(),
    })
    out = out.reindex(p["document_id"].unique())
    for c in ("lender_grantee", "lender_grantor", "referee_grantor", "lien_grantee"):
        out[c] = out[c].fillna(False).astype(bool)
    out["lender_grantee"] |= out["referee_grantor"] & out["lien_grantee"]
    lg, lr, ref = out["lender_grantee"], out["lender_grantor"], out["referee_grantor"]
    ev = pd.Series("ORDINARY", index=out.index)
    ev[lr & ~lg & ~ref] = "LENDER_RESALE"
    ev[lg & ~lr & ~ref] = "LENDER_ACQ_OTHER"
    ev[lg & lr & ~ref] = "LENDER_TO_LENDER"
    ev[ref & ~lg] = "AUCTION_THIRD_PARTY"
    ev[ref & lg] = "LENDER_ACQ_REFEREE"
    out["event"] = ev
    out["amount_is_market"] = ~ev.isin(NONMARKET)
    out.index.name = "document_id"
    return out.reset_index(), table


if __name__ == "__main__":
    for nm in sys.argv[1:]:
        print(f"{nm!r:50} lender={lender_match(nm)} referee={is_referee(nm)}")
