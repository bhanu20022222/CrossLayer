import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type FormEvent,
  type ReactNode,
} from "react";

interface SessionStatus {
  configured: boolean;
  authenticated: boolean;
  username: string | null;
}

interface AuthContextValue {
  username: string;
  logoutError: string | null;
  logout: () => Promise<void>;
}

const AuthContext = createContext<AuthContextValue | null>(null);

async function responseError(response: Response) {
  try {
    const body = (await response.json()) as { detail?: string };
    return body.detail ?? `Request failed (${response.status})`;
  } catch {
    return `Request failed (${response.status})`;
  }
}

function LoginScreen({
  onLogin,
  initialError,
}: {
  onLogin: (username: string, password: string) => Promise<void>;
  initialError: string | null;
}) {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(initialError);
  const [submitting, setSubmitting] = useState(false);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      await onLogin(username, password);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Login failed");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <main className="auth-page">
      <section className="auth-card" aria-labelledby="login-title">
        <div className="auth-mark" aria-hidden="true">CL</div>
        <p className="auth-eyebrow">CROSSLAYER RESEARCH DASHBOARD</p>
        <h1 id="login-title">Sign in</h1>
        <p className="auth-description">
          Authenticate to view cluster telemetry and network-affinity results.
        </p>
        <form className="auth-form" onSubmit={submit}>
          <label htmlFor="username">Username</label>
          <input
            id="username"
            name="username"
            autoComplete="username"
            value={username}
            onChange={(event) => setUsername(event.target.value)}
            required
            maxLength={128}
          />
          <label htmlFor="password">Password</label>
          <input
            id="password"
            name="password"
            type="password"
            autoComplete="current-password"
            value={password}
            onChange={(event) => setPassword(event.target.value)}
            required
            maxLength={1024}
          />
          {error ? <p className="auth-error" role="alert">{error}</p> : null}
          <button type="submit" className="auth-submit" disabled={submitting}>
            {submitting ? "Signing in..." : "Sign in to dashboard"}
          </button>
        </form>
        <p className="auth-footer">Session protected · HTTP-only cookie</p>
      </section>
    </main>
  );
}

function AuthSetupScreen() {
  return (
    <main className="auth-page">
      <section className="auth-card auth-setup" aria-labelledby="setup-title">
        <div className="auth-mark" aria-hidden="true">CL</div>
        <p className="auth-eyebrow">CROSSLAYER RESEARCH DASHBOARD</p>
        <h1 id="setup-title">Login needs configuration</h1>
        <p className="auth-description">
          The dashboard API is fail-closed. Set credentials and a private signing secret
          in the backend environment, then restart the backend.
        </p>
        <pre>{`$env:CROSSLAYER_AUTH_USERNAME = "your-user"
$env:CROSSLAYER_AUTH_PASSWORD = "your-private-password"
$bytes = New-Object byte[] 32
        $rng = [Security.Cryptography.RandomNumberGenerator]::Create()
        $rng.GetBytes($bytes)
        $env:CROSSLAYER_AUTH_SECRET = [Convert]::ToBase64String($bytes)`}</pre>
        <p className="auth-footer">
          Do not commit credentials. Use HTTPS and set CROSSLAYER_AUTH_COOKIE_SECURE=true
          when serving outside localhost.
        </p>
      </section>
    </main>
  );
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [session, setSession] = useState<SessionStatus | null>(null);
  const [sessionError, setSessionError] = useState<string | null>(null);
  const [logoutError, setLogoutError] = useState<string | null>(null);

  const refreshSession = useCallback(async () => {
    try {
      const response = await fetch("/api/v1/auth/session", {
        credentials: "same-origin",
      });
      if (!response.ok) throw new Error(await responseError(response));
      const status = (await response.json()) as SessionStatus;
      setSession(status);
      setSessionError(null);
    } catch (error) {
      setSessionError(error instanceof Error ? error.message : "Could not reach the dashboard API");
    }
  }, []);

  useEffect(() => {
    void refreshSession();
    const onUnauthorized = () => {
      setSession((current) =>
        current ? { ...current, authenticated: false, username: null } : current,
      );
    };
    window.addEventListener("crosslayer:unauthorized", onUnauthorized);
    return () => window.removeEventListener("crosslayer:unauthorized", onUnauthorized);
  }, [refreshSession]);

  const login = useCallback(async (username: string, password: string) => {
    const response = await fetch("/api/v1/auth/login", {
      method: "POST",
      credentials: "same-origin",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ username, password }),
    });
    if (!response.ok) throw new Error(await responseError(response));
    const body = (await response.json()) as { username: string };
    setSession({ configured: true, authenticated: true, username: body.username });
    setSessionError(null);
  }, []);

  const logout = useCallback(async () => {
    try {
      const response = await fetch("/api/v1/auth/logout", {
        method: "POST",
        credentials: "same-origin",
      });
      if (!response.ok) throw new Error(await responseError(response));
      setLogoutError(null);
      setSession((current) =>
        current ? { ...current, authenticated: false, username: null } : current,
      );
    } catch (error) {
      const message = error instanceof Error ? error.message : "Could not sign out";
      setLogoutError(message);
      throw error;
    }
  }, []);

  const value = useMemo(
    () =>
      session?.username
        ? { username: session.username, logout, logoutError }
        : null,
    [session?.username, logout, logoutError],
  );

  if (!session) {
    return (
      <main className="auth-page">
        <p className={sessionError ? "auth-error" : "auth-loading"} role="status">
          {sessionError ?? "Checking dashboard session..."}
        </p>
        {sessionError ? (
          <button type="button" onClick={() => void refreshSession()}>Retry</button>
        ) : null}
      </main>
    );
  }
  if (!session.configured) return <AuthSetupScreen />;
  if (!session.authenticated || !value) {
    return <LoginScreen onLogin={login} initialError={sessionError} />;
  }

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const value = useContext(AuthContext);
  if (!value) throw new Error("useAuth must be used inside an authenticated dashboard");
  return value;
}
