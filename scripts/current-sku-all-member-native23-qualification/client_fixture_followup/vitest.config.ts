import { defineConfig, mergeConfig } from 'vite'
import original from '../../../vite.config.ts'

// Supplemental family15 only. The existing main72 command/artifact stays exact.
export default defineConfig(env => mergeConfig(
  typeof original === 'function' ? original(env) : original,
  { test: { include: ['scripts/current-sku-all-member-native23-qualification/client_fixture_followup/sku-pair-conversion.derived.test.ts'], hookTimeout: 60_000, testTimeout: 60_000 } },
))
