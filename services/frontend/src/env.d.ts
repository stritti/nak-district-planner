/// <reference types="vite/client" />

/** Frontend version, injected from package.json at build time (vite `define`). */
declare const __APP_VERSION__: string

declare module '*.vue' {
  import type { DefineComponent } from 'vue'
  const component: DefineComponent<object, object, unknown>
  export default component
}
