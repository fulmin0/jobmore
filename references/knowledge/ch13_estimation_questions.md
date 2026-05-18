# Ch13: Estimation Questions

## Summary
Full framework for answering "How would you estimate X?" questions (also called Fermi estimation or market sizing). Covers the 8-step approach, common question types, sample walkthroughs, and what interviewers are actually evaluating. These questions test structured thinking and comfort with ambiguity — not numerical accuracy.

## Key Concepts
- **What interviewers actually test**: Process, not precision. A wrong answer with clean structure > a right answer with no structure. Interviewers want to see: (1) you can break a complex unknown into manageable pieces, (2) you sanity-check your own numbers, (3) you communicate assumptions explicitly
- **8-Step Approach**:
  1. **Clarify**: Ask clarifying questions to bound the problem. "Are we estimating global or US?" "Daily, monthly, or annual?"
  2. **Catalog**: List what you know that's relevant (base facts, reference numbers you carry in your head)
  3. **Equation**: Write out the formula before plugging in numbers. "Total = X × Y × Z"
  4. **Edge Cases**: Identify factors that could significantly change the estimate (seasonality, geography, user segments)
  5. **Break Down**: Segment the problem (by user type, geography, use case) to make each piece estimable
  6. **Assumptions**: State your assumptions explicitly and defend them briefly
  7. **Math**: Do the arithmetic, keeping it rough and round (no false precision)
  8. **Sanity Check**: Does the number feel right? Cross-check against a known reference ("that's roughly the population of France — seems too high for a niche B2B tool")
- **Reference numbers to memorize** (carry these into any interview):
  - US population: ~330M
  - World population: ~8B
  - US smartphone penetration: ~85%
  - US internet users: ~270M
  - Average US household size: ~2.5
  - Hours of video uploaded to YouTube per minute: ~500 hours (as of ~2022)
  - Average person checks phone: ~150x/day
  - US GDP: ~$25T
- **Common question types**:
  - Market size: "How large is the market for X?"
  - Usage estimation: "How many queries does Google get per day?"
  - Revenue estimation: "What's Uber's annual revenue?"
  - Infrastructure: "How many servers does Netflix need?"
  - Product metrics: "How many people use Google Maps daily?"
- **Segmentation strategies**:
  - By geography (US vs. global, urban vs. rural)
  - By user type (age cohort, income bracket, tech adoption curve)
  - By use case (daily vs. weekly vs. occasional users)
  - By platform (mobile vs. desktop, iOS vs. Android)
- **Common mistakes**:
  - Jumping to numbers without writing the equation
  - Not segmenting — treating all users as identical
  - No sanity check — accepting an implausible number
  - Over-precision: "$47.3B market" sounds made up; "$45–50B" is more honest
  - Silence: Never stop talking. Walk through your thinking aloud

## Direct Quotes / Signals Worth Preserving
- "The goal isn't to get the right answer. The goal is to show you can think through an ambiguous problem systematically."
- On sanity checks: "If your estimate says 500M Americans own dogs, you should notice that's more than the US population and restart."
- On equation-first: "Write the formula before you touch a number. The formula is the structure. The numbers are just inputs."
- "State your assumptions explicitly. The interviewer doesn't care if your assumption is wrong — they care that you're aware it's an assumption."

## Relevance to Job Search Pipeline
- **Product analytics interviews**: Estimation skills are also tested as "metric definition" questions — "How would you measure success for X feature?" uses the same decomposition approach
- **Data-driven behavioral stories**: The estimation framework reinforces the analytical credibility that behavioral stories about data-driven decisions need — show you can structure problems, not just pull dashboards
- **System design prep**: Infrastructure estimation questions (servers, storage, bandwidth) overlap with system design — useful for technical PM roles
- **Practice reference**: For active pipeline jobs where data/analytical skills are a JD pillar, prep 2–3 estimation questions from the relevant domain (e-commerce, SaaS, consumer)
