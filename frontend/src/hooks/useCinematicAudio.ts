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
 * Ambient-first policy (final audio polish): the soundscape attempts to
 * start immediately so a first-time visitor feels the system is alive. If
 * the browser's autoplay policy holds the context in "suspended", the hook
 * waits for the FIRST user interaction (pointer/key/touch/wheel) and resumes
 * then — no autoplay hacks, no forced playback. The SOUND ON/OFF toggle
 * remains authoritative: an explicit user opt-out is never overridden.
 */
export function useCinematicAudio() {
  const [enabled, setEnabled] = useState(false);
  const ctxRef = useRef<AudioContext | null>(null);
  const sirenGainRef = useRef<GainNode | null>(null);
  const droneGainRef = useRef<GainNode | null>(null);
  /** Set when the user explicitly opts out — ambient retry must respect it. */
  const userOptOutRef = useRef(false);

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
    userOptOutRef.current = false;
    build();
    void ctxRef.current?.resume();
    setEnabled(true);
  }, [build]);

  const disable = useCallback(() => {
    userOptOutRef.current = true; // respect the toggle against ambient retry
    if (ctxRef.current?.state === 'running') {
      ctxRef.current.suspend().catch(() => {});
    }
    setEnabled(false);
  }, []);

  /**
   * Ambient-first startup. Tries to begin immediately (some browsers allow
   * it); otherwise arms one-time first-interaction listeners and resumes
   * there — the graceful, policy-compliant path.
   */
  useEffect(() => {
    build();
    const ctx = ctxRef.current;
    if (!ctx) return;

    let settled = false;
    const GESTURES = ['pointerdown', 'keydown', 'touchstart', 'wheel'] as const;

    const settle = () => {
      if (settled) return;
      settled = true;
      for (const g of GESTURES) window.removeEventListener(g, onGesture);
    };

    const attempt = () => {
      if (userOptOutRef.current) {
        settle();
        return;
      }
      void ctx
        .resume()
        .then(() => {
          if (userOptOutRef.current) {
            // User toggled off while we were waiting — stand down.
            void ctx.suspend().catch(() => {});
            settle();
            return;
          }
          if (ctx.state === 'running') {
            setEnabled(true);
            settle(); // ambient is live — stop listening
          }
          // Still suspended: keep waiting for a genuine interaction.
        })
        .catch(() => {
          /* autoplay refused — retry on next gesture */
        });
    };

    const onGesture = () => attempt();

    attempt(); // immediate try — works when permissions allow
    for (const g of GESTURES) window.addEventListener(g, onGesture, { passive: true });

    return () => {
      settled = true;
      for (const g of GESTURES) window.removeEventListener(g, onGesture);
    };
  }, [build]);

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
