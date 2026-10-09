import { Navigate, Outlet, useLocation } from "react-router";

import { useToken } from "./useSession";

export function RequireSignIn() {
  const token = useToken();
  const location = useLocation();
  if (!token) {
    const next = encodeURIComponent(location.pathname + location.search);
    return <Navigate to={`/sign-in?next=${next}`} replace />;
  }
  return <Outlet />;
}
