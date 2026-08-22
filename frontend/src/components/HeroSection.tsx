'use client';

import { motion } from 'framer-motion';
import Link from 'next/link';

const metrics = [
  { label: 'Active Simulations', value: '—', status: 'standby' },
  { label: 'AI Models Loaded', value: '—', status: 'standby' },
  { label: 'System Latency', value: '—', status: 'standby' },
];

export default function HeroSection() {
  return (
    <section className="relative min-h-screen flex items-center justify-center px-6">
      {/* Background gradient orbs */}
      <div className="absolute inset-0 overflow-hidden pointer-events-none">
        <div className="absolute top-1/4 left-1/4 w-96 h-96 bg-cyan-500/10 rounded-full blur-3xl" />
        <div className="absolute bottom-1/4 right-1/4 w-96 h-96 bg-purple-500/10 rounded-full blur-3xl" />
        <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[600px] h-[600px] bg-blue-500/5 rounded-full blur-3xl" />
      </div>

      <div className="relative z-10 max-w-5xl mx-auto text-center">
        {/* System status badge */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, delay: 0.2 }}
          className="inline-flex items-center gap-2 px-4 py-2 rounded-full glass-panel mb-8"
        >
          <div className="h-2 w-2 rounded-full bg-cyan-400 animate-pulse" />
          <span className="text-xs text-[var(--color-text-secondary)] tracking-widest uppercase">Aureon Command System v0.1</span>
        </motion.div>

        {/* Main heading */}
        <motion.h1
          initial={{ opacity: 0, y: 30 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.7, delay: 0.3 }}
          className="text-5xl md:text-7xl font-bold tracking-tight leading-tight mb-6"
        >
          <span className="text-gradient">Intelligent</span>
          <br />
          Urban Command
        </motion.h1>

        {/* Subtitle */}
        <motion.p
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6, delay: 0.5 }}
          className="text-lg md:text-xl text-[var(--color-text-secondary)] max-w-2xl mx-auto mb-12 leading-relaxed"
        >
          AI-powered digital twin platform for real-time city simulation,
          predictive analytics, and emergency response optimization.
        </motion.p>

        {/* CTA buttons */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6, delay: 0.7 }}
          className="flex flex-col sm:flex-row items-center justify-center gap-4 mb-16"
        >
          <Link href="/dashboard" className="px-8 py-3 rounded-xl bg-gradient-to-r from-cyan-500 to-blue-600 text-white font-medium hover:shadow-lg hover:shadow-cyan-500/25 transition-all duration-300 inline-block">
            Launch Dashboard
          </Link>
          <Link href="/simulation" className="px-8 py-3 rounded-xl glass-panel text-[var(--color-text-secondary)] hover:text-[var(--color-text-primary)] transition-all duration-300 inline-block">
            Run Simulation
          </Link>
        </motion.div>

        {/* Status metrics */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6, delay: 0.9 }}
          className="grid grid-cols-1 sm:grid-cols-3 gap-4 max-w-2xl mx-auto"
        >
          {metrics.map((metric) => (
            <div key={metric.label} className="glass-panel rounded-xl px-6 py-4 text-center">
              <p className="text-2xl font-semibold text-[var(--color-text-primary)] mb-1">{metric.value}</p>
              <p className="text-xs text-[var(--color-text-muted)] uppercase tracking-wider">{metric.label}</p>
            </div>
          ))}
        </motion.div>
      </div>
    </section>
  );
}
