/// <reference types="vitest/config" />
import { defineConfig } from 'vitest/config'

// Separate vitest config (vitest 3 bundles vite 7; project uses vite 8 with rolldown,
// so mixing defineConfig from vitest/config and vite plugins causes plugin-type mismatches).
// Tests are pure TS with no DOM or React — no vite plugins needed here.
export default defineConfig({
  test: {
    environment: 'node',
    include: ['src/**/*.test.ts'],
  },
})
