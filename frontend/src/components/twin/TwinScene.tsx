'use client';

import CityRoads from './CityRoads';
import { HospitalMarkers, StationMarkers } from './CityMarkers';
import Ambulances from './Ambulances';
import Incidents from './Incidents';
import IncidentLabels from './IncidentLabels';
import RouteFlowLayer from './RouteFlowLayer';
import SelectionHighlight from './SelectionHighlight';
import CameraRig from './CameraRig';
import StatsProbe, { type TwinPerfStats } from './StatsProbe';

/**
 * Twin scene composition (Phase 10B).
 *
 * The city floats in the void — no ground plane, no grid, no chrome.
 * Lighting is moonlight-neutral: the network reads as luminous structure,
 * and every colored element is a live entity or clinical infrastructure.
 */
export default function TwinScene({
  onStats,
}: {
  onStats?: (stats: TwinPerfStats) => void;
}) {
  return (
    <>
      <color attach="background" args={['#05070D']} />
      <fog attach="fog" args={['#05070D', 150, 340]} />

      {/* Moonlight — neutral steel, no color cast on the network */}
      <hemisphereLight args={['#1a2436', '#05070D', 0.5]} />
      <directionalLight position={[40, 80, 20]} intensity={0.55} color="#c9d6ea" />
      <ambientLight intensity={0.12} />

      <CameraRig />

      <CityRoads />
      <HospitalMarkers />
      <StationMarkers />

      {/* Ambient movement — the streets always carry traffic */}
      <RouteFlowLayer />

      {/* Live layers */}
      <Ambulances />
      <Incidents />
      <IncidentLabels />
      <SelectionHighlight />

      {onStats && <StatsProbe onStats={onStats} />}
    </>
  );
}
