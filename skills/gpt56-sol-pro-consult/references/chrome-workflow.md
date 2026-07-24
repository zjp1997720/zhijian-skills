# Codex Chrome Workflow

Use this as the default execution path for every GPT 5.6 Sol Pro consultation.

## Contents

- Connect to Chrome
- Confirm authentication and model
- Upload required files
- Insert and verify the context packet
- Send once and recover safely
- Extract and verify

## 1. Connect to Chrome

1. Read the installed `chrome:control-chrome` Skill completely.
2. Discover the `node_repl js` tool when it is not already callable.
3. Initialize the browser runtime from the Chrome plugin's own absolute `scripts/browser-client.mjs` path.
4. Select the Chrome extension binding with `agent.browsers.get("extension")` and read its complete documentation before interacting.
5. Reuse an existing ChatGPT tab when available; otherwise create one and navigate directly to `https://chatgpt.com/`.

Do not inspect cookies, local storage, passwords, profiles, or session databases. Keep browser work in the background unless the user asks to see it.

Treat a browser-kernel reset as loss of every prior JavaScript binding and unresolved promise. Reinitialize the browser runtime and reacquire `agent`, `browser`, `tab`, and fresh locators. Never carry an unresolved Playwright promise into a later `node_repl js` invocation.

## 2. Confirm authentication and model

Take one fresh DOM snapshot. Confirm the account is signed in and the composer is available.

Open the model picker using locator ground truth from the snapshot. Before every click:

1. Build a stable locator from the latest snapshot.
2. Call `count()` unless uniqueness is self-evident.
3. Click only when exactly one element matches.
4. Take a targeted observation after the UI changes.

Confirm GPT 5.6 Sol Pro using either a current GPT 5.6-specific Pro test ID or both of these visible signals:

- model-family row: `GPT-5.6 Sol`
- exact `Pro` menu radio: `aria-checked=true`

If `Pro` is not checked, click the exact `Pro` radio once and verify both signals again. `Extra High` is base GPT 5.6 Sol, not Pro.

## 3. Upload required files

Read the Chrome plugin's file-upload documentation before uploading.

Use the real file chooser. Run the entire block—including promise creation, both clicks, `await`, and `setFiles`—inside one `node_repl js` invocation:

```js
const chooserPromise = tab.playwright.waitForEvent("filechooser", { timeoutMs: 15000 });
const addButton = tab.playwright.getByTestId("composer-plus-btn");
if (await addButton.count() !== 1) throw new Error("Expected one composer add-files button");
await addButton.click();

// Build this locator from the fresh menu snapshot; localized text may differ.
const fileMenuItem = tab.playwright.getByText("添加照片和文件", { exact: true });
if (await fileMenuItem.count() !== 1) throw new Error("Expected one add-files menu item");
await fileMenuItem.click();

const chooser = await chooserPromise;
await chooser.setFiles(["/path/to/file.md"]);
```

Do not split `waitForEvent("filechooser")` and `chooser.setFiles(...)` across browser calls. A pending chooser promise does not survive a reset or a later invocation.

Verify every required filename is visible in the composer. If multiple uploads are unstable, combine text sources with `scripts/build_attachment_bundle.py` and upload one Markdown file.

## 4. Insert and verify the context packet

Run `scripts/check_packet_safety.py` locally before touching the composer. After all uploads finish, take a fresh DOM snapshot and reacquire the composer because attachment UI changes can invalidate earlier locators.

1. Use the Chrome plugin's supported text-entry method once to insert the complete packet.
2. Read the composer's `innerText()` from a fresh locator. Require both a distinctive packet prefix and the unique `GPT56_SOL_PRO_RESULT_...` sentinel.
3. If the rendered text is empty, inspect a fresh snapshot. When the uploaded packet preview exposes exactly one associated action named `在文本字段中显示` or `Show in text field`, click that action once.
4. Reacquire the composer and verify its `innerText()` again. Stop when the prefix or sentinel is still missing.

Do not loop through `fill`, `type`, and clipboard paste after the first verified failure. Do not treat an attachment card or filename as composer text. Never click Send with an empty or unverified packet.

## 5. Send once and recover safely

The user's consultation request authorizes sending the prepared packet and selected artifacts to ChatGPT. It does not authorize unrelated uploads or messages.

Track `dispatch_state` locally:

- `NOT_SENT`: Send has definitely not been clicked.
- `SENT`: the click completed and a fresh observation shows the user turn, an emptied composer, or active generation.
- `UNKNOWN`: the browser resets, disconnects, or times out during or after the click before submission evidence is observed.

Verify the composer prefix, sentinel, model, and attachment names immediately before clicking Send. Send once. Set `SENT` only after observing submission evidence; use `UNKNOWN` for every ambiguous click outcome.

When Chrome resets in `NOT_SENT`, reconnect, re-confirm the model, and rebuild the draft in an existing or fresh ChatGPT tab. When the state is `SENT` or `UNKNOWN`, recover the existing conversation from fresh tab inventory and its conversation URL, then wait or extract. Never create a fresh consultation or click Send again in `SENT` or `UNKNOWN`. If the original conversation cannot be identified uniquely, mark the consultation incomplete instead of risking a duplicate.

GPT 5.6 Sol Pro can take 10–20 minutes. Poll the same conversation with targeted DOM snapshots. Treat these as active-generation signals:

- `data-testid=stop-button`
- visible “正在思考” or equivalent generating status
- an incomplete assistant preamble while the stop control remains

Do not stop, retry, refresh, or send “continue” while generation remains active.

## 6. Extract and verify

After generation stops, identify the latest assistant turn from a fresh snapshot. Read that turn only; do not treat the user's echoed sentinel as success.

Normalize escaped underscores and verify `GPT56_SOL_PRO_RESULT_...` appears inside the assistant turn. If it is absent, re-read the complete latest assistant turn once. Mark the consultation incomplete when the final answer still lacks the sentinel or appears truncated.

Record:

- model selection evidence
- Chrome browser path
- packet sentinel and timestamp
- uploaded filenames
- dispatch state and conversation URL when available
- completion state
- extracted answer

Finalize browser tabs after extraction. Keep a tab only when the user needs to continue from it.
