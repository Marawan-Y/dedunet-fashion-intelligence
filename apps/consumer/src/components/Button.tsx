import type { ButtonHTMLAttributes, ReactNode } from "react";
import { Link } from "react-router-dom";
import { cx } from "./primitives";
import styles from "./Button.module.css";

export type ButtonVariant = "primary" | "accent" | "secondary" | "quiet" | "link";

function variantClass(variant: ButtonVariant): string {
  return styles[variant]!;
}

interface CommonProps {
  variant?: ButtonVariant;
  fullWidth?: boolean;
  children: ReactNode;
  className?: string;
}

type ButtonProps = CommonProps & ButtonHTMLAttributes<HTMLButtonElement>;

export function Button({
  variant = "primary",
  fullWidth,
  className,
  children,
  type = "button",
  ...rest
}: ButtonProps) {
  return (
    <button
      type={type}
      className={cx(styles.base, variantClass(variant), fullWidth && styles.full, className)}
      {...rest}
    >
      {children}
    </button>
  );
}

/**
 * A link that looks like a button.
 *
 * A separate component rather than a prop, because the two are different elements with
 * different semantics: a link navigates and belongs in the tab order as a link, a button
 * performs an action. Styling them alike is a visual decision; conflating them is an
 * accessibility bug.
 */
export function ButtonLink({
  to,
  variant = "primary",
  fullWidth,
  className,
  children,
  ...rest
}: CommonProps & { to: string } & Record<string, unknown>) {
  const external = /^https?:\/\//i.test(to);

  if (external) {
    return (
      <a
        href={to}
        className={cx(styles.base, variantClass(variant), fullWidth && styles.full, className)}
        rel="noopener noreferrer"
        target="_blank"
        {...rest}
      >
        {children}
      </a>
    );
  }

  return (
    <Link
      to={to}
      className={cx(styles.base, variantClass(variant), fullWidth && styles.full, className)}
      {...rest}
    >
      {children}
    </Link>
  );
}
