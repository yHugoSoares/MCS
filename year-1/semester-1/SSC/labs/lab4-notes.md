# Lab 4 notes (Block 2) — running log

## Setup
```bash
ssh -p 2222 -L 3000:localhost:3000 -L 5556:localhost:5556 student@localhost
cd ~/ssc-lab4 && docker compose up -d && docker compose ps  # dex :5556, client :3000
curl -s http://localhost:5556/dex/.well-known/openid-configuration | jq '{issuer, authorization_endpoint, token_endpoint, jwks_uri}'
```
Snapshot: `lab4-clean` (UTM). Login: `student@ssc.local` / `password`. Client: `democlient`.

## P1 — discovery
```json
{
  "issuer": "http://localhost:5556/dex",
  "authorization_endpoint": "http://localhost:5556/dex/auth",
  "token_endpoint": "http://localhost:5556/dex/token",
  "jwks_uri": "http://localhost:5556/dex/keys"
}
```
Proof: `../reports/images/G04Prep1.png`.

## P2 — ID vs access (1 sentence)
ID token proves to a specific audience (the client) that a subject authenticated
with the issuer at a given time; access token only proves to a resource server
that the bearer is authorized to access a resource.

## P3 — redirectURIs (`~/ssc-lab4/dex-config.yaml`)
```yaml
staticClients:
  - id: democlient
    name: 'SSC demo client'
    secret: democlientsecret
    redirectURIs:
      - 'http://localhost:3000/callback'
```

## Ex.1 — endpoints
`authorization_endpoint` = browser login; `token_endpoint` = code→token (back
channel); `jwks_uri` = provider public keys for signature verify.

## Ex.1a — flow sketch
Image: `../reports/images/G04Ex1a.png` (in report2.tex as Fig. 1a).
```
1. Browser GET / → GET /login (client) [FRONT]
2. 302 → GET /dex/auth?client_id…&code_challenge S256 (dex) [FRONT]
3. POST login student@ssc.local [FRONT]
4. 302 → /callback?code=…&state=… (code in URL) [FRONT]
5. GET /callback?code&state [FRONT]
6. POST /dex/token {code + client_secret + code_verifier} [BACK, NOT in Network tab]
7. {id_token, access_token} [BACK]
8. 302 Set-Cookie sid → GET /debug [FRONT]
```
Why back channel matters: code travels in URL (history/logs) but alone is
useless — redeem needs `client_secret` + `code_verifier` which never go through
the browser.

## Ex.2 — run + capture (browser)
### 2a — auth request (`curl -D http://localhost:3000/login`)
```
client_id = democlient
redirect_uri = http://localhost:3000/callback
response_type = code
scope = openid profile email
state = state-… (random per login)
nonce = nonce-… (random per login)
code_challenge = … / code_challenge_method = S256
```

### 2b — callback + tokens
- `GET /callback?code&state` visible in URL (front channel).
- `POST dex/token` absent: Network tab shows only `GET /debug [200]`.
- Tokens at `http://localhost:3000/debug` ("fetched on the back channel").
- Claims (decoded, NOT verified):
```json
{
  "iss": "http://localhost:5556/dex",
  "sub": "CiQ5ZTFhNGMyMi0wMDAwLTRhMDAtYjAwMC0wMDAwMDAwMDAwMDQSBWxvY2Fs",
  "aud": "democlient",
  "exp": 1792059639,
  "iat": 1791973239,
  "nonce": "nonce-uSUYwl_WtVgr",
  "email": "student@ssc.local",
  "email_verified": true,
  "name": "student"
}
```
- Full tokens saved in `lab4-tokens.txt` (`$ID` for Part C/E).

### 2c — client.py audit
Sends but never checks: `state` only `in PENDING` (global dict, not bound to
browser cookie), `nonce` stored never compared, no signature verify via
`jwks_uri`, no `iss/aud/exp` checks. `decode_payload()` = base64 only.
Attacker mint/replay → chosen `sub/email` becomes logged-in `sid` session.
"use OIDC" ≠ secure without validation.

## Ex.3 — what the tokens prove (`$ID` from flow.py)
Header:
```json
{ "alg": "RS256", "kid": "e7d865ac5fd0364f06f6ad1034a17fba2a2a6486" }
```
Payload:
```json
{
  "iss": "http://localhost:5556/dex",
  "sub": "CiQ5ZTFhNGMyMi0wMDAwLTRhMDAtYjAwMC0wMDAwMDAwMDAwMDQSBWxvY2Fs",
  "aud": "democlient",
  "exp": 1792060200, "iat": 1791973800,
  "nonce": "nonce-iNp0iD7r",
  "email": "student@ssc.local", "email_verified": true, "name": "student"
}
```
JWKS (`curl -s http://localhost:5556/dex/keys`):
```json
{ "kid": "e7d865ac5fd0364f06f6ad1034a17fba2a2a6486", "alg": "RS256", "kty": "RSA", "use": "sig" }
```
`kid` matches header → client picks that key. `match: True`.

### 3a — claim roles (if ignored, attacker can…)
- `iss`: accept tokens from any issuer → attacker mints tokens under own IdP and client trusts them.
- `aud`: accept tokens meant for another client → attacker replays a token issued for its own app into the victim app.
- `exp`: accept expired tokens → attacker replays leaked/old tokens forever.
- `sub`: no stable user binding → attacker swaps/confuses identities (all logins map to attacker or wrong user).
- `nonce`: accept replays of old flows → attacker replays a captured ID token / injects its own login response into victim's browser (session fixation, no freshness).

### 3b — alg/kid → key
Header gives `alg` + `kid`. Client fetches JWKS at `jwks_uri`
(discovery), selects entry with equal `kid`, verifies RS256 signature with that
RSA key. Confirmed above.

### 3c — access token ≠ identity
Access token is bearer authorization for a resource server (what the bearer may
do), not an authentication assertion to this client: wrong audience, no
`nonce`/login binding — presenting it proves nothing about who logged in here.

## Ex.4 — redirect_uri validation (live)
Tampered: `http://localhost:3000.attacker.example/callback`
Registered (P3): `http://localhost:3000/callback`

### 4a — what dex does (observed browser + curl)
1. Browser shows `400 Bad Request` + exact text:
   `Unregistered redirect_uri ("http://localhost:3000.attacker.example/callback").`
   Absent vs Ex.2: no login form, no `302 → /callback?code&state` — flow stops
   before authentication.
2. Chain: `1: 302 Location: /dex/auth/local?…redirect_uri%3D…` (connector
   picker only — NOT acceptance, validation is deferred); `2: 400` with error
   body above. The 302 does not mean the URI was accepted.
3. Exact-match failed: full string differs (`localhost:3000` + `/callback` vs
   `localhost:3000.attacker.example` + `/callback`). Starts-with-prefix would
   pass; exact compare refuses.

### 4b — full attack if loose (reasoning)
Attacker crafts auth URL with `redirect_uri` under its control that a sloppy
rule still accepts, lures logged-in victim to open it; victim authenticates;
OP `302 → attacker-URL?code=…&state=…`; attacker reads code from its server
logs, then redeems at `token_endpoint` (needs client creds/verifier per 4c) and
impersonates victim / calls APIs as victim.

### 4c — PKCE cases
- (i) Legit client started flow, code leaks: attacker must also present
  `code_verifier` (+ `client_secret` for confidential `democlient`) at token
  endpoint. Both never travel through the browser (back channel only) — redeem
  fails without them.
- (ii) Attacker builds URL with own `code_challenge` for a public client
  (no secret), victim logs in: PKCE binds code to the initiator, so it stops
  code *injection* into someone else's session — but here the attacker IS the
  initiator holding the verifier, so PKCE gives the victim nothing. Left
  standing: exact `redirect_uri` match (+ `client_secret` only if confidential;
  for public clients, effectively just the redirect check + user vigilance).

### 4d — sloppy rules (registered `https://app.example.com/callback`)
1. Wildcard `https://*.example.com/callback` → attacker registers/controls
   `https://evil.example.com/callback` (needs subdomain + valid TLS).
2. Substring `contains app.example.com` → e.g.
   `https://app.example.com.attacker.example/callback` or
   `https://attacker.example/app.example.com/callback` (needs attacker domain + TLS).
3. Correct rule: exact string match against the pre-registered set (scheme +
   host + port + path, no patterns/wildcards). Closes all three — nothing to
   game, only the registered value passes. (dex v2.41.1 does this, even for
   loopback — no loose case to demo.)

## Ex.5 — ID-token validation (live, `$ID` from flow.py)
Tamper: change `email`→`attacker@evil.example`, `sub`→`attacker`, keep header +
signature (invalid). Script from guide, saved `/tmp/tamp.txt`.

### 5a — verify.py (correct)
```
REJECTED: InvalidSignatureError: Signature verification failed (exit=1)
```
Payload edited → signature (over header+payload with dex RSA key) no longer
matches JWKS key for `kid`. Correct verifier fetches JWKS, allow-lists
`RS256`, checks `iss/aud/exp` — any fails closed.

### 5b — verify_naive.py (wrong)
```
ACCEPTED (naively): trusting the payload without any signature check
  sub   = attacker
  email = attacker@evil.example (exit=0)
```
Skipped: everything — no key fetch, no signature check, no `iss/aud/exp`.
`alg:none` and `just decode` are the same failure: both treat an unsigned /
self-asserted payload as trusted because neither verifies a signature by an
expected key. (verify.py never trusts token `alg`; naive never even looks.)

### 5c — minimum correct checks (assessed, goes in report)
1. Signature: fetch JWKS via `jwks_uri`, pick key by `kid`, verify with
   allow-listed `RS256` (reject `none`/other; never trust token `alg`).
2. `iss` == expected issuer (`http://localhost:5556/dex`).
3. `aud` == this client (`democlient`; if multiple auds, `azp` must be client).
4. `exp` not passed (plus `iat` sanity, clock-skew window).
5. `nonce` == value sent in this auth request (ties token to this flow).
6. Before trusting: `state` seen before AND bound to the browser that started
   the flow (else valid token, wrong session — Reflection Q2).

## Reflection (Lab report 2, 266 words — in report2.tex)
1. Centralizing on dex buys real SSO: one credential, one policy, clients stop
   seeing passwords and only verify signatures via `jwks_uri` (as with
   `verify.py`). Cost: everything hinges on one key + user DB. Owning the IdP =
   minting ID tokens with any sub/email/aud/nonce → log into every client at
   once, plus access tokens. Local incident becomes ecosystem-wide (same shape
   as Lab 5 SSH CA — compare there).
2. Even with all of 5c passing, `client.py` stays unsafe: `PENDING` is global —
   any self-issued `state` accepted, never tied to the starting browser.
   Attacker starts own login, gets valid `code+state` (its identity), drives
   victim's browser to that `/callback?code&state`; client redeems with its
   stored verifier, sets `sid` → victim logged in as attacker (login
   CSRF/session fixation). Token genuine, login insecure: validation proves
   genuineness, not ownership by this browser. Past that point security is
   session management (bind state/nonce/verifier to initiator via own cookie),
   not token crypto.
