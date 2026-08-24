'use client';

import { useRef } from 'react';
import * as THREE from 'three';
import { useFrame } from '@react-three/fiber';
import { getLiveBuffer } from '@/lib/twin/live-buffer';

const MAX_INCIDENTS = 48;

/**
 * Active incident beacons (Phase 11H).
 *
 * Every incident renders as marker + ring — never a bare circle:
 *   red core beacon      → the emergency site itself
 *   crit-red ground ring → its urgency, breathing with the scene heartbeat
 *
 * Severity reads through size: critical rings run visibly wider than
 * minor ones. Rhythm and scale carry urgency; nothing else is added.
 */
const SEVERITY_SCALE: Record<string, number> = {
  critical: 1.45,
  major: 1.25,
  high: 1.15,
  moderate: 0.95,
  medium: 0.95,
  minor: 0.8,
  low: 0.7,
};

function severityScale(sev: string): number {
  return SEVERITY_SCALE[sev.toLowerCase()] ?? 1;
}

export default function Incidents() {
  const ringRef = useRef<THREE.InstancedMesh>(null);
  const coreRef = useRef<THREE.InstancedMesh>(null);

  const workMatrix = useRef(new THREE.Matrix4());
  const hideMatrix = useRef(
    new THREE.Matrix4().makeTranslation(0, -10, 0).scale(new THREE.Vector3(0.0001, 0.0001, 0.0001)),
  );
  const workQuat = useRef(new THREE.Quaternion().setFromAxisAngle(
    new THREE.Vector3(1, 0, 0),
    -Math.PI / 2,
  ));
  const identityQuat = useRef(new THREE.Quaternion());
  const workPos = useRef(new THREE.Vector3());
  const workScale = useRef(new THREE.Vector3());

  useFrame(({ clock }) => {
    const ring = ringRef.current;
    const core = coreRef.current;
    if (!ring || !core) return;

    const { incidents } = getLiveBuffer();
    const pulse = 1 + 0.14 * Math.sin(clock.elapsedTime * 2.4);

    let i = 0;
    for (const inc of incidents) {
      if (i >= MAX_INCIDENTS) break;
      const s = pulse * severityScale(inc.severity);

      workPos.current.set(inc.x, 0.12, inc.z);
      workScale.current.setScalar(s);
      workMatrix.current.compose(workPos.current, workQuat.current, workScale.current);
      ring.setMatrixAt(i, workMatrix.current);

      // Core sits under the ring — the actual emergency location.
      workPos.current.set(inc.x, 0.5, inc.z);
      workScale.current.setScalar(0.55 * severityScale(inc.severity));
      workMatrix.current.compose(workPos.current, identityQuat.current, workScale.current);
      core.setMatrixAt(i, workMatrix.current);

      i += 1;
    }
    for (; i < MAX_INCIDENTS; i++) {
      ring.setMatrixAt(i, hideMatrix.current);
      core.setMatrixAt(i, hideMatrix.current);
    }
    ring.instanceMatrix.needsUpdate = true;
    core.instanceMatrix.needsUpdate = true;
  });

  return (
    <>
      <instancedMesh ref={ringRef} args={[undefined, undefined, MAX_INCIDENTS]} frustumCulled={false}>
        <ringGeometry args={[0.85, 1.15, 40]} />
        <meshBasicMaterial color="#FF3655" transparent opacity={0.75} side={THREE.DoubleSide} depthWrite={false} />
      </instancedMesh>
      <instancedMesh ref={coreRef} args={[undefined, undefined, MAX_INCIDENTS]} frustumCulled={false}>
        <sphereGeometry args={[0.34, 16, 12]} />
        <meshBasicMaterial color="#FF3655" toneMapped={false} />
      </instancedMesh>
    </>
  );
}
