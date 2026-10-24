import { defineConfig } from 'vitest/config';

export default defineConfig({
  // A new repo has no tests yet. Remove this once the first test lands, so a
  // broken include pattern fails instead of passing.
  test: { passWithNoTests: true },
});
