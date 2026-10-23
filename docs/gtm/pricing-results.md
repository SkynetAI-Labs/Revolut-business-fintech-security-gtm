# Scenario Pricing Results

**Research date:** 23 October 2026
**Basis:** pricing-scenarios.md
**Status:** Domestic calculation completed; cross-border totals unresolved

## Scenario A: Domestic Baseline

Assume standard electronic GBP transfers to external UK bank accounts,
not CHAPS or other premium payment services. No physical card order
or optional service is included.

| Provider / plan | Calculation | Monthly scenario cost |
|---|---|---|
| Revolut Basic | GBP10 + max(20 outgoing - 10 allowance, 0) x GBP0.20 | GBP12 |
| Revolut Grow, monthly billing | GBP35; outgoing transfers within allowance | GBP35 |
| Revolut Scale, monthly billing | GBP125; outgoing transfers within allowance | GBP125 |
| Starling Business | No monthly fee; specified UK payments have no transaction fee | GBP0 |
| HSBC Small Business Banking | No monthly fee; specified standard UK digital transfers included | GBP0 |
| Wise Business | Exact outgoing GBP transfer fees not established | Unresolved |

Evidence: S015, S020-S023.

S023 excludes the five incoming GBP transfers from Revolut's allowance
count. Do not count them as five additional chargeable transfers.

Wise's GBP50 setup charge for full features/account details is a
one-off cost. It is not a recurring monthly subscription and does not
resolve the unknown transfer costs.

These are scenario-specific charges, not comprehensive ownership costs.
Eligibility and additional-service charges still apply.

## Scenario B: Cross-Border Agency

Use EUR local/SEPA receipt and payment routes for further comparison.
If a provider requires another rail or a separate currency product,
identify that explicitly and check its charges.

For Revolut, let V be the GBP-equivalent value of EUR6,000 at the
provider's actual conversion rate:

- Basic known component: GBP12 domestic baseline + GBP5 outgoing
  international payment + 0.006 x max(V - GBP1,000, 0).
- Grow monthly known component: GBP35 +
  0.006 x max(V - GBP15,000, 0).
- Scale monthly known component: GBP125 +
  0.006 x max(V - GBP60,000, 0).

These are conditional components, not final quotes. They assume unused
monthly allowances, standard processing, no outside-market-hours fee
and no premium transfer option. Incoming EUR does not consume the
transfer allowance under S023. Verify any receipt or intermediary fees.

Wise requires route-specific sending and conversion quotes.
Starling and HSBC require confirmation of currency-account availability,
receipt route, exchange-rate basis and outgoing payment charges.

No full cross-border total or cheapest-provider ranking is established.

## Commercial Interpretation

The domestic scenario gives no basis for claiming Revolut is cheapest.
A cross-border proposition must establish relevant operational benefits
and a fair, complete usage-cost comparison.

## Outstanding Evidence

- Timestamped EUR-to-GBP conversion quotes.
- EUR1,000 supplier-payment charges using the specified funding balance.
- Required currency-account or service subscriptions.
- Receipt and intermediary charges, where applicable.
- Any material difference in supported payment routes.

HSBC announces fee changes effective 14 December 2026. Recheck the
applicable schedule before using this analysis for a later pilot.
