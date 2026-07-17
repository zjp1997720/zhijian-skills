import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const here = path.dirname(fileURLToPath(import.meta.url));
const skillDir = path.resolve(here, '..');

const read = (relative) => fs.readFileSync(path.join(skillDir, relative), 'utf8');
const json = (relative) => JSON.parse(read(relative));

const skill = read('SKILL.md');
for (const phrase of [
  '$imagegen',
  'explicit restart authorization',
  'codex-theme-v1:',
  'rollback boundary',
  'missing evidence',
]) {
  assert.ok(skill.includes(phrase), `SKILL.md must include ${phrase}`);
}

const triggers = json('evals/trigger_cases.json');
assert.ok(triggers.should_trigger.length >= 8, 'trigger eval needs broad positive coverage');
assert.ok(triggers.should_not_trigger.length >= 8, 'trigger eval needs broad negative coverage');
assert.ok(triggers.near_neighbor.length >= 4, 'trigger eval needs near-neighbor coverage');

const caseLines = read('evals/output/cases.jsonl').trim().split('\n');
assert.ok(caseLines.length >= 5, 'output eval needs at least five cases');
for (const line of caseLines) {
  const item = JSON.parse(line);
  assert.ok(item.id && item.prompt && item.baseline_output && item.with_skill_output);
  assert.ok(Array.isArray(item.assertions) && item.assertions.length >= 3);
  for (const input of item.input_files ?? []) {
    assert.ok(fs.existsSync(path.join(skillDir, 'evals/output', input)), `missing fixture ${input}`);
  }
}

const ir = json('skill-ir/examples/codex-theme-studio.json');
assert.equal(ir.schema_version, '2.0.0');
assert.equal(ir.name, 'codex-theme-studio');
assert.equal(ir.risk.trust_boundary, 'external');
assert.ok(ir.workflow.failure_modes.length >= 6);
assert.equal(ir.resources.reports, undefined, 'generated reports are local evidence, not release resources');
for (const baseline of ['references/output-eval-baseline.md', 'security/trust-baseline.md']) {
  assert.ok(fs.existsSync(path.join(skillDir, baseline)), `missing checked-in source baseline ${baseline}`);
  assert.ok(skill.includes(baseline), `SKILL.md must route to ${baseline}`);
}

const manifest = json('manifest.json');
assert.ok(!manifest.factory_components.includes('reports'), 'manifest must not publish generated reports');

const permissions = json('security/permission_policy.json');
for (const capability of ['network', 'file_write', 'subprocess']) {
  assert.equal(permissions.capabilities[capability].decision, 'approved');
}
const network = json('security/network_policy.json');
assert.equal(network.default_policy.outbound_internet, 'deny');
assert.equal(network.default_policy.loopback_only, true);

console.log('PASS: governed Skill, ImageGen, eval, and trust contracts are present.');
