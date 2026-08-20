'use client';

import { motion } from 'framer-motion';
import { FEATURES } from '@/lib/constants';

const accentColors = {
  cyan: 'border-cyan-500/20 hover:border-cyan-500/40',
  blue: 'border-blue-500/20 hover:border-blue-500/40',
  purple: 'border-purple-500/20 hover:border-purple-500/40',
  emerald: 'border-emerald-500/20 hover:border-emerald-500/40',
} as const;

const glowColors = {
  cyan: 'group-hover:shadow-cyan-500/10',
  blue: 'group-hover:shadow-blue-500/10',
  purple: 'group-hover:shadow-purple-500/10',
  emerald: 'group-hover:shadow-emerald-500/10',
} as const;

export default function FeatureGrid() {
  return (
    <section className="relative px-6 py-24">
      <div className="max-w-6xl mx-auto">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, margin: '-100px' }}
          transition={{ duration: 0.6 }}
          className="text-center mb-16"
        >
          <h2 className="text-3xl md:text-4xl font-bold mb-4">Core Systems</h2>
          <p className="text-[var(--color-text-secondary)] max-w-xl mx-auto">
            Modular AI subsystems working in concert to deliver real-time urban intelligence.
          </p>
        </motion.div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {FEATURES.map((feature, index) => (
            <motion.div
              key={feature.title}
              initial={{ opacity: 0, y: 30 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true, margin: '-50px' }}
              transition={{ duration: 0.5, delay: index * 0.1 }}
              className="group"
            >
              <div
                className={`glass-panel rounded-2xl p-8 h-full border transition-all duration-300 group-hover:shadow-xl ${accentColors[feature.accentColor]} ${glowColors[feature.accentColor]}`}
              >
                <div className="text-4xl mb-4">{feature.icon}</div>
                <h3 className="text-xl font-semibold mb-3">{feature.title}</h3>
                <p className="text-[var(--color-text-secondary)] leading-relaxed text-sm">
                  {feature.description}
                </p>
              </div>
            </motion.div>
          ))}
        </div>
      </div>
    </section>
  );
}
