# wechat-article-search Changelog

## 1.0.3 — 2026-08-24

- Detect the Sogou `/antispider` rate-limit redirect and fail loudly instead of reporting it as zero search results.
- Exit non-zero when the first page is blocked; keep already-collected articles when a later page is blocked.
- Cover the detection with an offline regression test.

## 1.0.2 — 2026-07-17

- Publish and install exclusively through `zjp1997720/zhijian-skills`.

## 1.0.1 — 2026-07-17

- Add a brand-aligned light README hero and clearer bilingual discovery guidance.
- Correct the documented standalone mirror layout without changing search behavior.

## 1.0.0 — 2026-07-16

- Establish the first independently versioned governance baseline.
- Preserve the active local Node package and lockfile.
