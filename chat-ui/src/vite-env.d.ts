/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_AGENT_BASE_URL: string;
  readonly VITE_BASE_PATH: string;
  readonly VITE_EMBEDDED: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
