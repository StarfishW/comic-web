const APP_NAME = 'Comic Web'
const DEFAULT_TITLE = APP_NAME

export function setDocumentTitle(...parts) {
  const title = parts.filter(Boolean).join(' · ')
  document.title = title ? `${title} | ${APP_NAME}` : DEFAULT_TITLE
}

export function resetDocumentTitle() {
  document.title = DEFAULT_TITLE
}
