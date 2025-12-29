// Drum template - Percussive synth without gate
SynthDef(\drum_template, {
    |out=0, freq=80, decay=0.1, tone=0.5, amp=1.0|
    var sig, env;

    // Percussive envelope (no gate parameter)
    env = EnvGen.kr(Env.perc(0.001, decay), doneAction: 2);

    // Mix of sine (kick) and noise (snap)
    sig = (SinOsc.ar(freq * env) * tone) + (WhiteNoise.ar * (1 - tone));

    // Amplitude
    sig = sig * env * amp;

    Out.ar(out, sig ! 2);
}).add;
