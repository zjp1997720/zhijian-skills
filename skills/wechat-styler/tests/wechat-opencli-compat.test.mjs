import assert from 'node:assert/strict';
import test from 'node:test';
import vm from 'node:vm';
import { prepareSession, OpencliError, buildCoverUploadSelectionScript, buildAdvanceCoverScript } from '../scripts/wechat-opencli.mjs';

const options = { profile: 'test', session: 'compat', reuseCurrent: true };
const editor = { url: 'https://mp.weixin.qq.com/cgi-bin/appmsg?t=media/appmsg_edit_v2&token=test' };

test('reuses the bound editor via DOM without requesting a formatted state or rebinding', () => {
  const commands = [];
  const result = prepareSession(options, (_p, _s, args) => {
    commands.push(args[0]);
    assert.equal(args[1], 'JSON.stringify({url: window.location.href})');
    return JSON.stringify(editor);
  });
  assert.deepEqual(result, editor);
  assert.deepEqual(commands, ['eval']);
});

test('binds once only when the session explicitly has no bound tab, then rechecks', () => {
  const commands = [];
  const result = prepareSession(options, (_p, _s, args) => {
    commands.push(args[0]);
    if (commands.length === 1) throw new OpencliError('eval failed', 'No bound tab');
    return JSON.stringify(editor);
  });
  assert.deepEqual(result, editor);
  assert.deepEqual(commands, ['eval', 'bind', 'eval']);
});

test('does not switch away from a bound non-editor, lookalike domain, or permission denial', () => {
  for (const response of [
    { url: 'https://mp.weixin.qq.com/cgi-bin/home' },
    { url: 'https://mp.weixin.qq.com.evil.test/cgi-bin/appmsg?t=media/appmsg_edit' },
    new OpencliError('permission denied', 'session not bound'),
    new OpencliError('eval failed', 'connection timeout'),
  ]) {
    const commands = [];
    assert.throws(() => prepareSession(options, (_p, _s, args) => {
      commands.push(args[0]);
      if (response instanceof Error) throw response;
      return JSON.stringify(response);
    }));
    assert.deepEqual(commands, ['eval']);
  }
});

function button(label, disabled = false) {
  return { textContent: label, disabled, clicks: 0, getClientRects: () => [1],
    getAttribute: () => null, click() { this.clicks++; } };
}
function dialog(text, buttons, { visible = true, titles = [] } = {}) {
  return { innerText: text, getClientRects: () => visible ? [1] : [],
    querySelector: (selector) => selector.includes('img-picker') && titles.length ? titles[0] : null,
    querySelectorAll: (selector) => selector === 'button,a' ? buttons : titles };
}
function execute(script, dialogs, outside = []) {
  return JSON.parse(vm.runInNewContext(script, { document: {
    querySelectorAll: (selector) => selector === 'button,a' ? outside : dialogs,
  } }));
}

test('direct crop dialog advances without waiting for or clicking a library filename', () => {
  const confirm = button('确认');
  const crop = dialog('编辑封面 2.35:1 (消息列表) 1:1 (转发卡片和公众号主页)', [confirm]);
  const selection = execute(buildCoverUploadSelectionScript('cover.jpg'), [crop]);
  assert.equal(selection.stage, 'crop');
  assert.equal(selection.ok, true);
  assert.equal(confirm.clicks, 0);
  const unrelated = button('确认');
  assert.equal(execute(buildAdvanceCoverScript(), [crop], [unrelated]).clicked, '确认');
  assert.equal(confirm.clicks, 1);
  assert.equal(unrelated.clicks, 0);
});

test('library path still matches the visible filename and selects it', () => {
  const item = button('cover.jpg');
  const title = { textContent: 'cover.jpg', getClientRects: () => [1], closest: () => item };
  const library = dialog('图片库', [], { titles: [title] });
  const selection = execute(buildCoverUploadSelectionScript('cover.jpg'), [library]);
  assert.equal(selection.stage, 'library');
  assert.equal(item.clicks, 1);
});

test('hidden crop dialogs and disabled confirm controls do not advance the flow', () => {
  const hiddenConfirm = button('确认');
  const disabledConfirm = button('确认', true);
  const dialogs = [dialog('编辑封面 2.35:1', [hiddenConfirm], { visible: false }),
    dialog('编辑封面 2.35:1', [disabledConfirm])];
  assert.equal(execute(buildCoverUploadSelectionScript('cover.jpg'), dialogs).ok, false);
  assert.equal(execute(buildAdvanceCoverScript(), dialogs).clicked, '');
  assert.equal(hiddenConfirm.clicks + disabledConfirm.clicks, 0);
});

test('unrelated page confirmations and stale filenames are not clicked', () => {
  const unrelated = button('确认');
  assert.equal(execute(buildAdvanceCoverScript(), [], [unrelated]).clicked, '');
  const item = button('old-cover.jpg');
  const title = { textContent: 'old-cover.jpg', getClientRects: () => [1], closest: () => item };
  assert.equal(execute(buildCoverUploadSelectionScript('cover.jpg'), [dialog('图片库', [], { titles: [title] })]).ok, false);
  assert.equal(item.clicks + unrelated.clicks, 0);
});
