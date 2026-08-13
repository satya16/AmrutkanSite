import { App as AntApp } from 'antd'
import { formatBytes } from './bytes'

function triggerDownload(href: string, filename: string) {
  const a = document.createElement('a')
  a.href = href
  a.download = filename
  document.body.appendChild(a)
  a.click()
  a.remove()
}

export function useDownloadConfirm() {
  const { modal } = AntApp.useApp()

  return (label: string, sizeBytes: number | null | undefined, href: string, filename: string) => {
    modal.confirm({
      title: 'डाउनलोड करायचे?',
      content: `${label} — आकार: ${sizeBytes ? formatBytes(sizeBytes) : 'आकार अज्ञात'}`,
      okText: 'डाउनलोड करा',
      cancelText: 'रद्द करा',
      onOk: () => triggerDownload(href, filename),
    })
  }
}
