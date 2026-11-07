/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_API_BASE?: string
  readonly VITE_SPA_REDIRECT_URI?: string
}

interface ImportMeta {
  readonly env: ImportMetaEnv
}
