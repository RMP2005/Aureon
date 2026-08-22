'use client';

import dynamic from 'next/dynamic';
import Navbar from '@/components/Navbar';
import HeroSection from '@/components/HeroSection';
import FeatureGrid from '@/components/FeatureGrid';
import SystemStatus from '@/components/SystemStatus';
import Footer from '@/components/Footer';

const Scene3D = dynamic(() => import('@/components/Scene3D'), {
  ssr: false,
});

export default function Home() {
  return (
    <>
      <Scene3D />
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
