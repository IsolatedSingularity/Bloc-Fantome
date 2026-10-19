// SuperCollider 3.14.1 NRT. Recorded Minecraft material excites the resonators.
// Paths and cue are supplied by render_opening_audio.py; no real-time server.
(
var score, orbit, rise;
Archive.archiveDir = "@WORK@";
orbit = SynthDef(\orbitBed, {
    var air, stone, body;
    RandSeed.ir(1, 296);
    air = PlayBuf.ar(2, 0, BufRateScale.kr(0)*0.63, loop:1);
    stone = PlayBuf.ar(2, 1, BufRateScale.kr(1)*0.31, loop:1);
    body = LPF.ar(HPF.ar(air, 160), 1800)*0.6;
    body = body + BPF.ar(stone, [320, 470], 0.3)*0.8;
    body = body + AllpassC.ar(body, 0.2, [0.071, 0.097], 1.4)*0.25;
    Out.ar(0, Limiter.ar(LeakDC.ar(body)*2.5, 0.8));
});
rise = SynthDef(\sanctuaryRise, {
    var stone, air, weight, ribs, body, env;
    RandSeed.ir(1, 296);
    stone = PlayBuf.ar(2, 1, BufRateScale.kr(1)*[0.19,0.23], loop:1).sum*0.5;
    air = PlayBuf.ar(2, 0, BufRateScale.kr(0)*0.27, loop:1);
    weight = Mix(BPF.ar(stone, [29,43,61,87], [0.15,0.2,0.3,0.3], [8,5,3,2]));
    ribs = Mix(Ringz.ar(LPF.ar(stone, 220), [34,51,76,114], [0.7,0.5,0.3,0.2], [0.1,0.08,0.05,0.025]));
    body = (weight + ribs).tanh*0.6 + LPF.ar(stone, 380)*0.35 + LPF.ar(air, 260)*0.2;
    body = body + CombC.ar(body, 0.3, [0.127,0.183], 1.8)*0.18;
    env = EnvGen.kr(Env([0,0.85,1,0.65,0], [0.55,2.1,1.35,1.4], [-3,1,-1,-4]));
    Out.ar(0, Limiter.ar(LeakDC.ar(body)*env*2, 0.85));
});
score = Score([
    [0, [\d_recv, orbit.asBytes]], [0, [\d_recv, rise.asBytes]],
    [0, [\b_allocRead, 0, "@AIR@"]],
    [0, [\b_allocRead, 1, "@STONE@"]],
    [0.05, [\s_new, \@CUE@, 1000, 0, 0]],
    [@DURATION@, [\g_freeAll, 0]]
]);
score.writeOSCFile("@SCORE@", 0, @DURATION@);
"SCORE_WRITTEN".postln;
0.exit;
)
