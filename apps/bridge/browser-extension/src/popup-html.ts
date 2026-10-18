import {
  BROWSER_EXTENSION_POPUP_ENTRYPOINT_FILE
} from "./entrypoints.js";

export const BROWSER_EXTENSION_POPUP_ROOT_ID = "nsealr-popup-root";
export const BROWSER_EXTENSION_POPUP_STATUS_ID = "nsealr-popup-status";
export const BROWSER_EXTENSION_POPUP_LIST_ID = "nsealr-popup-list";
export const BROWSER_EXTENSION_POPUP_REFRESH_ID = "nsealr-popup-refresh";

export function browserExtensionPopupHtml(): string {
  return `<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>nSealr</title>
  <style>
    :root {
      color-scheme: light;
      --nsealr-ink: #111315;
      --nsealr-muted: #667085;
      --nsealr-rule: #d7dde5;
      --nsealr-panel: #f7f9fb;
      --nsealr-accent: #0f766e;
      --nsealr-danger: #b42318;
      --nsealr-bg: #ffffff;
    }
    * {
      box-sizing: border-box;
    }
    body {
      margin: 0;
      width: 320px;
      min-height: 220px;
      font: 13px/1.4 ui-sans-serif, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      color: var(--nsealr-ink);
      background: var(--nsealr-bg);
    }
    .nsealr-popup {
      display: grid;
      grid-template-rows: auto minmax(112px, 1fr) auto;
      gap: 10px;
      min-height: 220px;
      padding: 12px;
    }
    .nsealr-popup__top {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 8px;
      padding-bottom: 8px;
      border-bottom: 1px solid var(--nsealr-rule);
    }
    .nsealr-popup__brand {
      font-weight: 700;
      letter-spacing: 0;
    }
    .nsealr-popup__status {
      max-width: 170px;
      overflow: hidden;
      color: var(--nsealr-muted);
      font-size: 12px;
      text-overflow: ellipsis;
      white-space: nowrap;
    }
    .nsealr-popup__list {
      display: grid;
      align-content: start;
      gap: 8px;
      min-width: 0;
    }
    .nsealr-popup__empty,
    .nsealr-popup__request,
    .nsealr-popup__permission {
      border: 1px solid var(--nsealr-rule);
      border-radius: 8px;
      background: var(--nsealr-panel);
    }
    .nsealr-popup__empty {
      padding: 18px 12px;
      color: var(--nsealr-muted);
      text-align: center;
    }
    .nsealr-popup__request,
    .nsealr-popup__permission {
      display: grid;
      gap: 8px;
      padding: 10px;
    }
    .nsealr-popup__request-head {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 8px;
    }
    .nsealr-popup__method {
      min-width: 0;
      overflow-wrap: anywhere;
      font-weight: 650;
    }
    .nsealr-popup__badge {
      flex: 0 0 auto;
      border: 1px solid #99d6cf;
      border-radius: 999px;
      padding: 2px 7px;
      color: var(--nsealr-accent);
      font-size: 11px;
      line-height: 1.25;
      background: #e7f6f3;
    }
    .nsealr-popup__meta {
      display: grid;
      gap: 2px;
      min-width: 0;
      color: var(--nsealr-muted);
      font-size: 12px;
    }
    .nsealr-popup__meta-line {
      overflow-wrap: anywhere;
    }
    .nsealr-popup__chips {
      display: flex;
      flex-wrap: wrap;
      gap: 4px;
    }
    .nsealr-popup__digest {
      border: 1px solid #e3e8ef;
      border-radius: 6px;
      padding: 5px 6px;
      overflow-wrap: anywhere;
      color: #344054;
      background: #ffffff;
      font: 11px/1.35 ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
    }
    .nsealr-popup__permission-methods {
      display: grid;
      gap: 6px;
      min-width: 0;
    }
    .nsealr-popup__permission-method {
      display: grid;
      gap: 2px;
      min-width: 0;
      padding-top: 6px;
      border-top: 1px solid #e3e8ef;
    }
    .nsealr-popup__permission-chips {
      display: flex;
      flex-wrap: wrap;
      gap: 4px;
    }
    .nsealr-popup__chip {
      border: 1px solid #c7d7fe;
      border-radius: 999px;
      padding: 2px 7px;
      color: #1849a9;
      background: #eef4ff;
      font-size: 11px;
      line-height: 1.25;
    }
    .nsealr-popup__actions {
      display: flex;
      gap: 6px;
      justify-content: flex-end;
    }
    .nsealr-popup__button {
      min-height: 30px;
      border: 1px solid var(--nsealr-rule);
      border-radius: 7px;
      padding: 5px 10px;
      color: var(--nsealr-ink);
      background: var(--nsealr-bg);
      font: inherit;
      cursor: pointer;
    }
    .nsealr-popup__button:hover {
      border-color: #aeb8c5;
    }
    .nsealr-popup__button:disabled {
      color: #9aa4b2;
      cursor: default;
    }
    .nsealr-popup__button--danger {
      color: var(--nsealr-danger);
    }
    .nsealr-popup__button--primary {
      border-color: #0f766e;
      color: #ffffff;
      background: #0f766e;
    }
    .nsealr-popup__button--primary:hover {
      border-color: #115e59;
      background: #115e59;
    }
    .nsealr-popup__button--primary:disabled {
      border-color: #99d6cf;
      color: #eef4f3;
      background: #99d6cf;
    }
    .nsealr-popup__footer {
      display: flex;
      justify-content: flex-end;
      padding-top: 2px;
    }
  </style>
</head>
<body>
  <main id="${BROWSER_EXTENSION_POPUP_ROOT_ID}" class="nsealr-popup">
    <header class="nsealr-popup__top">
      <span class="nsealr-popup__brand">nSealr</span>
      <span id="${BROWSER_EXTENSION_POPUP_STATUS_ID}" class="nsealr-popup__status">Ready</span>
    </header>
    <section id="${BROWSER_EXTENSION_POPUP_LIST_ID}" class="nsealr-popup__list" aria-live="polite"></section>
    <footer class="nsealr-popup__footer">
      <button id="${BROWSER_EXTENSION_POPUP_REFRESH_ID}" class="nsealr-popup__button" type="button">Refresh</button>
    </footer>
  </main>
  <script type="module" src="${BROWSER_EXTENSION_POPUP_ENTRYPOINT_FILE}"></script>
</body>
</html>
`;
}
