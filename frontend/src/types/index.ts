export interface NavItem {
  label: string;
  href: string;
}

export interface FeatureCard {
  title: string;
  description: string;
  icon: string;
  accentColor: 'cyan' | 'blue' | 'purple' | 'emerald';
}

export interface SystemMetric {
  label: string;
  value: string;
  trend: 'up' | 'down' | 'stable';
  unit?: string;
}
