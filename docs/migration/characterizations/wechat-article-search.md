# wechat-article-search characterization

- **Trigger contract:** Search WeChat public-account articles by keyword and return title, summary, date, account, and URL.
- **Workflow invariant:** Node runtime with the committed package lock; search behavior remains in `scripts/search_wechat.js`.
- **Output invariant:** Structured article results and explicit failure when dependencies or upstream search are unavailable.
- **Capability:** Network access and subprocess execution of Node; no credential requirement.
- **Resource graph:** `package.json`, `package-lock.json`, `scripts/search_wechat.js`.

