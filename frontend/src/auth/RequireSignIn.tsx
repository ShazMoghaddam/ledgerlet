import { Navigate, Outlet, useLocation } from "react-router";

import { useSignedIn } from "./useSession";

export function RequireSignIn() {
  const signedIn = useSignedIn();
  const location = useLocation();
  if (!signedIn) {
    const next = encodeURIComponent(location.pathname + location.search);
    return <Navigate to={`/sign-in?next=${next}`} replace />;
  }
  return <Outlet />;
}
