// HTTP Basic Auth for every Pages request, off unless AUTH_ENABLED is "true".
// Credentials come only from the Pages environment (SITE_USER, SITE_PASS).
// If either is missing while auth is on, respond 503 so the site is never served open.

async function digest(value) {
  const bytes = new TextEncoder().encode(value);
  const hash = await crypto.subtle.digest("SHA-256", bytes);
  return new Uint8Array(hash);
}

function timingSafeEqual(left, right) {
  if (left.length !== right.length) {
    return false;
  }
  let diff = 0;
  for (let i = 0; i < left.length; i += 1) {
    diff |= left[i] ^ right[i];
  }
  return diff === 0;
}

async function secretEqual(provided, expected) {
  const [left, right] = await Promise.all([digest(provided), digest(expected)]);
  return timingSafeEqual(left, right);
}

function decodeBasic(header) {
  const match = /^Basic\s+([A-Za-z0-9+/=_-]+)$/i.exec((header || "").trim());
  if (!match) {
    return null;
  }
  let bytes;
  try {
    const binary = atob(match[1]);
    bytes = Uint8Array.from(binary, (char) => char.charCodeAt(0));
  } catch {
    return null;
  }
  const text = new TextDecoder().decode(bytes);
  const separator = text.indexOf(":");
  if (separator < 0) {
    return null;
  }
  return {
    user: text.slice(0, separator),
    pass: text.slice(separator + 1),
  };
}

function text(status, body, extraHeaders) {
  return new Response(body, {
    status,
    headers: {
      "Content-Type": "text/plain; charset=utf-8",
      "Cache-Control": "no-store",
      "X-Robots-Tag": "noindex, nofollow",
      ...extraHeaders,
    },
  });
}

export async function onRequest(context) {
  const env = context.env || {};
  if (env.AUTH_ENABLED !== "true") {
    return context.next();
  }
  const user = env.SITE_USER;
  const pass = env.SITE_PASS;
  if (typeof user !== "string" || typeof pass !== "string" || user.length === 0 || pass.length === 0) {
    return text(503, "Authentication is not configured.\n");
  }

  const provided = decodeBasic(context.request.headers.get("Authorization"));
  const userOk = await secretEqual(provided ? provided.user : "", user);
  const passOk = await secretEqual(provided ? provided.pass : "", pass);
  if (((userOk ? 1 : 0) & (passOk ? 1 : 0)) !== 1) {
    return text(401, "Authentication required.\n", {
      "WWW-Authenticate": 'Basic realm="CAPA", charset="UTF-8"',
    });
  }

  const response = await context.next();
  const headers = new Headers(response.headers);
  headers.set("Cache-Control", "private, no-store");
  headers.set("X-Robots-Tag", "noindex, nofollow");
  return new Response(response.body, {
    status: response.status,
    statusText: response.statusText,
    headers,
  });
}
