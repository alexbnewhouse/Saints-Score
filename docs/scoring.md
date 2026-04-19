# Saints Score Scoring Methodology

## Overview

The Saints Score quantifies the degree to which an online community canonizes
a perpetrator of mass-casualty violence. It consists of two complementary
versions.

## Naïve Saints Score

$$\text{Saints}_a = z\left(\log\frac{E^+_a + \epsilon}{E^-_a + \epsilon}\right) \cdot (I_a^* + L_a^* + \tilde{S}_a^*)$$

Where:
- $E^+_a, E^-_a$ = positive and negative sentiment proportions
- $I_a^*$ = min-max scaled intensity
- $L_a^*$ = min-max scaled longevity
- $\tilde{S}_a^*$ = min-max scaled semantic similarity
- $z(\cdot)$ = z-score across attackers

### Known issues
- Ratio is unbounded
- Sum mixes unit-heterogeneous terms
- No measurement uncertainty

## Bayesian Measurement Model

Treat Saints Score as a latent variable $\eta_a$ with five continuous indicators:

1. $\log(E^+/E^-)$ — affect ratio
2. $I_a$ — intensity
3. $L_a$ — longevity
4. $\tilde{S}_a$ — semantic convergence
5. $\log(\text{mention volume})$ — raw mention count

### Model specification

$$y_{aj} = \lambda_j \eta_a + \epsilon_{aj}$$

$$\eta_a \sim \text{Normal}(0, 1)$$
$$\lambda_j \sim \text{Normal}(0.5, 1)$$
$$\sigma_j \sim \text{HalfNormal}(1)$$
$$\epsilon_{aj} \sim \text{Normal}(0, \sigma_j)$$

All indicators are standardised before fitting.

### Output

- Posterior mean factor scores with 89% HDIs per attacker
- Factor loading estimates with credible intervals
- Model diagnostics: PPC, LOO
