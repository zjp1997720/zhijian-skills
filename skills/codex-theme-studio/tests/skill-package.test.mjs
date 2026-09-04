import assert from "node:assert/strict";
import fs from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const version = (await fs.readFile(path.join(root, "VERSION"), "utf8")).trim();
const manifest = JSON.parse(await fs.readFile(path.join(root, "manifest.json"), "utf8"));
const skill = await fs.readFile(path.join(root, "SKILL.md"), "utf8");
const openai = await fs.readFile(path.join(root, "agents/openai.yaml"), "utf8");
const interfaceYaml = await fs.readFile(path.join(root, "agents/interface.yaml"), "utf8");
const triggerCases = JSON.parse(await fs.readFile(path.join(root, "evals/trigger_cases.json"), "utf8"));
const outputCases = (await fs.readFile(path.join(root, "evals/output/cases.jsonl"), "utf8"))
  .trim().split("\n").map(JSON.parse);

assert.equal(manifest.name, "codex-theme-studio");
assert.equal(manifest.version, version);
assert.equal(manifest.maturity_tier, "governed");
assert.equal(manifest.lifecycle_stage, "governed");
assert.equal(manifest.review_cadence, "per-release");
assert.match(skill, /^---\nname: codex-theme-studio\n/m);
assert.match(skill, /Do not use for Windows, Linux, ChatGPT web, ZCode, Doubao Work/);
assert.match(skill, /output contract/);
assert.match(skill, /file-backed fixture/);
assert.match(skill, /rollback boundary/);
assert.match(skill, /trust report/);
assert.match(skill, /missing evidence/);
assert.match(openai, /\$codex-theme-studio/);
assert.match(interfaceYaml, /^name: codex-theme-studio$/m);
assert.ok(triggerCases.should_trigger.length >= 4);
assert.ok(triggerCases.should_not_trigger.length >= 4);
assert.ok(triggerCases.edge_cases.length >= 3);
assert.equal(outputCases.length, 3);

let baselinePasses = 0;
let withSkillPasses = 0;
let assertions = 0;
for (const testCase of outputCases) {
  for (const assertion of testCase.assertions) {
    assertions += 1;
    const passes = (output) =>
      (assertion.required || []).every((value) => output.includes(value)) &&
      (assertion.forbidden || []).every((value) => !output.includes(value));
    if (passes(testCase.baseline_output)) baselinePasses += 1;
    if (passes(testCase.with_skill_output)) withSkillPasses += 1;
  }
}

assert.equal(assertions, 11);
assert.equal(baselinePasses, 0);
assert.equal(withSkillPasses, 11);

console.log("PASS: governed Skill metadata, trigger boundary, and 11 output assertions.");
