import './globals.css';
import type { Metadata } from 'next';

export const metadata: Metadata = {
  title: 'بنّا | Banna',
  description: 'AI renovation planning and execution copilot for Iran',
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="fa" dir="rtl">
      <body>{children}</body>
    </html>
  );
}
