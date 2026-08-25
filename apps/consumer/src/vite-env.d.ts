/// <reference types="vite/client" />

/* The build-time configuration seam.
 *
 * Declared rather than left to the ambient ImportMetaEnv index signature so a typo in a
 * variable name is a compile error instead of an undefined that silently takes the
 * fallback branch. */
interface ImportMetaEnv {
  /** Absolute origin of the commerce API, baked in at image build. */
  readonly VITE_API_BASE_URL?: string;
  /** "true" when a gateway fronts both this client and the API on one origin. */
  readonly VITE_API_SAME_ORIGIN?: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
