import type { ButtonHTMLAttributes, ReactNode } from "react";
import { Link, type LinkProps } from "react-router";

import s from "./Button.module.css";

type Variant = "primary" | "secondary" | "quiet";

interface Look {
  variant?: Variant;
  size?: "normal" | "large";
  block?: boolean;
}

function classes({ variant = "primary", size = "normal", block = false }: Look, extra?: string) {
  return [s.button, s[variant], size === "large" && s.large, block && s.block, extra]
    .filter(Boolean)
    .join(" ");
}

export function Button({
  variant,
  size,
  block,
  className,
  type = "button",
  ...rest
}: Look & ButtonHTMLAttributes<HTMLButtonElement>) {
  return <button type={type} className={classes({ variant, size, block }, className)} {...rest} />;
}

/** Navigation that looks like a button: it goes somewhere, so it's a link. */
export function ButtonLink({
  variant,
  size,
  block,
  className,
  children,
  ...rest
}: Look & LinkProps & { children: ReactNode }) {
  return (
    <Link className={classes({ variant, size, block }, className)} {...rest}>
      {children}
    </Link>
  );
}
