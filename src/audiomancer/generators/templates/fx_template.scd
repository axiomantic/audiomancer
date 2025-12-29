// FX template - Noise and texture generator
SynthDef(\fx_template, {
    |out=0, freq=1000, density=10, decay=0.5, amp=0.3|
    var sig, env;

    // Percussive envelope
    env = EnvGen.kr(Env.perc(0.01, decay), doneAction: 2);

    // Dust (sparse impulses) with resonant filter
    sig = Dust.ar(density);
    sig = RLPF.ar(sig, freq, 0.1);

    // Amplitude
    sig = sig * env * amp;

    Out.ar(out, sig ! 2);
}).add;
