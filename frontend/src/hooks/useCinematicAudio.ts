'use client';

import { useCallback, useEffect, useRef, useState } from 'react';

/**
 * Procedural cinematic audio (Phase 10C) — no binary assets.
 *
 * Two layers synthesized with WebAudio (original Aureon identity):
 *   - city drone: detuned low oscillators through a lowpass, always present
 *     once sound is enabled
 *   - response siren: a distant two-tone wail whose level tracks the
 *     "pulse" act intensity fed in from scroll progress
 *
 * IDENTITY NOTE: the synthesis is the ORIGINAL Phase 10C design — same
 * oscillators, same detune, same 220Hz lowpass darkness, same siren. Only
 * frequency balance (a touch more energy at the drone's own octave for
 * small-speaker compatibility) and loudness normalization differ from the
 * first revision, so the mix reads as "the same Aureon audio, reliably
 * audible" rather than a new soundtrack.
 *
 * Ambient-first policy: playback starts as soon as the browser allows it;
 * if autoplay is blocked it resumes gracefully on first user interaction.
 *
 * Playback reliability contract:
 *   - every resume() is VERIFIED against ctx.state (never fire-and-forget)
 *   - ctx.onstatechange keeps the toggle honest with reality
 *   - SOUND OFF hard-mutes the master instantly, THEN suspends
 *   - SOUND ON schedules a fresh master fade every time, so repeated
 *     OFF→ON→OFF→ON always produces audio
 *   - AUDIO_DEBUG (dev builds) logs the full signal path and exposes
 *     window.__aureonAudioCtx / __aureonAudioMaster for live inspection
 */

const AUDIO_DEBUG = process.env.NODE_ENV !== 'production';

export function useCinematicAudio() {
  const [enabled, setEnabled] = useState(false);
  const ctxRef = useRef<AudioContext | null>(null);
  const sirenGainRef = useRef<GainNode | null>(null);
  const droneGainRef = useRef<GainNode | null>(null);
  const masterRef = useRef<GainNode | null>(null);
  /** Set when the user explicitly opts out — ambient retry must respect it. */
  const userOptOutRef = useRef(false);

  const log = useCallback((...args: unknown[]) => {
    if (AUDIO_DEBUG) console.log('[aureon-audio]', ...args);
  }, []);

  const build = useCallback(() => {
    const Ctx =
      window.AudioContext ??
      (window as unknown as { webkitAudioContext?: typeof AudioContext }).webkitAudioContext;
    if (!Ctx) {
      log('no WebAudio support');
      return;
    }
    if (ctxRef.current) {
      log('context already built, state =', ctxRef.current.state);
      return;
    }

    const ctx = new Ctx();
    log('AudioContext created, initial state =', ctx.state, 'sampleRate =', ctx.sampleRate);

    const master = ctx.createGain();
    // Start fully muted; every activation schedules its own fade-in.
    master.gain.setValueAtTime(0, ctx.currentTime);
    master.connect(ctx.destination);

    // --- City drone (original oscillator set & character) ---------------
    const droneGain = ctx.createGain();
    // Loudness normalization only: 0.05 → 0.14 so the ORIGINAL drone is
    // audible on real speakers while staying subtle room tone.
    droneGain.gain.value = 0.14;
    const lp = ctx.createBiquadFilter();
    lp.type = 'lowpass';
    lp.frequency.value = 220; // original darkness — unchanged
    lp.Q.value = 0.4;
    droneGain.connect(lp).connect(master);

    for (const [freq, detune, g] of [
      [48, -6, 0.5],
      [48.7, 5, 0.5],
      [96, 0, 0.3], // speaker compatibility: the drone's own octave lifted
    ] as const) {
      const osc = ctx.createOscillator();
      osc.type = 'sine';
      osc.frequency.value = freq;
      osc.detune.value = detune;
      const gain = ctx.createGain();
      gain.gain.value = g;
      osc.connect(gain).connect(droneGain);
      osc.start();
      log('drone oscillator started:', freq, 'Hz');
    }

    // --- Distant siren (two-tone wail via LFO on frequency) -------------
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
    lfo.frequency.value = 0.16;
    const lfoDepth = ctx.createGain();
    lfoDepth.gain.value = 190;
    lfo.connect(lfoDepth).connect(wail.frequency);
    wail.connect(sirenGain);
    wail.start();
    lfo.start();
    log('siren oscillators started');

    ctxRef.current = ctx;
    droneGainRef.current = droneGain;
    sirenGainRef.current = sirenGain;
    masterRef.current = master;

    // Keep the toggle honest: mirror the REAL context state.
    ctx.onstatechange = () => {
      log('state change →', ctx.state);
      if (ctx.state === 'running' && !userOptOutRef.current) setEnabled(true);
    };

    if (AUDIO_DEBUG) {
      const w = window as unknown as {
        __aureonAudioCtx?: AudioContext;
        __aureonAudioMaster?: GainNode;
      };
      w.__aureonAudioCtx = ctx;
      w.__aureonAudioMaster = master;
    }
  }, [log]);

  /** Fresh master fade-in — scheduled per activation, not once at build. */
  const fadeUp = useCallback(() => {
    const ctx = ctxRef.current;
    const master = masterRef.current;
    if (!ctx || !master) return;
    const t = ctx.currentTime;
    master.gain.cancelScheduledValues(t);
    master.gain.setValueAtTime(master.gain.value, t);
    master.gain.setTargetAtTime(0.62, t + 0.05, 0.9);
    log('master fade scheduled → 0.62 from', master.gain.value);
  }, [log]);

  const enable = useCallback(() => {
    userOptOutRef.current = false;
    build();
    const ctx = ctxRef.current;
    if (!ctx) return;

    if (ctx.state === 'suspended') {
      void ctx
        .resume()
        .then(() => {
          log('resume() resolved, state =', ctx.state);
          if (ctx.state === 'running') {
            fadeUp();
            setEnabled(true);
          } else {
            log('still suspended after resume — browser withheld activation');
          }
        })
        .catch((e) => log('resume() rejected:', e));
    } else {
      log('context already', ctx.state);
      fadeUp();
      setEnabled(true);
    }
  }, [build, fadeUp, log]);

  const disable = useCallback(() => {
    userOptOutRef.current = true; // respect the toggle against ambient retry
    const ctx = ctxRef.current;
    const master = masterRef.current;
    if (ctx && master) {
      // Hard-mute FIRST (instant silence), then suspend the render quantum.
      const t = ctx.currentTime;
      master.gain.cancelScheduledValues(t);
      master.gain.setValueAtTime(master.gain.value, t);
      master.gain.linearRampToValueAtTime(0, t + 0.08);
      if (ctx.state === 'running') ctx.suspend().catch(() => {});
      log('muted + suspended');
    }
    setEnabled(false);
  }, [log]);

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
          log('ambient resume attempt, state =', ctx.state);
          if (userOptOutRef.current) {
            void ctx.suspend().catch(() => {});
            settle();
            return;
          }
          if (ctx.state === 'running') {
            fadeUp();
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
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [build]);

  useEffect(() => () => void ctxRef.current?.close().catch(() => {}), []);

  /** Called from scroll updates — smooth, allocation-free. */
  const setIntensity = useCallback(
    (level: number) => {
      const ctx = ctxRef.current;
      const siren = sirenGainRef.current;
      if (!ctx || !siren || ctx.state !== 'running') return;
      const target = Math.max(0, level) * 0.035;
      siren.gain.setTargetAtTime(target, ctx.currentTime, 0.6);
    },
    [],
  );

  return { enabled, enable, disable, setIntensity };
}
