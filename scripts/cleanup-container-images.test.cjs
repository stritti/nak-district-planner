// SPDX-FileCopyrightText: 2026 Stephan Strittmatter
// SPDX-License-Identifier: AGPL-3.0-only

'use strict';

const test = require('node:test');
const assert = require('node:assert/strict');
const { isCandidate, cleanup } = require('./cleanup-container-images.cjs');

function version(id, tags, name = 'sha256:' + id) {
  return { id, name, metadata: { container: { tags } } };
}

test('release aliases, mixed tags, unknown tags and untagged manifests are protected', () => {
  for (const tags of [[], ['latest'], ['1'], ['1.0'], ['1.0.0'], ['1.0.0-rc.7'],
    ['sha-abcdef0', '1.0.0-rc.7'], ['main', 'latest'], ['feature/test'], ['sha-not-a-sha']]) {
    assert.equal(isCandidate(version(1, tags)), false, JSON.stringify(tags));
  }
  assert.equal(isCandidate({ id: 1 }), false);
  assert.equal(isCandidate(version(1, ['main', 'sha-abcdef0'])), true);
  assert.equal(isCandidate(version(1, ['develop'])), true);
});

function mock(batches, refreshed = {}) {
  const calls = [];
  return {
    calls,
    request: async (method, endpoint) => {
      calls.push({ method, endpoint });
      if (method === 'DELETE') return;
      if (endpoint.includes('?')) return batches[endpoint] ?? [];
      return refreshed[endpoint];
    }
  };
}

const root = '/users/stritti/packages/container/nak-district-planner%2F';

test('preview paginates and never deletes; release tags protect the same digest', async () => {
  const first = Array.from({ length: 100 }, (_, i) => version(i + 1, ['1.0.0']));
  const api = mock({
    [root + 'backend/versions?per_page=100&page=1']: first,
    [root + 'backend/versions?per_page=100&page=2']: [
      version(101, ['sha-abcdef0']), version(102, ['main'], first[0].name)
    ],
    [root + 'frontend/versions?per_page=100&page=1']: [version(201, [])]
  });
  const result = await cleanup({ ...api, owner: 'stritti', repository: 'nak-district-planner',
    mode: 'preview', log: () => {} });
  assert.deepEqual(result, { candidates: 1, deleted: 0 });
  assert.equal(api.calls.filter((c) => c.method === 'DELETE').length, 0);
  assert.ok(api.calls.some((c) => c.endpoint.endsWith('page=2')));
});

test('delete rechecks tags and skips a version that acquired a release tag', async () => {
  const api = mock({
    [root + 'backend/versions?per_page=100&page=1']: [version(1, ['main']), version(2, ['sha-abcdef0'])],
    [root + 'frontend/versions?per_page=100&page=1']: [version(3, ['1.0.0-rc.7'])]
  }, {
    [root + 'backend/versions/1']: version(1, ['main', '1.0.0']),
    [root + 'backend/versions/2']: version(2, ['sha-abcdef0'])
  });
  const result = await cleanup({ ...api, owner: 'stritti', repository: 'nak-district-planner',
    mode: 'delete', log: () => {} });
  assert.deepEqual(result, { candidates: 2, deleted: 1 });
  assert.deepEqual(api.calls.filter((c) => c.method === 'DELETE'),
    [{ method: 'DELETE', endpoint: root + 'backend/versions/2' }]);
});

test('listing failure aborts before deleting anything', async () => {
  const api = mock({ [root + 'backend/versions?per_page=100&page=1']: [version(1, ['main'])] });
  const request = async (method, endpoint) => {
    if (endpoint.includes('frontend')) throw new Error('HTTP 403');
    return api.request(method, endpoint);
  };
  await assert.rejects(cleanup({ request, owner: 'stritti', repository: 'nak-district-planner',
    mode: 'delete', log: () => {} }), /403/);
  assert.equal(api.calls.filter((c) => c.method === 'DELETE').length, 0);
});
