/// <reference types="vite/client" />

interface ImportMetaEnv {
  /** Auth0 sign-in. All three set: Auth0; none: the development token box. */
  readonly VITE_AUTH0_DOMAIN?: string;
  readonly VITE_AUTH0_CLIENT_ID?: string;
  readonly VITE_AUTH0_AUDIENCE?: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
