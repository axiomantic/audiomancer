// Pad template - Sustained atmospheric synth
SynthDef(\pad_template, {
    |out=0, freq=220, cutoff=1500, attack=0.5, release=1.0,
     detune=0.02, amp=0.4, gate=1|
    var sig, env, osc1, osc2;

    // Long ASR envelope for pads
    env = EnvGen.kr(Env.asr(attack, 1, release), gate, doneAction: 2);

    // Detuned oscillators for thickness
    osc1 = Saw.ar(freq);
    osc2 = Saw.ar(freq * (1 + detune));
    sig = (osc1 + osc2) * 0.5;

    // Soft filter
    sig = LPF.ar(sig, cutoff * env);

    // Amplitude
    sig = sig * env * amp;

    Out.ar(out, sig ! 2);
}).add;
