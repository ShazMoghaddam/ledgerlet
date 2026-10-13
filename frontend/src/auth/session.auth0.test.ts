/**
 * The Auth0 side of the session, with the SDK replaced by a stand-in. The env is
 * read when the module loads, so each test loads a fresh copy.
 */
const client = {
  isAuthenticated: vi.fn(),
  getTokenSilently: vi.fn(),
  loginWithRedirect: vi.fn(),
  handleRedirectCallback: vi.fn(),
  logout: vi.fn(),
};
const createAuth0Client = vi.fn<(options: unknown) => Promise<typeof client>>(() =>
  Promise.resolve(client),
);
vi.mock("@auth0/auth0-spa-js", () => ({ createAuth0Client }));

async function load() {
  vi.resetModules();
  vi.stubEnv("VITE_AUTH0_DOMAIN", "ledgerlet.uk.auth0.com");
  vi.stubEnv("VITE_AUTH0_CLIENT_ID", "client-123");
  vi.stubEnv("VITE_AUTH0_AUDIENCE", "https://api.ledgerlet.app");
  return import("./session");
}

beforeEach(() => {
  Object.values(client).forEach((f) => f.mockReset());
  createAuth0Client.mockClear();
});
afterEach(() => vi.unstubAllEnvs());

it("uses Auth0 for the API, with rotating refresh tokens, returning to the callback page", async () => {
  client.isAuthenticated.mockResolvedValue(false);
  const session = await load();
  expect(session.signInMethod).toBe("auth0");
  await session.initSession();
  expect(createAuth0Client).toHaveBeenCalledWith({
    domain: "ledgerlet.uk.auth0.com",
    clientId: "client-123",
    authorizationParams: {
      audience: "https://api.ledgerlet.app",
      redirect_uri: `${window.location.origin}/sign-in/callback`,
    },
    cacheLocation: "localstorage",
    useRefreshTokens: true,
    useRefreshTokensFallback: false,
  });
  expect(session.isSignedIn()).toBe(false);
  expect(await session.getAccessToken()).toBeNull();
});

it("gives each request a fresh token while signed in", async () => {
  client.isAuthenticated.mockResolvedValue(true);
  client.getTokenSilently.mockResolvedValue("access-token");
  const session = await load();
  await session.initSession();
  expect(session.isSignedIn()).toBe(true);
  expect(await session.getAccessToken()).toBe("access-token");
});

it("signs out here when Auth0 says the session has ended", async () => {
  client.isAuthenticated.mockResolvedValue(true);
  client.getTokenSilently.mockRejectedValue(new Error("login_required"));
  const session = await load();
  await session.initSession();
  const changed = vi.fn();
  session.subscribe(changed);
  expect(await session.getAccessToken()).toBeNull();
  expect(session.isSignedIn()).toBe(false);
  expect(client.logout).toHaveBeenCalledWith({ openUrl: false });
  expect(changed).toHaveBeenCalled();
});

it("finishes signing in once, and goes where the landlord was heading", async () => {
  client.isAuthenticated.mockResolvedValueOnce(false).mockResolvedValue(true);
  client.handleRedirectCallback.mockResolvedValue({ appState: { next: "/tax" } });
  const session = await load();
  await session.initSession();
  const [a, b] = await Promise.all([session.finishSignIn(), session.finishSignIn()]);
  expect([a, b]).toEqual(["/tax", "/tax"]);
  expect(client.handleRedirectCallback).toHaveBeenCalledTimes(1);
  expect(session.isSignedIn()).toBe(true);
});

it("starts sign-in with where to come back to, and signs out of Auth0 too", async () => {
  client.isAuthenticated.mockResolvedValue(true);
  const session = await load();
  await session.initSession();
  await session.startSignIn("/properties");
  expect(client.loginWithRedirect).toHaveBeenCalledWith({ appState: { next: "/properties" } });
  session.signOut();
  expect(session.isSignedIn()).toBe(false);
  expect(client.logout).toHaveBeenCalledWith({
    logoutParams: { returnTo: `${window.location.origin}/sign-in` },
  });
});
