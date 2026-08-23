'use client';

import Navbar from '@/components/Navbar';
import HeroSection from '@/components/HeroSection';
import FeatureGrid from '@/components/FeatureGrid';
import SystemStatus from '@/components/SystemStatus';
import Footer from '@/components/Footer';

// Scene3D removed in Phase 10A — decorative sphere superseded by the
// real digital twin (blueprint §5). Landing cinematic arrives in 10C.

export default function Home() {
  return (
    <>
      <Navbar />
      <main>
        <HeroSection />
        <FeatureGrid />
        <SystemStatus />
      </main>
      <Footer />
    </>
  );
}
