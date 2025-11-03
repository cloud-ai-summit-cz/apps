/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_TOY_SERVICE_URL?: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
