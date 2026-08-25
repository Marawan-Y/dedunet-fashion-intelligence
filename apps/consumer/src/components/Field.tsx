import { useId, useState } from "react";
import type { InputHTMLAttributes, ReactNode, SelectHTMLAttributes } from "react";
import { cx } from "./primitives";
import styles from "./Field.module.css";

/* Accessible form controls.
 *
 * The id is generated with useId and threaded to the label, the hint and the error, so the
 * three associations that make a field usable — label/for, aria-describedby, aria-invalid —
 * cannot be forgotten at a call site. A page that hand-wires them is a page where one of
 * them is eventually missing.
 */

interface FieldShellProps {
  label: string;
  hint?: string;
  error?: string;
  optional?: boolean;
  children: (props: {
    id: string;
    describedBy: string | undefined;
    invalid: boolean;
    className: string;
  }) => ReactNode;
}

function FieldShell({ label, hint, error, optional, children }: FieldShellProps) {
  const id = useId();
  const hintId = `${id}-hint`;
  const errorId = `${id}-error`;

  /* Both, when both exist: the hint explains the format and the error says what went
     wrong, and dropping the hint the moment an error appears removes the information the
     customer needs to fix it. */
  const describedBy = [hint ? hintId : null, error ? errorId : null].filter(Boolean).join(" ");

  return (
    <div className={styles.field}>
      <label className={styles.label} htmlFor={id}>
        {label}
        {optional ? <span className={styles.optional}> (optional)</span> : null}
      </label>

      {children({
        id,
        describedBy: describedBy || undefined,
        invalid: Boolean(error),
        className: styles.control!,
      })}

      {hint ? (
        <p className={styles.hint} id={hintId}>
          {hint}
        </p>
      ) : null}

      {error ? (
        <p className={styles.error} id={errorId}>
          <svg
            className={styles.errorMark}
            viewBox="0 0 16 16"
            width="14"
            height="14"
            aria-hidden="true"
            focusable="false"
          >
            <path
              d="M8 1.5 15 14H1z M8 6.5v3.2 M8 11.6v.9"
              fill="none"
              stroke="currentColor"
              strokeWidth="1.5"
              strokeLinejoin="round"
            />
          </svg>
          {/* The word "Error" is carried in text, not implied by the colour. */}
          <span>
            <span className="sr-only">Error: </span>
            {error}
          </span>
        </p>
      ) : null}
    </div>
  );
}

type InputProps = Omit<InputHTMLAttributes<HTMLInputElement>, "id"> & {
  label: string;
  hint?: string;
  error?: string;
  optional?: boolean;
};

export function TextField({ label, hint, error, optional, ...rest }: InputProps) {
  return (
    <FieldShell label={label} hint={hint} error={error} optional={optional}>
      {({ id, describedBy, invalid, className }) => (
        <input
          {...rest}
          id={id}
          className={className}
          aria-describedby={describedBy}
          aria-invalid={invalid || undefined}
        />
      )}
    </FieldShell>
  );
}

/**
 * A password field with a visibility control.
 *
 * The control is a real button inside the field, announced with its state, because a
 * password rule a customer cannot check against is a password rule they fail repeatedly.
 */
export function PasswordField({ label, hint, error, ...rest }: InputProps) {
  const [visible, setVisible] = useState(false);

  return (
    <FieldShell label={label} hint={hint} error={error}>
      {({ id, describedBy, invalid, className }) => (
        <div className={styles.withAction}>
          <input
            {...rest}
            id={id}
            type={visible ? "text" : "password"}
            className={className}
            aria-describedby={describedBy}
            aria-invalid={invalid || undefined}
          />
          <button
            type="button"
            className={styles.action}
            onClick={() => setVisible((v) => !v)}
            aria-pressed={visible}
            aria-controls={id}
          >
            {visible ? "Hide" : "Show"}
          </button>
        </div>
      )}
    </FieldShell>
  );
}

type SelectProps = Omit<SelectHTMLAttributes<HTMLSelectElement>, "id"> & {
  label: string;
  hint?: string;
  error?: string;
  children: ReactNode;
};

export function SelectField({ label, hint, error, children, ...rest }: SelectProps) {
  return (
    <FieldShell label={label} hint={hint} error={error}>
      {({ id, describedBy, invalid, className }) => (
        <select
          {...rest}
          id={id}
          className={cx(className, styles.select)}
          aria-describedby={describedBy}
          aria-invalid={invalid || undefined}
        >
          {children}
        </select>
      )}
    </FieldShell>
  );
}

/** A checkbox whose whole row is the target. */
export function CheckboxField({
  label,
  ...rest
}: Omit<InputHTMLAttributes<HTMLInputElement>, "type"> & { label: string }) {
  const id = useId();
  return (
    <div className={styles.checkbox}>
      <input {...rest} id={id} type="checkbox" className={styles.checkboxInput} />
      <label htmlFor={id} className={styles.checkboxLabel}>
        {label}
      </label>
    </div>
  );
}

export function Form({
  children,
  onSubmit,
  ...rest
}: {
  children: ReactNode;
  onSubmit: (event: React.FormEvent<HTMLFormElement>) => void;
} & Record<string, unknown>) {
  return (
    <form className={styles.form} onSubmit={onSubmit} noValidate {...rest}>
      {children}
    </form>
  );
}
