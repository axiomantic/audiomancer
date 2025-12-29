// TB-303 acid bass SynthDef for testing
SynthDef(\tb303, {
    |out=0, freq=440, cutoff=1200, resonance=0.7, envmod=0.6,
     decay=0.2, accent=0, slide=0, wave=0, gate=1, amp=0.5|
    var sig, env, fenv, osc1, osc2;

    // Amplitude envelope
    env = EnvGen.kr(Env.asr(0.001, 1, 0.05), gate, doneAction: 2);

    // Filter envelope
    fenv = EnvGen.kr(Env.perc(0.001, decay)) * envmod * 4000;

    // Portamento/slide
    freq = Lag.kr(freq, slide * 0.1);

    // Oscillators
    osc1 = Saw.ar(freq);
    osc2 = Pulse.ar(freq, 0.5);
    sig = Select.ar(wave, [osc1, osc2]);

    // Moog-style filter
    sig = MoogFF.ar(sig, (cutoff + fenv).clip(20, 20000), resonance);

    // Accent and amplitude
    sig = sig * env * amp * (1 + (accent * 0.5));

    Out.ar(out, sig ! 2);
}).add;
