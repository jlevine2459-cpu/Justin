# Pool pick model (Week 11, 2026-11-22)

Independent model built to check and improve the ChatGPT desk's picks.

1. `src/hist.py` loads nflverse game results with closing spreads, totals and spread prices (1999–2026).
2. `src/translate_test.py`, `src/translate_recency.py`: an out-of-sample backtest (2012–2025) of converting a market spread into a cover probability at a different, pool, half-point line. The kernel margin distribution, rescaled to no-vig price, is well calibrated. It slightly *understates* the value of extra points, by about 1 percentage point at 2.5–3 points.
3. Walk-forward tests (2008–2026) show that spread juice alone does not beat a coin flip over the full history, so juice is shrunk 50%. Road underdogs covered about 51.9% of walk-forward leans, so a +0.8 percentage point road-dog prior is applied.
4. `src/probs.py`: final probability = 50% sportsbook translation + 50% exchange midpoint (Kalshi/Polymarket exact-line contracts), plus the road-dog prior.
5. `src/field.py`, `src/season_sim.py`: Monte Carlo simulation of the rest of the season, using all 467 entrants' current wins, all posted Week 11 cards (anonymised arrays only), future weeks resampled from this week's games and pick shares, season payouts 1–15 and the weekly $400/$150. All 4,096 possible cards were screened, then the shortlist was rerun on fresh simulations with paired error bars.

Raw pool pages and participant names are not stored in this repository.
