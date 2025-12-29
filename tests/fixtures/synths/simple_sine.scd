// Simple sine wave SynthDef for testing
SynthDef(\simple_sine, {
    |out=0, freq=440, amp=0.5, gate=1|
    var sig, env;
    env = EnvGen.kr(Env.asr(0.01, 1, 0.1), gate, doneAction: 2);
    sig = SinOsc.ar(freq) * amp * env;
    Out.ar(out, sig ! 2);
}).add;
