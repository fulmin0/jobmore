import type { Metadata } from 'next'
import { Newsreader, DM_Sans, Caveat, JetBrains_Mono } from 'next/font/google'
import './globals.css'

const newsreader = Newsreader({
  subsets: ['latin'],
  weight: ['400', '500', '600'],
  style: ['normal', 'italic'],
  display: 'swap',
  variable: '--font-display',
})
const dmSans = DM_Sans({
  subsets: ['latin'],
  display: 'swap',
  variable: '--font-ui',
})
const caveat = Caveat({
  subsets: ['latin'],
  weight: ['500', '600', '700'],
  display: 'swap',
  variable: '--font-hand',
})
const jetbrainsMono = JetBrains_Mono({
  subsets: ['latin'],
  weight: ['400', '500'],
  display: 'swap',
  variable: '--font-mono',
})

export const metadata: Metadata = {
  title: 'jobmore',
}

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html
      lang="en"
      className={`${newsreader.variable} ${dmSans.variable} ${caveat.variable} ${jetbrainsMono.variable}`}
    >
      <body>{children}</body>
    </html>
  )
}
