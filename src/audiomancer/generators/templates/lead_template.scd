// Lead template - Bright melodic synth with envelope
SynthDef(\lead_template, {
    |out=0, freq=440, cutoff=2000, resonance=0.3, attack=0.01,
     decay=0.2, sustain=0.7, release=0.3, amp=0.5, gate=1|
    var sig, env;

    // ADSR envelope
    env = EnvGen.kr(
        Env.adsr(attack, decay, sustain, release),
        gate,
        doneAction: 2
    );

    // Pulse wave oscillator with variable width
    sig = Pulse.ar(freq, 0.5);

    // Bright filter
    sig = LPF.ar(sig, cutoff * env);

    // Amplitude
    sig = sig * env * amp;

    Out.ar(out, sig ! 2);
}).add;
