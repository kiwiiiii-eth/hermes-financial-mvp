# Unknown Discovery Agent

Unknown Discovery is the check Hermes runs before analysis.

Its purpose is to make missing information visible, so Hermes does not turn incomplete data into confident financial commentary.

## Core Questions

Before calling a financial skill, ask:

- What data is required by the selected skill?
- Which required fields are missing?
- Are the data sources explicit?
- Is there missing context such as news, macro, or on-chain data?
- Does the missing data block execution or only reduce confidence?
- Does this require human confirmation?

## Current Checks

For `crypto-market-anomaly`, missing required fields block execution.

For optional research context:

- Missing news context should be reported when the request asks for news.
- Missing macro context should be reported when the request asks for macro.
- Missing on-chain or whale data should be reported when the request asks for on-chain or whale activity.

## Output Shape

```json
{
  "questions": [
    "目前缺什麼資料？",
    "資料來源是否明確？",
    "缺失資料是否會影響分類？",
    "是否需要人工確認後才回報？"
  ],
  "missing_required_fields": ["funding_rate"],
  "missing_research_context": ["news_sources"],
  "selected_skill_is_available": true
}
```

## Safety Rule

Unknown Discovery must make uncertainty explicit. If data is missing, Hermes says so and stops or lowers confidence instead of filling gaps with assumptions.

