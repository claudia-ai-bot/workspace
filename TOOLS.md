# TOOLS.md - Local Notes

## Server

- **Remote server:** srv1457306 (100.112.172.117) — Hostinger VPS
- **Access:** via Tailscale VPN tunnel (100.112.172.117 is the Tailscale IP)
- **Gateway port:** 18789 (loopback only)
- **Dashboard URL:** http://127.0.0.1:18789 (requires SSH tunnel)
- **Dashboard token:** stored in openclaw.json

## SSH Tunnel (Dashboard Access)

Open a NEW local terminal (keep gateway running):
```
ssh -N -L 18790:127.0.0.1:18789 chris@100.112.172.117
```
Then: `http://localhost:18790/#token=<token from openclaw dashboard>`

## Node Host

- Node: srv1457306 — needs to be running for full capabilities
- Start with: `OPENCLAW_GATEWAY_TOKEN=<token> openclaw node run`
- Capabilities: browser, system (system.run = exec)
- Disconnects when gateway restarts — need to reconnect manually

## Gateway Management

- Restart: `openclaw gateway restart`
- Force kill if stuck: `fuser -k 18789/tcp` then `openclaw gateway start`
- Check logs if issues

## Hooks Enabled

- session-memory 💾
- command-logger 📝

## Tools Profile

- Set to: `full`

## Telegram Group Rules

**Golden rule:** Always check the inbound context metadata (`chat_id`) to verify which group a message came from BEFORE responding.

**Before every reply in a group:**
1. ✅ Read the `chat_id` in the inbound_meta JSON — this is the SOURCE group
2. ✅ If replying normally (no message tool), it auto-routes to that group — just reply
3. ✅ If using message tool (`action=send`), ALWAYS specify the exact `target` or `channel`
4. ❌ Never assume or guess which group you're in — the metadata is ground truth

**Known groups:**
- `telegram:-5237212015` = Recruitment (main discussion group)
- [Add others as they're created]

**Rule in action:**
- Message from `-5237212015` → reply goes back to `-5237212015` automatically
- Using message tool? Specify `target="telegram:-5237212015"` explicitly
- Don't cross-post unless Chris explicitly asks for it

## Browser Tool

**Use for:**
- Hunting deals/vouchers (search, filter, see layouts)
- Interactive navigation (click, fill forms, submit)
- Real-time info that changes (deals, stock, schedules)
- Screenshots/visual inspection needed

**Don't use for:**
- Simple text fetching (use web_fetch, it's faster)
- When you just need content extraction

**Note:** Server has no browser installed yet (Chromium would need to be installed). Can only use with host/sandbox browser.
