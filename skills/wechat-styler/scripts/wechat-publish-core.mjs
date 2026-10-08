import { WECHAT_IMAGE_HOSTS } from './wechat-image-hosts.mjs';

const editorLookupSource = `
  const titleEditor = document.querySelector(".title-editor__input .ProseMirror");
  const ueditor = document.querySelector("#ueditor_0 [contenteditable=true]");
  const proseEditors = [...document.querySelectorAll(".ProseMirror")]
    .filter((element) => element !== titleEditor && !element.closest(".title-editor__input"));
  const semanticBody = document.querySelector(".rich_media_content .ProseMirror")
    || document.querySelector("#js_editor .ProseMirror");
  const visibleBodies = proseEditors
    .filter((element) => element.offsetParent !== null)
    .sort((left, right) => right.getBoundingClientRect().height - left.getBoundingClientRect().height);
  const bodyEditor = ueditor || semanticBody || visibleBodies[0] || proseEditors[0] || null;
`;

function decodeHtml(value) {
  return value
    .replaceAll('&amp;', '&')
    .replaceAll('&quot;', '"')
    .replaceAll('&#39;', "'")
    .replaceAll('&lt;', '<')
    .replaceAll('&gt;', '>');
}

function extractBalancedSection(html, startIndex) {
  const tagPattern = /<\/?section\b[^>]*>/gi;
  tagPattern.lastIndex = startIndex;
  let depth = 0;
  let match;
  while ((match = tagPattern.exec(html)) !== null) {
    depth += match[0].startsWith('</') ? -1 : 1;
    if (depth === 0) return html.slice(startIndex, tagPattern.lastIndex);
  }
  return html.slice(startIndex);
}

function findMetaContent(html, name) {
  const tags = html.match(/<meta\b[^>]*>/gi) || [];
  for (const tag of tags) {
    const nameMatch = tag.match(/\bname=["']([^"']+)["']/i);
    const contentMatch = tag.match(/\bcontent=["']([^"']*)["']/i);
    if (nameMatch?.[1]?.toLowerCase() === name && contentMatch?.[1] !== undefined) {
      return decodeHtml(contentMatch[1]);
    }
  }
  return '';
}

function extractImageUrls(content) {
  return [...content.matchAll(/<img\b[^>]*\bsrc=["']([^"']+)["'][^>]*>/gi)]
    .map((match) => decodeHtml(match[1]));
}

export function hardenCodeBlockLineBreaks(html) {
  return String(html).replace(
    /(<pre\b[^>]*>\s*<code\b[^>]*>)([\s\S]*?)(<\/code>\s*<\/pre>)/gi,
    (_, opening, code, closing) => `${opening}${code.replace(/\r\n?|\n/g, '<br>')}${closing}`,
  );
}

function extractCodeBlockMetrics(content) {
  const blocks = content.match(/<pre\b[^>]*>[\s\S]*?<\/pre>/gi) || [];
  return {
    codeBlockCount: blocks.length,
    codeBlockBreakCount: blocks.reduce(
      (total, block) => total + (block.match(/<br\b[^>]*>/gi) || []).length,
      0,
    ),
  };
}

export function extractArticleDocument(html) {
  const titleMatch = html.match(/<title>([\s\S]*?)<\/title>/i);
  const rawTitle = titleMatch?.[1] ? decodeHtml(titleMatch[1].trim()) : '';
  const title = rawTitle === 'WeChat Article' ? '' : rawTitle;
  const summary = findMetaContent(html, 'description');
  const contractMatch = /<section\b[^>]*data-wechat-root=["']article["'][^>]*>/i.exec(html);
  const bodyMatch = /<body\b[^>]*>([\s\S]*?)<\/body>/i.exec(html);
  const body = bodyMatch?.[1] || html;
  let content;
  if (contractMatch?.index !== undefined) {
    content = extractBalancedSection(html, contractMatch.index);
  } else {
    const legacyMatch = /<section\b[^>]*style=["'][^"']*background-color:/i.exec(body);
    content = legacyMatch?.index !== undefined
      ? extractBalancedSection(body, legacyMatch.index)
      : body.trim();
  }
  content = hardenCodeBlockLineBreaks(content);
  const imageUrls = extractImageUrls(content);
  const nonHttpImageUrls = imageUrls.filter((source) => !/^https?:\/\//i.test(source));
  const codeBlockMetrics = extractCodeBlockMetrics(content);
  return {
    content,
    title,
    summary,
    imageUrls,
    nonHttpImageUrls,
    svgCount: (content.match(/<svg\b/gi) || []).length,
    animateCount: (content.match(/<animate(?:Transform)?\b/gi) || []).length,
    svgImageCount: (content.match(/<image\b/gi) || []).length,
    xiaolanNativeFrameCount: (content.match(/data-xiaolan-render=["']native-svg-pixels["']/gi) || []).length,
    ...codeBlockMetrics,
  };
}

export function buildProbeScript() {
  return `(() => {
${editorLookupSource}
  return JSON.stringify({
    readyState: document.readyState,
    hasTitleEditor: Boolean(titleEditor),
    hasBodyEditor: Boolean(bodyEditor),
    editorCount: document.querySelectorAll(".ProseMirror").length,
    bodyHeight: bodyEditor ? bodyEditor.getBoundingClientRect().height : 0
  });
})()`;
}

export function buildInjectScript(content) {
  const encoded = Buffer.from(hardenCodeBlockLineBreaks(content), 'utf8').toString('base64');
  return `(() => {
${editorLookupSource}
  if (!bodyEditor) return JSON.stringify({ ok: false, reason: "body editor not found" });
  const binary = atob("${encoded}");
  const bytes = Uint8Array.from(binary, (char) => char.charCodeAt(0));
  const html = new TextDecoder("utf-8").decode(bytes);
  window.getSelection()?.removeAllRanges();
  bodyEditor.innerHTML = html;
  for (const paragraph of [...bodyEditor.querySelectorAll("p")]) {
    const text = paragraph.textContent.trim();
    const empty = text === "" || text === "\\u00a0" || paragraph.innerHTML === "<br>";
    if (empty && paragraph.querySelectorAll("svg,img").length === 0) paragraph.remove();
  }
  bodyEditor.dispatchEvent(new InputEvent("input", { bubbles: true, inputType: "insertText", data: null }));
  bodyEditor.dispatchEvent(new Event("change", { bubbles: true }));
  window.getSelection()?.removeAllRanges();
  return JSON.stringify({
    ok: true,
    svgCount: bodyEditor.querySelectorAll("svg").length,
    animateCount: bodyEditor.querySelectorAll("animate,animateTransform").length,
    imageCount: [...bodyEditor.querySelectorAll("img")].filter((image) => !image.classList.contains("ProseMirror-separator")).length,
    codeBlockCount: bodyEditor.querySelectorAll("pre").length,
    codeBlockBreakCount: [...bodyEditor.querySelectorAll("pre")]
      .reduce((total, block) => total + block.querySelectorAll("br").length, 0),
    textLength: (bodyEditor.innerText || bodyEditor.textContent || "").trim().length
  });
})()`;
}

// 长文章的单参数体积会超过系统 argv 上限（E2BIG）。分段把 base64 推进页面缓冲区，
// 最后一次性赋值 innerHTML，保持"一次写入、不做后续 DOM 操作"的编辑器约束。
export function buildInjectScripts(content, chunkSize = 48000) {
  const encoded = Buffer.from(hardenCodeBlockLineBreaks(content), 'utf8').toString('base64');
  const chunks = [];
  for (let index = 0; index < encoded.length; index += chunkSize) {
    chunks.push(encoded.slice(index, index + chunkSize));
  }

  const scripts = [`(() => {
  window.__wechatStylerChunks = [];
  return JSON.stringify({ ok: true, phase: "reset", chunks: ${chunks.length} });
})()`];

  chunks.forEach((chunk, index) => {
    scripts.push(`(() => {
  if (!Array.isArray(window.__wechatStylerChunks)) window.__wechatStylerChunks = [];
  window.__wechatStylerChunks.push("${chunk}");
  return JSON.stringify({ ok: true, phase: "chunk", index: ${index} });
})()`);
  });

  scripts.push(`(() => {
${editorLookupSource}
  const chunks = Array.isArray(window.__wechatStylerChunks) ? window.__wechatStylerChunks : [];
  window.__wechatStylerChunks = [];
  if (!bodyEditor) return JSON.stringify({ ok: false, reason: "body editor not found" });
  const binary = atob(chunks.join(""));
  const bytes = Uint8Array.from(binary, (char) => char.charCodeAt(0));
  const html = new TextDecoder("utf-8").decode(bytes);
  window.getSelection()?.removeAllRanges();
  bodyEditor.innerHTML = html;
  for (const paragraph of [...bodyEditor.querySelectorAll("p")]) {
    const text = paragraph.textContent.trim();
    const empty = text === "" || text === "\\u00a0" || paragraph.innerHTML === "<br>";
    if (empty && paragraph.querySelectorAll("svg,img").length === 0) paragraph.remove();
  }
  bodyEditor.dispatchEvent(new InputEvent("input", { bubbles: true, inputType: "insertText", data: null }));
  bodyEditor.dispatchEvent(new Event("change", { bubbles: true }));
  window.getSelection()?.removeAllRanges();
  return JSON.stringify({
    ok: true,
    svgCount: bodyEditor.querySelectorAll("svg").length,
    animateCount: bodyEditor.querySelectorAll("animate,animateTransform").length,
    imageCount: [...bodyEditor.querySelectorAll("img")].filter((image) => !image.classList.contains("ProseMirror-separator")).length,
    codeBlockCount: bodyEditor.querySelectorAll("pre").length,
    codeBlockBreakCount: [...bodyEditor.querySelectorAll("pre")]
      .reduce((total, block) => total + block.querySelectorAll("br").length, 0),
    textLength: (bodyEditor.innerText || bodyEditor.textContent || "").trim().length,
    chunkCount: chunks.length
  });
})()`);

  return scripts;
}

export function buildMetadataScript(metadata) {
  const title = metadata.title ?? null;
  const summary = metadata.summary ?? null;
  const author = metadata.author ?? null;
  return `(() => {
${editorLookupSource}
  const setValue = (element, value) => {
    if (!element || value === null) return;
    const prototype = element instanceof HTMLTextAreaElement ? HTMLTextAreaElement.prototype : HTMLInputElement.prototype;
    const setter = Object.getOwnPropertyDescriptor(prototype, "value")?.set;
    if (setter) setter.call(element, value); else element.value = value;
    element.dispatchEvent(new Event("input", { bubbles: true }));
    element.dispatchEvent(new Event("change", { bubbles: true }));
    element.dispatchEvent(new Event("blur", { bubbles: true }));
  };
  window.getSelection()?.removeAllRanges();
  const titleValue = ${JSON.stringify(title)};
  if (titleEditor && titleValue !== null) {
    titleEditor.replaceChildren(document.createTextNode(titleValue));
    titleEditor.dispatchEvent(new InputEvent("input", { bubbles: true, inputType: "insertText", data: titleValue }));
    titleEditor.dispatchEvent(new Event("change", { bubbles: true }));
  }
  setValue(document.querySelector("#title"), titleValue);
  setValue(document.querySelector("#js_description"), ${JSON.stringify(summary)});
  setValue(document.querySelector("#author"), ${JSON.stringify(author)});
  window.getSelection()?.removeAllRanges();
  return JSON.stringify({
    title: document.querySelector("#title")?.value || titleEditor?.innerText || "",
    visibleTitle: titleEditor?.innerText || "",
    summary: document.querySelector("#js_description")?.value || "",
    author: document.querySelector("#author")?.value || ""
  });
})()`;
}

export function buildVerifyScript(expectedTitle = '') {
  return `(() => {
${editorLookupSource}
  if (!bodyEditor) return JSON.stringify({ ok: false, reason: "body editor not found" });
  const trustedImageHosts = new Set(${JSON.stringify(WECHAT_IMAGE_HOSTS)});
  const isWeChatHostedImage = (source) => {
    try { return trustedImageHosts.has(new URL(source, window.location.href).hostname.toLowerCase()); }
    catch { return false; }
  };
  const images = [...bodyEditor.querySelectorAll("img")]
    .filter((image) => !image.classList.contains("ProseMirror-separator"));
  const pendingImages = images
    .map((image) => image.currentSrc || image.src || "")
    .filter((source) => /^https?:/i.test(source) && !isWeChatHostedImage(source));
  const failedUrls = [...document.querySelectorAll(".js_catchremoteimageerror")]
    .map((element) => element.getAttribute("data-cacheurl") || "")
    .filter(Boolean);
  const coverArea = document.querySelector("#js_cover_area") || document.querySelector(".js_cover_btn_area");
  const coverSources = coverArea ? [...coverArea.querySelectorAll("img,[style*='background']")]
    .flatMap((element) => {
      const values = [element.currentSrc || element.src || "", element.style?.backgroundImage || ""];
      return values.flatMap((value) => value.match(/(?:https?:|blob:|data:image)[^\"')]+/g) || []);
    }) : [];
  const history = [...document.querySelectorAll("#history_pop tr")]
    .slice(1, 4)
    .map((row) => (row.innerText || "").trim())
    .filter(Boolean);
  const text = (bodyEditor.innerText || bodyEditor.textContent || "").trim();
  const svgImageCount = bodyEditor.querySelectorAll("svg image").length;
  const xiaolanNativeFrameCount = bodyEditor.querySelectorAll('[data-xiaolan-render="native-svg-pixels"]').length;
  const svgPathCount = bodyEditor.querySelectorAll("svg path").length;
  const codeBlocks = [...bodyEditor.querySelectorAll("pre")];
  const codeBlockBreakCount = codeBlocks.reduce(
    (total, block) => total + block.querySelectorAll("br").length,
    0,
  );
  const expectedTitle = ${JSON.stringify(expectedTitle)};
  const url = window.location.href;
  const saved = (document.body?.innerText || "").includes("已保存");
  return JSON.stringify({
    ok: true,
    title: document.querySelector("#title")?.value || titleEditor?.innerText || "",
    visibleTitle: titleEditor?.innerText || "",
    summary: document.querySelector("#js_description")?.value || "",
    svgCount: bodyEditor.querySelectorAll("svg").length,
    animateCount: bodyEditor.querySelectorAll("animate,animateTransform").length,
    svgImageCount,
    xiaolanNativeFrameCount,
    svgPathCount,
    codeBlockCount: codeBlocks.length,
    codeBlockBreakCount,
    imageCount: images.length,
    failedUrls,
    pendingImages,
    textLength: text.length,
    firstText: text.slice(0, 80),
    lastText: text.slice(-80),
    titleOccurrencesInBody: expectedTitle ? text.split(expectedTitle).length - 1 : 0,
    cover: { hasImage: coverSources.length > 0, sources: coverSources },
    saved,
    history,
    appmsgid: new URL(url).searchParams.get("appmsgid") || "",
    saveEvidence: {
      appmsgid: /[?&]appmsgid=\\d+/.test(url),
      savedBanner: saved,
      history: history.length > 0
    },
    url
  });
})()`;
}

export function parseOpencliJson(output) {
  const lines = output.trim().split(/\r?\n/).reverse();
  for (const line of lines) {
    const trimmed = line.trim();
    if (!trimmed.startsWith('{') || !trimmed.endsWith('}')) continue;
    try {
      return JSON.parse(trimmed);
    } catch {
      continue;
    }
  }
  throw new Error(`opencli did not return JSON: ${output.slice(0, 300)}`);
}

// Omitted summaries preserve the editor value; an explicit empty string clears it.
export function buildMetadataVerification(state, metadata = {}) {
  const summaryChecked = metadata.summary !== undefined;
  return {
    summaryChecked,
    expectedSummary: summaryChecked ? metadata.summary : null,
    summaryMatches: summaryChecked ? state?.summary === metadata.summary : null,
  };
}
