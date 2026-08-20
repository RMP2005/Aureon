import { type NavItem, type FeatureCard } from '@/types';

export const NAV_ITEMS: NavItem[] = [
  { label: 'Dashboard', href: '/dashboard' },
  { label: 'Simulation', href: '/simulation' },
  { label: 'Analytics', href: '/analytics' },
  { label: 'Models', href: '/models' },
];

export const FEATURES: FeatureCard[] = [
  {
    title: 'Digital Twin Simulation',
    description: 'High-fidelity city simulation with real-time physics, weather systems, and infrastructure modeling.',
    icon: '🌐',
    accentColor: 'cyan',
  },
  {
    title: 'AI Event Classification',
    description: 'Neural network-powered event detection and classification across urban environments.',
    icon: '🧠',
    accentColor: 'blue',
  },
  {
    title: 'Predictive Analytics',
    description: 'Time-series forecasting and anomaly detection for proactive emergency response.',
    icon: '📊',
    accentColor: 'purple',
  },
  {
    title: 'Response Optimization',
    description: 'Resource allocation and routing optimization for emergency management.',
    icon: '⚡',
    accentColor: 'emerald',
  },
];

export const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000/api/v1';
export const WS_BASE_URL = process.env.NEXT_PUBLIC_WS_URL ?? 'ws://localhost:8000/ws';
