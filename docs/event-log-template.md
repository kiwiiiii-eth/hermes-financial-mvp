# Event Log Template

Each anomaly analysis should be saved as a replayable Markdown event.

```markdown
## YYYY-MM-DD HH:mm SYMBOL

### Input
- symbol:
- window:
- current_price:
- price_change_5m:
- funding_rate:
- funding_change:
- open_interest:
- oi_change_5m:
- volume_change_5m:
- data_quality:
- sources:

### Hermes Read
- anomaly_type: Short Squeeze / Long Squeeze / Funding 異常 / 假突破 / 無明確訊號
- 現象:
- 判斷:
- 支持證據:
- 反證:
- 風險:
- 建議動作:
- 是否需要人工確認:

### Notification
- channel:
- message_id:
- sent_at:

### Follow-up
- 30m price:
- 1h price:
- OI follow-up:
- funding follow-up:

### Lesson
- 判斷是否有效:
- 是否需要調整規則:
```
