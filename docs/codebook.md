# Saints Score Codebook

## Variable Definitions

### Case-level Variables

| Variable | Type | Description |
|---|---|---|
| `case_id` | str | Unique identifier: `COUNTRY-YEAR-NAME` |
| `event_date` | date | UTC date of the attack |
| `event_year` | int | Year of the attack |
| `country` | str | ISO country code |
| `status` | enum | `C` (completed), `PF` (partially foiled), `F` (foiled) |
| `perpetrator_name` | str | Canonical name |
| `method_primary` | enum | Primary weapon type |
| `fatalities_excl_perp` | int | Fatalities excluding perpetrator |
| `venue_type` | enum | Attack location type |
| `manifesto_exists` | enum | `Y`, `N`, or `Partial` |
| `livestream_successful` | enum | `Y`, `N`, or `Partial` |
| `saints_relevance` | enum | Expected Saints Score level |
| `saints_tradition` | enum | Tradition/subculture classification |

### Saints Score Components

| Variable | Type | Description |
|---|---|---|
| `intensity` | float | I_a: mention proportion in immediate window [t, t+7d] |
| `longevity` | float | L_a = 1/α from power-law decay fit |
| `similarity_median` | float | S_a: median pairwise cosine similarity |
| `positive_ratio` | float | Proportion of positive-sentiment mentions |
| `negative_ratio` | float | Proportion of negative-sentiment mentions |
| `saints_naive` | float | Naïve composite score |
| `saints_bayes_mean` | float | Bayesian factor score (posterior mean) |
| `saints_bayes_hdi_lo` | float | 89% HDI lower bound |
| `saints_bayes_hdi_hi` | float | 89% HDI upper bound |

### Temporal Windows

| Window | Start | End | Description |
|---|---|---|---|
| Baseline | t - 365d | t - 1d | Pre-attack background rate |
| Immediate | t | t + 7d | First week post-attack |
| Near-term | t + 8d | t + 90d | Weeks 2–13 |
| Long-term | t + 91d | t + 730d | Months 4–24 |
