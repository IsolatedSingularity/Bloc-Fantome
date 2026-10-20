// Native, finite offline score. Long field recordings are read continuously;
// no repeating Minecraft clip or Python synthesis supplies the sound bed.
(
var root = "@WORK@", sources = @SOURCES@, score, defs, duration = @DURATION@;
var add = { |time, message| score.add([time, message]) };
defs = [
    SynthDef(\material, { |out=0, buf=0, amp=0.2, rate=0.65, start=0, dur=10, cutoff=700, pan=0|
        var source=PlayBuf.ar(2,buf,BufRateScale.kr(buf)*rate,1,start*BufSampleRate.kr(buf),0);
        var envelope=EnvGen.kr(Env.linen(0.6,dur.max(1)-1,0.4),doneAction:2);
        var grain=LPF.ar(HPF.ar(source,32),cutoff);
        var cavity=CombC.ar(grain,0.3,[0.071,0.093],1.7)*0.16;
        Out.ar(out,Balance2.ar(grain[0]+cavity[0],grain[1]+cavity[1],pan,amp*envelope));
    }),
    SynthDef(\buriedVoice, { |out=0,buf=0,amp=0.3,rate=0.7,dur=5,pan=0,cutoff=600|
        var source=PlayBuf.ar(2,buf,BufRateScale.kr(buf)*rate,1,0,0);
        var env=EnvGen.kr(Env.linen(0.24,dur.max(0.6)-0.55,0.31),doneAction:2);
        var throat=HPF.ar(Mix(source)*0.5,100);
        var sealed=LPF.ar(throat,cutoff*(1+SinOsc.kr(0.37,pan*3,0.24)));
        var room=FreeVerb2.ar(sealed,DelayC.ar(sealed,0.15,0.037),0.28,0.87,0.72);
        Out.ar(out,Balance2.ar(room[0],room[1],pan+SinOsc.kr(0.19,pan,0.15),amp*env));
    }),
    SynthDef(\contact, { |out=0,buf=0,amp=0.2,rate=0.5,start=0,pan=0,dur=1.4|
        var source=PlayBuf.ar(2,buf,BufRateScale.kr(buf)*rate,1,start*BufSampleRate.kr(buf),0);
        var envelope=EnvGen.kr(Env.perc(0.015,dur,1,-5),doneAction:2);
        var sound=LPF.ar(source,900)+BPF.ar(source,85,0.7)*0.6;
        Out.ar(out,Balance2.ar(sound[0],sound[1],pan,amp*envelope));
    })
];
score=List.new;
defs.do({|definition| add.value(0,[\d_recv,definition.asBytes])});
sources.do({|path,index|add.value(0,[\b_allocRead,index,path])});
@EVENTS@
add.value(duration,[\c_set,0,0]);
Score(score.sort({|a,b|a[0]<b[0]})).write(root++"/score.osc");
0.exit;
)
