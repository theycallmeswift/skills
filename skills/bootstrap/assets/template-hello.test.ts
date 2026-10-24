import { expect, it } from 'vitest';

it('says hello to the world', () => {
  expect(`hello, ${'world'}`).toBe('hello, world');
});
