import type { Metadata } from 'next'
import './globals.css'
import './composer.css'

export const metadata: Metadata = {
  title: 'Sovereign Compliance AI',
  description: 'Browser extension trợ lý tuân thủ',
}

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return <html lang="vi"><body>{children}</body></html>
}
