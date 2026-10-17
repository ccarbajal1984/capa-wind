// Session login for every Pages request. Auth is on unless AUTH_ENABLED is
// exactly "false". Credentials come only from the Pages environment
// (SITE_USER, SITE_PASS). SESSION_SECRET, when set, is the cookie signing
// key; otherwise the key is derived from SITE_PASS. If either credential is
// missing while auth is on, respond 503 so the site is never served open.

const COOKIE = "capa_session";
const MAX_AGE = 60 * 60 * 24 * 30;

const PUBLIC_PATHS = new Set([
  "/login",
  "/logout",
  "/favicon.svg",
  "/favicon.ico",
  "/apple-touch-icon.png",
  "/assets/capa-logo.svg",
]);

function text(status, body) {
  return new Response(body, {
    status,
    headers: {
      "Content-Type": "text/plain; charset=utf-8",
      "Cache-Control": "no-store",
      "X-Robots-Tag": "noindex, nofollow",
    },
  });
}

function escapeHtml(value) {
  return String(value).replace(/[&<>"']/g, (ch) => ({
    "&": "&amp;",
    "<": "&lt;",
    ">": "&gt;",
    '"': "&quot;",
    "'": "&#39;",
  }[ch]));
}

function bytesToB64url(bytes) {
  let binary = "";
  const view = bytes instanceof Uint8Array ? bytes : new Uint8Array(bytes);
  for (let i = 0; i < view.length; i += 1) binary += String.fromCharCode(view[i]);
  return btoa(binary).replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/g, "");
}

function b64urlToBytes(value) {
  const padded = value.replace(/-/g, "+").replace(/_/g, "/") + "===".slice((value.length + 3) % 4);
  const binary = atob(padded);
  const out = new Uint8Array(binary.length);
  for (let i = 0; i < binary.length; i += 1) out[i] = binary.charCodeAt(i);
  return out;
}

function timingSafeEqual(left, right) {
  const length = Math.max(left.length, right.length);
  let diff = left.length ^ right.length;
  for (let i = 0; i < length; i += 1) {
    diff |= (left[i] || 0) ^ (right[i] || 0);
  }
  return diff === 0;
}

async function digest(value) {
  const hash = await crypto.subtle.digest("SHA-256", new TextEncoder().encode(value));
  return new Uint8Array(hash);
}

async function secretEqual(provided, expected) {
  const [left, right] = await Promise.all([digest(provided), digest(expected)]);
  return timingSafeEqual(left, right);
}

function configured(env) {
  const user = typeof env.SITE_USER === "string" ? env.SITE_USER.trim() : "";
  const pass = typeof env.SITE_PASS === "string" ? env.SITE_PASS.trim() : "";
  if (!user || !pass) return null;
  const sessionSecret = typeof env.SESSION_SECRET === "string" ? env.SESSION_SECRET.trim() : "";
  return { user, pass, keyMaterial: sessionSecret || pass };
}

async function signingKey(material) {
  const derived = await digest(`capa-session-v1\0${material}`);
  return crypto.subtle.importKey("raw", derived, { name: "HMAC", hash: "SHA-256" }, false, ["sign"]);
}

async function sign(material, payload) {
  const key = await signingKey(material);
  const mac = await crypto.subtle.sign("HMAC", key, new TextEncoder().encode(payload));
  return bytesToB64url(mac);
}

function sessionCookie(value, maxAge) {
  return [
    `${COOKIE}=${value}`,
    "HttpOnly",
    "Secure",
    "SameSite=Lax",
    "Path=/",
    `Max-Age=${maxAge}`,
  ].join("; ");
}

function readCookie(header) {
  if (!header) return "";
  for (const part of header.split(";")) {
    const item = part.trim();
    const eq = item.indexOf("=");
    if (eq > 0 && item.slice(0, eq) === COOKIE) return item.slice(eq + 1);
  }
  return "";
}

function safeNext(value) {
  if (typeof value !== "string" || value.length === 0 || value.length > 512) return "/";
  if (!value.startsWith("/") || value.startsWith("//") || value.startsWith("/\\")) return "/";
  if (/[\u0000-\u001f\\]/.test(value) || value.includes("://")) return "/";
  if (value === "/login" || value.startsWith("/login?") || value.startsWith("/logout")) return "/";
  return value;
}

async function issueSession(creds, username) {
  const exp = Date.now() + MAX_AGE * 1000;
  const payload = bytesToB64url(new TextEncoder().encode(JSON.stringify({ u: username, exp })));
  const mac = await sign(creds.keyMaterial, payload);
  return sessionCookie(`${payload}.${mac}`, MAX_AGE);
}

async function readSession(request, creds) {
  const token = readCookie(request.headers.get("Cookie"));
  const dot = token.indexOf(".");
  if (dot <= 0 || dot !== token.lastIndexOf(".")) return null;
  const payload = token.slice(0, dot);
  const mac = token.slice(dot + 1);
  let expected;
  try {
    expected = await sign(creds.keyMaterial, payload);
  } catch {
    return null;
  }
  const left = b64urlToBytesSafe(mac);
  const right = b64urlToBytesSafe(expected);
  if (!left || !right || !timingSafeEqual(left, right)) return null;
  let data;
  try {
    data = JSON.parse(new TextDecoder().decode(b64urlToBytes(payload)));
  } catch {
    return null;
  }
  if (!data || typeof data.exp !== "number" || data.exp < Date.now()) return null;
  if (typeof data.u !== "string" || data.u !== creds.user.toLowerCase()) return null;
  return data;
}

function b64urlToBytesSafe(value) {
  if (!/^[A-Za-z0-9_-]+$/.test(value)) return null;
  try {
    return b64urlToBytes(value);
  } catch {
    return null;
  }
}

function loginPage(nextPath, error) {
  const next = escapeHtml(nextPath);
  const message = error
    ? `<p class="err" role="alert">${escapeHtml(error)}</p>`
    : "";
  const html = `<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<title>Log in · CAPA ESP 99</title>
<link rel="icon" href="/favicon.svg" type="image/svg+xml">
<meta name="theme-color" content="#0B1F3A">
<meta name="robots" content="noindex, nofollow">
<style>
*{box-sizing:border-box}html,body{margin:0;min-height:100%;background:#0B1F3A;color:#EAF2FB;font:15px/1.4 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif}
body{display:flex;align-items:center;justify-content:center;padding:24px}
form{width:min(380px,100%);background:#13304F;border:1px solid #2A4A70;border-radius:16px;padding:22px 20px 18px}
.boat{display:block;height:136px;width:auto;margin:2px auto 10px}
.brand{display:flex;flex-direction:column;align-items:center;gap:2px;margin-bottom:12px;text-align:center}
.brand b{display:block;font-size:18px;letter-spacing:.06em}
.brand span{color:#8FA8C4;font-size:12px}
h1{font-size:18px;margin:0 0 12px}
label{display:block;font-size:12px;font-weight:700;color:#8FA8C4;margin:10px 0 4px}
input{width:100%;font:16px/1.3 inherit;color:#EAF2FB;background:#0B1F3A;border:1px solid #2A4A70;border-radius:10px;padding:10px 12px}
button{width:100%;margin-top:16px;font:700 15px/1 inherit;color:#0B1F3A;background:#f5c542;border:0;border-radius:999px;padding:11px 14px;cursor:pointer}
.err{background:#3a2410;border:1px solid #f5c542;color:#f5c542;border-radius:8px;padding:8px 10px;margin:0 0 8px;font-size:13px}
</style></head><body>
<form method="post" action="/login">
  <img class="boat" src="/assets/capa-logo.svg" alt="" width="100" height="136">
  <div class="brand"><b>CAPA</b><span>ESP 99 · Bay of Palma</span></div>
  <h1>Log in</h1>
  ${message}
  <input type="hidden" name="next" value="${next}">
  <label for="username">Username</label>
  <input id="username" name="username" autocomplete="username" autocapitalize="none" required>
  <label for="password">Password</label>
  <input id="password" name="password" type="password" autocomplete="current-password" required>
  <button type="submit">Log in</button>
</form></body></html>`;
  return new Response(html, {
    status: error ? 401 : 200,
    headers: {
      "Content-Type": "text/html; charset=utf-8",
      "Cache-Control": "no-store",
      "X-Robots-Tag": "noindex, nofollow",
    },
  });
}

function redirect(location, setCookie) {
  const headers = {
    Location: location,
    "Cache-Control": "no-store",
    "X-Robots-Tag": "noindex, nofollow",
  };
  if (setCookie) headers["Set-Cookie"] = setCookie;
  return new Response(null, { status: 302, headers });
}

async function credentialsMatch(creds, username, password) {
  const userOk = await secretEqual(username.trim().toLowerCase(), creds.user.toLowerCase());
  const passOk = await secretEqual(password.trim(), creds.pass);
  return ((userOk ? 1 : 0) & (passOk ? 1 : 0)) === 1;
}

async function privateResponse(response) {
  const headers = new Headers(response.headers);
  headers.set("Cache-Control", "private, no-store");
  headers.set("X-Robots-Tag", "noindex, nofollow");
  return new Response(response.body, {
    status: response.status,
    statusText: response.statusText,
    headers,
  });
}

export async function onRequest(context) {
  const env = context.env || {};
  if (env.AUTH_ENABLED === "false") return context.next();

  const creds = configured(env);
  if (!creds) return text(503, "Authentication is not configured.\n");

  const url = new URL(context.request.url);
  const path = url.pathname;

  if (path === "/logout") {
    return redirect("/login", sessionCookie("", 0));
  }

  if (path === "/login") {
    const nextPath = safeNext(url.searchParams.get("next"));
    if (context.request.method === "POST") {
      let form;
      try {
        form = await context.request.formData();
      } catch {
        return loginPage("/", "That username or password is not right.");
      }
      const next = safeNext(String(form.get("next") || nextPath));
      const username = String(form.get("username") || "");
      const password = String(form.get("password") || "");
      if (!(await credentialsMatch(creds, username, password))) {
        return loginPage(next, "That username or password is not right.");
      }
      return redirect(next, await issueSession(creds, username.trim().toLowerCase()));
    }
    if (await readSession(context.request, creds)) return redirect(nextPath);
    return loginPage(nextPath, "");
  }

  if (PUBLIC_PATHS.has(path)) return context.next();

  if (!(await readSession(context.request, creds))) {
    const next = safeNext(path + url.search);
    return redirect(`/login?next=${encodeURIComponent(next)}`);
  }

  return privateResponse(await context.next());
}
