// Bass template - Low-frequency synth with resonant filter
SynthDef(\bass_template, {
    |out=0, freq=55, cutoff=800, resonance=0.5, envmod=0.4,
     decay=0.3, amp=0.7, gate=1|
    var sig, env, fenv;

    // Amplitude envelope
    env = EnvGen.kr(Env.asr(0.01, 1, 0.1), gate, doneAction: 2);

    // Filter envelope
    fenv = EnvGen.kr(Env.perc(0.01, decay)) * envmod * 2000;

    // Oscillator (sawtooth for rich harmonics)
    sig = Saw.ar(freq);

    // Resonant low-pass filter
    sig = RLPF.ar(sig, (cutoff + fenv).clip(20, 5000), resonance);

    // Amplitude
    sig = sig * env * amp;

    Out.ar(out, sig ! 2);
}).add;
