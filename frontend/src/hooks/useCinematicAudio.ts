'use client';

import { useCallback, useEffect, useRef, useState } from 'react';

/**
 * Procedural cinematic audio (Phase 10C) — no binary assets.
 *
 * Two layers synthesized with WebAudio:
 *   - city drone: detuned low oscillators through a lowpass, always present
 *     once sound is enabled
 *   - response siren: a distant two-tone wail whose level tracks the
 *     "pulse" act intensity fed in from scroll progress
 *
 * The AudioContext is created lazily on first user opt-in (autoplay policy)
 * and everything routes through a master gain for clean teardown.
 */
export function useCinematicAudio() {
  const [enabled, setEnabled] = useState(false);
  const ctxRef = useRef<AudioContext | null>(null);
  const sirenGainRef = useRef<GainNode | null>(null);
  const droneGainRef = useRef<GainNode | null>(null);

  const build = useCallback(() => {
    const Ctx = window.AudioContext ?? (window as unknown as { webkitAudioContext?: typeof AudioContext }).webkitAudioContext;
    if (!Ctx || ctxRef.current) return;

    const ctx = new Ctx();
    const master = ctx.createGain();
    master.gain.value = 0;
    master.connect(ctx.destination);

    // --- City drone ---------------------------------------------------
    const droneGain = ctx.createGain();
    droneGain.gain.value = 0.05;
    const lp = ctx.createBiquadFilter();
    lp.type = 'lowpass';
    lp.frequency.value = 220;
    lp.Q.value = 0.4;
    droneGain.connect(lp).connect(master);

    for (const [freq, detune] of [
      [48, -6],
      [48.7, 5],
      [96, 0],
    ] as const) {
      const osc = ctx.createOscillator();
      osc.type = 'sine';
      osc.frequency.value = freq;
      osc.detune.value = detune;
      const g = ctx.createGain();
      g.gain.value = freq > 60 ? 0.12 : 0.5;
      osc.connect(g).connect(droneGain);
      osc.start();
    }

    // --- Distant siren (two-tone wail via LFO on frequency) ------------
    const sirenGain = ctx.createGain();
    sirenGain.gain.value = 0; // silent until the pulse act
    const bp = ctx.createBiquadFilter();
    bp.type = 'bandpass';
    bp.frequency.value = 750;
    bp.Q.value = 2.2;
    sirenGain.connect(bp).connect(master);

    const wail = ctx.createOscillator();
    wail.type = 'sine';
    wail.frequency.value = 700;
    const lfo = ctx.createOscillator();
    lfo.type = 'triangle';
    lfo.frequency.value = 0.16; // slow wail sweep
    const lfoDepth = ctx.createGain();
    lfoDepth.gain.value = 190;
    lfo.connect(lfoDepth).connect(wail.frequency);
    wail.connect(sirenGain);
    wail.start();
    lfo.start();

    // Fade master in gently
    master.gain.setTargetAtTime(0.55, ctx.currentTime + 0.1, 1.4);

    ctxRef.current = ctx;
    droneGainRef.current = droneGain;
    sirenGainRef.current = sirenGain;
  }, []);

  const enable = useCallback(() => {
    build();
    void ctxRef.current?.resume();
    setEnabled(true);
  }, [build]);

  const disable = useCallback(() => {
    if (ctxRef.current?.state === 'running') {
      ctxRef.current.suspend().catch(() => {});
    }
    setEnabled(false);
  }, []);

  /** Called from scroll updates — smooth, allocation-free. */
  const setIntensity = useCallback((level: number) => {
    const ctx = ctxRef.current;
    const siren = sirenGainRef.current;
    if (!ctx || !siren || ctx.state !== 'running') return;
    // Peak during pulse act (~0.55 progress), receding afterwards.
    const target = Math.max(0, level) * 0.035;
    siren.gain.setTargetAtTime(target, ctx.currentTime, 0.6);
  }, []);

  useEffect(() => () => void ctxRef.current?.close().catch(() => {}), []);

  return { enabled, enable, disable, setIntensity };
}
