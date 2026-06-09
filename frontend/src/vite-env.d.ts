/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_API_BASE: string;
  readonly VITE_TELEGRAM_BOT: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
