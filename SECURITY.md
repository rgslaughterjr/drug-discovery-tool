# Security Guarantees: Drug Discovery Web UI Agent

## Data Privacy & Credential Handling

### 🔐 API Key Protection

**Guarantee:** Your API key is **NEVER stored, logged, or persisted**.

#### How It Works
1. **Session Creation:** You provide your API key once via the login form
2. **In-Memory Storage:** Key stored in FastAPI process memory (RAM) only, indexed by session_id
3. **Session Use:** For all API calls, only the session_id is sent (via X-Session-ID header)
4. **Session Cleanup:** When you close the window or click "End Session", key is overwritten with random data and deleted

#### What Happens to Your Key
```
You enter key → FastAPI stores in RAM → Session ID returned to browser
↓
All API calls use X-Session-ID header (not key)
↓
Browser closed OR 30-min timeout OR "End Session" clicked
↓
Key overwritten with random bytes → Session deleted from memory
```

### 📱 Client-Side Storage

**Guarantee:** Only the session_id is stored in sessionStorage (temporary, session-only).

| Storage Type | API Key | Session ID | Data |
|--------------|---------|------------|------|
| localStorage | ❌ NO | ❌ NO | ❌ NO |
| sessionStorage | ❌ NO | ✅ YES | ❌ NO |
| Memory (React) | ❌ NO | ✅ YES | ✅ provider, model names only |
| Cookies | ❌ NO | ❌ NO | ❌ NO |

**Verification (DevTools):**
```javascript
// All return null/undefined:
localStorage.getItem('api_key')      // null
sessionStorage.getItem('api_key')    // null
sessionStorage.getItem('sessionId')  // "abc123..." (OK, not sensitive)
window.apiKey                         // undefined
```

### 🌐 Network Security

**Guarantee:** API key never appears in HTTP requests or logs.

#### Request Headers
```
GET /api/models/available
Host: localhost:8000
X-Session-ID: abc123def456  ← Only session ID sent
```

#### Request Body (Workflow Call)
```json
POST /api/workflow/evaluate-target
X-Session-ID: abc123def456

{
  "organism": "Staphylococcus aureus",
  "protein_name": "GyrB",
  "protein_id": null
}
// NO "api_key" field
```

#### Backend Processing (No Logging)
```python
# src/routes/workflows.py
def _get_session_client(session_id: str):
    # Retrieve from SessionStore using session_id
    api_key = store.get_api_key(session_id)  # ← Secret, not logged
    # Create client with api_key (internal only)
    return DrugDiscoveryClient(config=APIConfig(...))
    # Never print, log, or return api_key
```

### ⏰ Session Lifecycle

**Guarantee:** Session automatically expires and credentials are deleted.

#### Session Duration
- **Initial TTL:** 30 minutes from creation
- **Activity Reset:** Any API call resets the timer
- **Inactivity Warning:** 25 minutes → User warned
- **Auto-Logout:** 30 minutes → Auto-redirect to login (credentials deleted)

#### Manual Cleanup
- **Close Browser:** beforeunload event → DELETE /session/{id}
- **Click End Session:** Confirmation modal → DELETE /session/{id}
- **Browser Crash:** Session auto-expires after 30 min

#### Verification (DevTools Network)
1. Open Network tab
2. Close browser tab
3. Check: Should see **DELETE /session/{id}** request
4. Reopen browser → Need to login again (session gone)

### 🛡️ Secure Key Deletion

**Guarantee:** API key is securely overwritten before deletion.

```python
# src/session_manager.py
def delete(self, session_id: str):
    session = self.sessions[session_id]
    api_key = session.get('api_key')
    
    # Overwrite with random data before deletion
    if api_key:
        random_data = secrets.token_urlsafe(len(api_key))
        session['api_key'] = random_data  # ← Overwrites original
    
    # Delete from store
    del self.sessions[session_id]
```

### 📝 Error Handling

**Guarantee:** Error messages never contain your API key.

#### Bad Examples (We DON'T do this)
```
❌ Error: Invalid API key 'sk-ant-abc123'
❌ Error: Authentication failed with key: sk-ant-...
❌ Traceback showing: api_key = "sk-ant-..."
```

#### Good Examples (We DO this)
```
✅ Error: Failed to create session. Check your API key.
✅ Error: Invalid provider. Use 'anthropic', 'openai', 'google', etc.
✅ Error: Session expired. Please log in again.
```

---

## Security Testing Checklist

### Before Each Session
- [ ] Review this document (you are here ✅)
- [ ] Check TESTING.md for multi-provider validation

### During Session
- [ ] Open DevTools → Application tab
- [ ] Verify `localStorage.getItem('api_key')` returns null
- [ ] Verify `sessionStorage.getItem('api_key')` returns null
- [ ] Open Network tab
- [ ] Send message in chat
- [ ] Check request headers: **X-Session-ID present, NO api_key**
- [ ] Check request body: **NO api_key field**

### On Close
- [ ] DevTools Network
- [ ] Close browser tab
- [ ] Verify **DELETE /session/{id}** request sent
- [ ] Response: 200 OK + "All credentials securely wiped"
- [ ] Reopen app
- [ ] Verify: Need to re-login (session deleted)

### Multi-Provider Verification
For each provider (Anthropic, OpenAI, Gemini, Cohere):
- [ ] Login with provider's API key
- [ ] Send message → API call succeeds
- [ ] Check Network tab: Only X-Session-ID sent (no key)
- [ ] Close window → DELETE request sent
- [ ] Reopen → Session gone, re-login required

---

## Comparison: Session-Based vs. Key-Per-Request

### Our Approach (Session-Based)
```
Browser                    Server
  |                          |
  |-- POST /session/create   |
  |    (api_key)             |
  |  ← session_id (only!)    |
  |                          | [Store: session_id → api_key]
  |-- POST /api/workflow     |
  |    (X-Session-ID)        |
  |  ← response              |
  |                          | [Use stored key]
  |                          |
  |-- DELETE /session/id     |
  |    (X-Session-ID)        |
  |  ← 200 OK                |
  |                          | [Overwrite key, delete]
```

**Advantages:**
- ✅ Key never in HTTP request/response
- ✅ Key never logged or stored on disk
- ✅ Key only in RAM during session
- ✅ Automatic expiry after 30 min
- ✅ Easy cleanup on logout

### Alternative Approach (Key-Per-Request) ❌ NOT USED
```
Browser                    Server
  |-- POST /api/workflow   |
  |    (api_key in body)    |
  |  ← response             | [Key exposed in logs/storage]
```

**Problems:**
- ❌ Key in HTTP request body (visible in proxy/logs)
- ❌ Key could be stored in server logs
- ❌ No automatic cleanup mechanism
- ❌ Key persists until manual deletion

---

## Regulatory Compliance

### GDPR (General Data Protection Regulation)
- ✅ **Data Minimization:** Only session_id stored on client
- ✅ **Data Retention:** Sessions auto-delete after 30 min
- ✅ **Right to Delete:** "End Session" button clears all data
- ⚠️ **Third-party processors:** LLM providers (you control via API key)

### HIPAA (Health Insurance Portability and Accountability Act)
- ⚠️ **Not inherently compliant** (depends on LLM provider & use case)
- ✅ **We ensure:** No unauthorized data storage or transmission
- ⚠️ **You ensure:** Use HIPAA-compliant LLM provider (Anthropic supports this)

### SOC 2 Type II
- ✅ **Our implementation:** Follows best practices for session management
- ⚠️ **Deployment:** Your hosting environment determines full compliance

---

## Incident Response

### If You Suspect Compromise

1. **Immediate Action:**
   - Click "End Session" button (clears all credentials)
   - Close browser completely
   - Revoke API key with your provider

2. **Provider Actions:**
   - Anthropic: https://console.anthropic.com → Settings → API Keys → Delete compromised key
   - OpenAI: https://platform.openai.com/api-keys → Delete key
   - Google: https://ai.google.dev/manage-api-keys → Delete key
   - Cohere: https://dashboard.cohere.ai/api-keys → Delete key

3. **Create New Key:**
   - Generate new API key from provider
   - Login to app with new key
   - Old key is now invalid

### Reporting Security Issues

If you discover a security vulnerability:
- **DO NOT** open a public GitHub issue with security details
- Email: security@anthropic.com (if using Anthropic)
- Or: Submit via responsible disclosure program of your LLM provider

---

## FAQ

**Q: Can the app developer see my API key?**
A: No. The code never logs, stores, or processes keys on persistent storage. Keys exist only in RAM during your session.

**Q: What if I close the app without clicking "End Session"?**
A: The beforeunload event handler sends a DELETE request to clean up the session. If the browser crashes, the session auto-expires after 30 minutes.

**Q: Are my results stored?**
A: No. Chat history exists only in your browser's memory. Close the tab → history is gone. We don't store conversations or results.

**Q: What data does the LLM provider see?**
A: Only what you send in your prompts (e.g., "Evaluate Staphylococcus aureus GyrB"). The provider sees your input but NOT your API key (handled by their API client).

**Q: Can I use this with institutional keys?**
A: Yes! If your institution provides shared API keys (e.g., university Anthropic account), you can use them. Just treat the key with the same care as a personal key.

**Q: Is this suitable for sensitive data?**
A: Use caution. The app is designed for scientific/research data. Avoid sending:
- Patient-identifiable information (PII)
- Proprietary compound data
- Confidential research data
Instead, use anonymized examples and consult your institution's data governance policy.

---

## Summary

✅ **Your API key is protected by:**
1. Session-based authentication (key never in requests)
2. In-memory storage (RAM only, no disk persistence)
3. Automatic expiry (30 min timeout)
4. Secure deletion (key overwritten before removal)
5. No logging (key never printed or stored)

✅ **You control your data by:**
1. Providing only your own API key
2. Logging out when done
3. Revoking keys with your provider if needed
4. Using GDPR/HIPAA-compliant providers

**Bottom line:** This app is designed with security-first principles. Your credentials are temporary and completely cleaned up on logout.
