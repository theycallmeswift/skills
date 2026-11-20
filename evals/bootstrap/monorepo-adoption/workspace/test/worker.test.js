import assert from 'node:assert/strict';
import { test } from 'node:test';
import { route } from '../src/worker.js';

test('known paths have a handler', () => {
  assert.ok(route('/health'));
  assert.ok(route('/digest'));
});

test('unknown paths have none', () => {
  assert.equal(route('/nope'), null);
});
