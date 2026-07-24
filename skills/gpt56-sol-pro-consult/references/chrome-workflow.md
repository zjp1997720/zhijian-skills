# Codex Chrome Workflow

Use this as the default execution path for every GPT 5.6 Sol Pro consultation.

## 1. Connect to Chrome

1. Read the installed `chrome:control-chrome` Skill completely.
2. Discover the `node_repl js` tool when it is not already callable.
3. Initialize the browser runtime from the Chrome plugin's own absolute `scripts/browser-client.mjs` path.
4. Select the Chrome extension binding with `agent.browsers.get("extension")` and read its complete documentation before interacting.
5. Reuse an existing ChatGPT tab when available; otherwise create one and navigate directly to `https://chatgpt.com/`.

Do not inspect cookies, local storage, passwords, profiles, or session databases. Keep browser work in the background unless the user asks to see it.

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

## 3. Fill the context packet

Run `scripts/check_packet_safety.py` locally before touching the composer.

Locate the ChatGPT composer from the current DOM snapshot. Fill the complete packet and verify a distinctive prefix plus the unique sentinel are present. Do not send a local path as evidence.

## 4. Upload required files

Read the Chrome plugin's file-upload documentation before uploading.

Use the real file chooser:

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

Verify every required filename is visible in the composer. If multiple uploads are unstable, combine text sources with `scripts/build_attachment_bundle.py` and upload one Markdown file.

## 5. Send and wait

The user's consultation request authorizes sending the prepared packet and selected artifacts to ChatGPT. It does not authorize unrelated uploads or messages.

Verify the composer text, sentinel, model, and attachment names immediately before clicking Send. Send once.

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
- completion state
- extracted answer

Finalize browser tabs after extraction. Keep a tab only when the user needs to continue from it.
