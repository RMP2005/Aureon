import type { Metadata } from 'next';
import './globals.css';

export const metadata: Metadata = {
  title: 'Aureon — AI-Powered Urban Intelligence',
  description: 'Digital twin platform for real-time city simulation, predictive analytics, and emergency response optimization.',
  keywords: ['digital twin', 'AI', 'simulation', 'urban intelligence', 'emergency response'],
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className="dark">
      <body className="min-h-screen bg-[var(--color-bg-primary)] text-[var(--color-text-primary)] antialiased">
        {children}
      </body>
    </html>
  );
}
