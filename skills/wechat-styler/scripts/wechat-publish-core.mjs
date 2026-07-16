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
  const imageUrls = extractImageUrls(content);
  return {
    content,
    title,
    summary,
    imageUrls,
    svgCount: (content.match(/<svg\b/gi) || []).length,
    animateCount: (content.match(/<animate(?:Transform)?\b/gi) || []).length,
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
  const encoded = Buffer.from(content, 'utf8').toString('base64');
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
    textLength: (bodyEditor.innerText || bodyEditor.textContent || "").trim().length
  });
})()`;
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
  const images = [...bodyEditor.querySelectorAll("img")]
    .filter((image) => !image.classList.contains("ProseMirror-separator"));
  const pendingImages = images
    .map((image) => image.currentSrc || image.src || "")
    .filter((source) => /^https?:/i.test(source) && !/(?:mmbiz|qpic)\\.(?:cn|com)/i.test(source));
  const failedUrls = [...document.querySelectorAll(".js_catchremoteimageerror")]
    .map((element) => element.getAttribute("data-cacheurl") || "")
    .filter(Boolean);
  const text = (bodyEditor.innerText || bodyEditor.textContent || "").trim();
  const expectedTitle = ${JSON.stringify(expectedTitle)};
  return JSON.stringify({
    ok: true,
    title: document.querySelector("#title")?.value || titleEditor?.innerText || "",
    visibleTitle: titleEditor?.innerText || "",
    summary: document.querySelector("#js_description")?.value || "",
    svgCount: bodyEditor.querySelectorAll("svg").length,
    animateCount: bodyEditor.querySelectorAll("animate,animateTransform").length,
    imageCount: images.length,
    failedUrls,
    pendingImages,
    textLength: text.length,
    firstText: text.slice(0, 80),
    lastText: text.slice(-80),
    titleOccurrencesInBody: expectedTitle ? text.split(expectedTitle).length - 1 : 0,
    saved: (document.body?.innerText || "").includes("已保存"),
    url: window.location.href
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
