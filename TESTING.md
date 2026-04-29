# Testing Guide: Drug Discovery Web UI Agent

## Local Development

### Prerequisites
- Python 3.8+
- Node.js 16+
- npm
- API key from at least one provider (Anthropic, OpenAI, Google, Cohere)

### Terminal 1: Start Backend
```bash
uvicorn src.main:app --reload --port 8000
```
Expected output:
```
INFO:     Uvicorn running on http://0.0.0.0:8000
INFO:     Application startup complete
```

### Terminal 2: Start Frontend
```bash
cd web && npm install && npm start
```
Expected output:
```
webpack compiled successfully
Compiled successfully!

You can now view drug-discovery-web-ui in the browser.

  Local:            http://localhost:3000
```

### Access the App
Open browser to http://localhost:3000

---

## Test Scenarios

### Scenario 1: Anthropic Provider
**Objective:** Test login + chat with Anthropic Claude

**Steps:**
1. Copy your Anthropic API key (from https://console.anthropic.com)
2. Enter in LoginModal:
   - Provider: Anthropic
   - API Key: `sk-ant-...`
   - Model: `claude-3-5-sonnet-20241022` (default)
3. Check confirmation checkbox
4. Click "Start Session"

**Expected:**
- ✅ Session created (X-Session-ID in headers)
- ✅ SessionBadge shows "🔐 anthropic (30m 0s)"
- ✅ ChatInterface renders

**Chat Test:**
- Type: "Evaluate Staphylococcus aureus GyrB"
- Expected: AI assessment of target protein
- Verify: Response displays in chat (no errors)

---

### Scenario 2: OpenAI Provider
**Objective:** Test login + chat with GPT-4o

**Steps:**
1. Copy OpenAI API key (from https://platform.openai.com/api-keys)
2. LoginModal:
   - Provider: openai
   - API Key: `sk-...`
   - Model: `gpt-4o`
3. Submit and test chat

**Chat Test:**
- Type: "Generate controls for S. aureus GyrB, PDB 4P8O"
- Expected: Validation compounds list (positive + negative controls)

---

### Scenario 3: Google Gemini Provider
**Objective:** Test with Gemini (newly added)

**Steps:**
1. Get Gemini API key from https://ai.google.dev/
2. LoginModal:
   - Provider: google
   - API Key: `AIzaSy...`
   - Model: `gemini-2.0-flash`
3. Submit and test

**Chat Test:**
- Type: "Prepare screening for Plasmodium falciparum DHFR, PDB 1J3I"
- Expected: Screening brief + ZINC20 query

---

### Scenario 4: Custom Model Name
**Objective:** Test custom model entry (not in defaults)

**Steps:**
1. LoginModal:
   - Provider: anthropic
   - API Key: `sk-ant-...`
   - Model: `claude-3-opus-20250219` (custom entry)
2. Submit

**Expected:**
- ✅ Session created with custom model
- ✅ Badge shows correct provider

---

### Scenario 5: Session Cleanup (beforeunload)
**Objective:** Verify API key deleted on tab close

**Steps:**
1. Login successfully
2. Open DevTools → Application → Network tab (filter: DELETE)
3. Close the browser tab
4. Check Network tab before it closes

**Expected:**
- ✅ DELETE /session/{id} request sent
- ✅ Server responds 200

**Verification:**
- Reopen app, need to login again (session deleted)

---

### Scenario 6: Inactivity Timeout
**Objective:** Test 30-min auto-logout

**Steps:**
1. Login
2. Sit idle for 25 minutes
3. Expected: Warning modal "Session will expire in 5 min"
4. Click "Cancel"
5. Sit idle for 5 more minutes
6. Expected: Auto-redirect to login

**Fast Test (for development):**
- Modify `useSessionCleanup.ts` INACTIVITY_WARNING = 5000 (5s), INACTIVITY_LOGOUT = 10000 (10s)
- Login
- Do nothing
- After 5s: Warning modal
- If you dismiss: After 10s total: Auto-logout

---

### Scenario 7: End Session Button
**Objective:** Manual logout with confirmation

**Steps:**
1. Login
2. Click SessionBadge (top-right)
3. Click "✕" button
4. Confirmation modal: "All data will be deleted"
5. Click "End Session & Clear Data"

**Expected:**
- ✅ DELETE /session/{id} sent
- ✅ SessionBadge disappears
- ✅ Redirect to LoginModal
- ✅ Need to re-enter credentials

---

### Scenario 8: Invalid Session (401 Response)
**Objective:** Test 401 handling

**Steps:**
1. Login normally
2. Manually delete session on backend (stop backend, restart, session lost)
3. Type message in chat
4. Click Send

**Expected:**
- ✅ 401 response from backend
- ✅ apiClient interceptor catches it
- ✅ Redirect to login screen

---

## Security Validation Checklist

### API Key Storage
- [ ] API key not in localStorage (`localStorage.getItem('api_key')` = null)
- [ ] API key not in sessionStorage (only sessionId present)
- [ ] API key not in window object
- [ ] API key not in console logs

**Verify via DevTools Console:**
```javascript
// All should be null/empty
sessionStorage.getItem('api_key')  // null
localStorage.getItem('api_key')    // null
window.apiKey                       // undefined
```

### Network Security
- [ ] API key never in HTTP request body
- [ ] X-Session-ID header present on all requests
- [ ] No plaintext session data in Network tab

**Verify via DevTools Network:**
1. Open Network tab
2. Send a message in chat
3. Click POST request to `/api/workflow/evaluate-target`
4. Check Request Headers: `X-Session-ID: abc123...`
5. Check Request Body: NO `api_key` field
6. Check Response: Includes `session_expires_in`

### Session Cleanup
- [ ] beforeunload DELETE request sent on tab close
- [ ] Session expires after 30 min (verified: badge counts down)
- [ ] Inactivity warning at 25 min
- [ ] Auto-logout at 30 min
- [ ] End Session button works + confirmation

**Verify:**
1. Open DevTools → Network
2. Type anything in chat (generates network activity)
3. Do nothing for 30 sec, then click "✕" in SessionBadge
4. Click "End Session"
5. Check Network: DELETE /session/{id} → 200

### Error Handling
- [ ] No API key in error messages
- [ ] Friendly error text displayed to user
- [ ] 401 redirects to login (not error page)

**Verify:**
1. Login with wrong API key (e.g., "sk-wrong")
2. Click "Start Session"
3. Error message: "Failed to create session. Check your API key."
4. NO error exposure of the key

---

## Claude Code Preview Testing

### Setup
```bash
# Repo already configured with .claude/settings.json
# Both servers auto-start on session begin

# If auto-start fails, manual startup:
# Terminal 1:
uvicorn src.main:app --reload --port 8000

# Terminal 2:
cd web && npm start
```

### Preview in Claude Code
1. Click **Preview** button in Claude Code Desktop
2. Select `http://localhost:3000`
3. React app renders in side panel

**Expected:**
- ✅ LoginModal visible in preview
- ✅ Can enter credentials + submit
- ✅ Chat interface loads
- ✅ Send message → response appears
- ✅ Edit React code → hot reload in preview (no full refresh)

---

## Multi-Provider Test Matrix

| Provider | API Key | Model | Test Status | Notes |
|----------|---------|-------|-------------|-------|
| **Anthropic** | sk-ant-... | claude-3-5-sonnet-20241022 | ⬜ TODO | Recommended, most tested |
| **OpenAI** | sk-... | gpt-4o | ⬜ TODO | Widely available |
| **Google Gemini** | AIzaSy... | gemini-2.0-flash | ⬜ TODO | New in Phase 1 |
| **Cohere** | cohbuild_... | command-r-plus | ⬜ TODO | Optional |

**Fill in results:**
- ✅ = Tested, all 4 workflows work
- ⚠️ = Tested, some issues (describe)
- ❌ = Tested, failed (describe)

---

## Performance Baseline

| Workflow | Expected Time | Notes |
|----------|----------------|-------|
| Evaluate Target | ~30-60s | Depends on LLM |
| Get Controls | ~60-90s | More complex response |
| Prep Screening | ~90-120s | Longest workflow |
| Analyze Hits | ~60-90s | Medium complexity |

**Network:**
- Baseline latency (no work): ~50-200ms (depends on API provider)
- Response streaming: N/A (not implemented, but can be added)

---

## Known Issues & Workarounds

### Issue: "Cannot find module 'react-scripts'"
**Fix:** `cd web && npm install`

### Issue: Port 8000 already in use
**Fix:** `lsof -i :8000` → `kill -9 <PID>` or use different port

### Issue: Port 3000 already in use
**Fix:** `PORT=3001 npm start` or `lsof -i :3000` → kill process

### Issue: CORS error on API call
**Fix:** Verify backend running on localhost:8000 with CORS middleware enabled
Check in `src/main.py`: `allow_origins=["http://localhost:3000"]`

### Issue: API key not being validated
**Fix:** Check that provider name matches exactly (anthropic, openai, google, etc. - lowercase)

---

## Success Criteria (All Must Pass)

- [x] Phase 0: Notebooks → Python modules ✅
- [x] Phase 1: Backend API + session manager ✅
- [x] Phase 2: Frontend + LoginModal ✅
- [x] Phase 3: ChatInterface + E2E integration ✅
- [ ] Phase 4: Multi-provider testing (THIS PHASE)
  - [ ] Anthropic tested (all 4 workflows)
  - [ ] OpenAI tested (all 4 workflows)
  - [ ] Gemini tested (all 4 workflows)
  - [ ] Security validation (all checklist items)
  - [ ] Claude Code preview working
- [ ] Phase 5: Deployment & documentation

---

## Reporting Results

After testing, update this section:

```markdown
## Test Results (Phase 4)

**Tested by:** [Your name]
**Date:** [Date]
**Environment:** [macOS/Windows/Linux + Python version + Node version]

### Provider Results
- Anthropic: ✅ All workflows pass
- OpenAI: ✅ All workflows pass
- Gemini: ✅ All workflows pass
- Cohere: [Tested/Not tested]

### Security Validation
- [x] API key not stored
- [x] beforeunload cleanup works
- [x] Inactivity timeout works
- [x] 401 redirect works

### Issues Found
[None / List any issues and workarounds]

### Claude Code Preview
- [x] Auto-start works
- [x] Preview renders correctly
- [x] Hot reload working
```
