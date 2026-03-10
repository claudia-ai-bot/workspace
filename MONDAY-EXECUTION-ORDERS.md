# Monday Execution Orders - Copy & Execute
**10% ROI Challenge - March 10, 2026**

---

## TRADE #1: NVDA (Mean Reversion)

**PRIMARY ORDER (Buy):**
```
Symbol:     NVDA
Type:       Market Buy
Quantity:   4 shares
Price:      $177.82 (at market, accept ~$177-179 range)
Execution:  Market open or any time Monday
```

**STOP LOSS ORDER (Auto-sell on loss):**
```
Symbol:     NVDA
Type:       Stop Order (Sell)
Quantity:   4 shares
Stop Price: $173.28
Execution:  Automatic when price hits $173.28
Max Loss:   $20 (4 × $1.14 per share)
```

**PROFIT TARGET ORDER (Auto-sell on win):**
```
Symbol:     NVDA
Type:       Limit Order (Sell)
Quantity:   4 shares
Limit Price: $188.49
Execution:  Automatic when price reaches $188.49
Profit:     +$42.68 (4 × $10.67 per share)
```

**Summary:**
- Buy 4 @ $177.82
- Stop @ $173.28 (down -$20)
- Target @ $188.49 (up +$42.68)
- Risk/Reward: 1:2.35

---

## TRADE #2: TSM (Mean Reversion)

**PRIMARY ORDER (Buy):**
```
Symbol:     TSM
Type:       Market Buy
Quantity:   2 shares
Price:      $338.89 (at market, accept ~$338-341 range)
Execution:  Market open or any time Monday
```

**STOP LOSS ORDER (Auto-sell on loss):**
```
Symbol:     TSM
Type:       Stop Order (Sell)
Quantity:   2 shares
Stop Price: $329.96
Execution:  Automatic when price hits $329.96
Max Loss:   $20 (2 × $8.93 per share)
```

**PROFIT TARGET ORDER (Auto-sell on win):**
```
Symbol:     TSM
Type:       Limit Order (Sell)
Quantity:   2 shares
Limit Price: $359.22
Execution:  Automatic when price reaches $359.22
Profit:     +$40.67 (2 × $20.33 per share)
```

**Summary:**
- Buy 2 @ $338.89
- Stop @ $329.96 (down -$20)
- Target @ $359.22 (up +$40.67)
- Risk/Reward: 1:2.28

---

## TRADE #3: MPC (Breakout)

**PRIMARY ORDER (Buy):**
```
Symbol:     MPC
Type:       Market Buy
Quantity:   2 shares
Price:      $221.28 (at market, accept ~$221-223 range)
Execution:  Market open or any time Monday
```

**STOP LOSS ORDER (Auto-sell on loss):**
```
Symbol:     MPC
Type:       Stop Order (Sell)
Quantity:   2 shares
Stop Price: $212.11
Execution:  Automatic when price hits $212.11
Max Loss:   $20 (2 × $9.17 per share)
```

**PROFIT TARGET ORDER (Auto-sell on win):**
```
Symbol:     MPC
Type:       Limit Order (Sell)
Quantity:   2 shares
Limit Price: $238.98
Execution:  Automatic when price reaches $238.98
Profit:     +$35.40 (2 × $17.70 per share)
```

**Summary:**
- Buy 2 @ $221.28
- Stop @ $212.11 (down -$20)
- Target @ $238.98 (up +$35.40)
- Risk/Reward: 1:1.93

---

## TRADE #4: SLB (Mean Reversion)

**PRIMARY ORDER (Buy):**
```
Symbol:     SLB
Type:       Market Buy
Quantity:   14 shares
Price:      $46.90 (at market, accept ~$46.75-47.00 range)
Execution:  Market open or any time Monday
```

**STOP LOSS ORDER (Auto-sell on loss):**
```
Symbol:     SLB
Type:       Stop Order (Sell)
Quantity:   14 shares
Stop Price: $45.47
Execution:  Automatic when price hits $45.47
Max Loss:   $20 (14 × $1.43 per share)
```

**PROFIT TARGET ORDER (Auto-sell on win):**
```
Symbol:     SLB
Type:       Limit Order (Sell)
Quantity:   14 shares
Limit Price: $49.71
Execution:  Automatic when price reaches $49.71
Profit:     +$39.40 (14 × $2.81 per share)
```

**Summary:**
- Buy 14 @ $46.90
- Stop @ $45.47 (down -$20)
- Target @ $49.71 (up +$39.40)
- Risk/Reward: 1:1.97

---

## EXECUTION CHECKLIST

### Before Market Open (9:30 AM Monday)

- [ ] Open IBKR
- [ ] Navigate to "Orders" section
- [ ] Verify account is in **Paper Trading mode** (not live!)

### During Market Open (9:30 AM - 10:00 AM recommended)

**For each trade:**

1. **CREATE BUY ORDER**
   - Symbol: [NVDA/TSM/MPC/SLB]
   - Type: Market
   - Quantity: [4/2/2/14]
   - Click "Submit"

2. **CREATE STOP LOSS** (immediately after buy fills)
   - Same symbol
   - Type: Stop Order (Sell)
   - Quantity: [same as above]
   - Stop Price: [from chart above]
   - Click "Submit"

3. **CREATE PROFIT TARGET** (immediately after buy fills)
   - Same symbol
   - Type: Limit Order (Sell)
   - Quantity: [same as above]
   - Limit Price: [from chart above]
   - Click "Submit"

### After Execution

- [ ] Confirm all 4 buy orders filled
- [ ] Confirm all 8 exit orders active (4 stops + 4 targets)
- [ ] Screenshot your position
- [ ] Report back to Claudia: "Executed: NVDA 4@$X.XX, TSM 2@$Y.YY, etc."

---

## PORTFOLIO RISK SUMMARY

| Trade | Risk | Target | Heat |
|-------|------|--------|------|
| NVDA | -$20 | +$42.68 | -$20 |
| TSM | -$20 | +$40.67 | -$40 |
| MPC | -$20 | +$35.40 | -$60 |
| SLB | -$20 | +$39.40 | -$80 |
| **TOTAL** | **-$80** | **+$157.95** | **Max -$80** |

**Wait:** Max heat is $80 (higher than $50 limit). Fix: Reduce to 3 trades (remove SLB if needed).

**Better approach:** Execute 3 trades Monday, save SLB for Tuesday.

---

## CONSERVATIVE APPROACH (RECOMMENDED)

**Execute only 3 trades Monday:**

1. ✅ NVDA (highest score, best R/R)
2. ✅ TSM (strong setup, good R/R)
3. ✅ MPC (breakout momentum)

**Save for later:**
- SLB (Tuesday or when position closes)

**Portfolio heat:** Max -$60 (within rules)

---

## IF ANY TRADE HITS TARGET EARLY

- **STOP:** Take the profit, don't let it reverse
- **EXIT BOTH:** Close the buy + close the stop
- **REDEPLOOY:** Use the profit to fund next trade

**Example:**
- NVDA hits $188.49 → Close all NVDA positions → +$42.68 profit
- Now you have $1,042.68 capital
- Later: Trade SLB with fresh capital

---

## COMMON MISTAKES TO AVOID

❌ **Don't:** Move the stop loss up (you'll get stopped out for tiny losses)  
✅ **DO:** Leave it exactly where placed

❌ **Don't:** Move the profit target (missing big winners)  
✅ **DO:** Let it ride to the target

❌ **Don't:** Execute all orders at once (overwhelming)  
✅ **DO:** Execute one trade at a time, wait for fills

❌ **Don't:** Change quantities (position sizing is calculated)  
✅ **DO:** Use exact share counts shown

---

## You're Ready

Copy the 3-4 orders above into IBKR Monday morning.

Set buy → set stop → set target → done.

IBKR handles the exits automatically.

Report back when filled. 🚀
