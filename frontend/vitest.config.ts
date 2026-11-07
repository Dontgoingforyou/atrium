import { mkdirSync } from 'node:fs'
import path from 'node:path'
import { fileURLToPath } from 'node:url'
import { defineConfig } from 'vitest/config'

const __dirname = path.dirname(fileURLToPath(import.meta.url))

// Vitest 4 пишет transform-кэш в os.tmpdir()/nanoid/{client,ssr}.
// /tmp на этой машине то EROFS, то каталог успевает исчезнуть (ENOENT mkdir).
const vitestTmp = path.resolve(__dirname, 'node_modules/.vite/tmp')
mkdirSync(vitestTmp, { recursive: true })
process.env.TMPDIR = vitestTmp

/**
 * Unit-тесты без React (domain/utils и др.); без @vitejs/plugin-react из-за конфликта версий Vite.
 *
 * Coverage считается только по слою чистой логики (как «app/» на бэке), не по всему SPA:
 * страницы/компоненты в порог CI не входят.
 */
export default defineConfig({
  // Vite 8 пишет environments в cacheDir/client и cacheDir/ssr.
  // Дефолт в /tmp/<random> на внешнем диске/после npm ci даёт ENOENT mkdir.
  cacheDir: path.resolve(__dirname, 'node_modules/.vite'),
  resolve: {
    alias: {
      '@': path.resolve(__dirname, 'src'),
    },
  },
  test: {
    environment: 'node',
    include: ['tests/**/*.test.ts'],
    /** Один воркер: меньше пик по ОЗУ (много параллельных node/vitest на машине разработчика). */
    maxWorkers: 1,
    coverage: {
      provider: 'v8',
      include: ['src/domain/**/*.{ts,tsx}', 'src/utils/**/*.{ts,tsx}'],
      exclude: [
        'src/**/*.d.ts',
        'src/**/*.module.css',
        '**/node_modules/**',
      ],
      reporter: ['text', 'text-summary', 'html', 'cobertura'],
      reportsDirectory: './coverage',
      thresholds: {
        lines: 70,
        statements: 70,
        functions: 70,
        branches: 55,
      },
    },
  },
})
