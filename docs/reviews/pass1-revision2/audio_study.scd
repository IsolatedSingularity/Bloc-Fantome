(
var root="@WORK@",sources=@SOURCES@,score=List.new,add,defs;
add={|t,msg|score.add([t,msg])};
defs=[SynthDef(\mass,{|buf=0,amp=1,rate=1,start=0,dur=1,attack=0.1,release=0.5,lo=30,hi=2500,pan=0,wet=0.4,resonance=0|
 var raw=PlayBuf.ar(2,buf,BufRateScale.kr(buf)*rate,1,start*BufSampleRate.kr(buf),0);
 var env=EnvGen.kr(Env.linen(attack,(dur-attack-release).max(0.01),release),doneAction:2);
 var filtered=LPF.ar(HPF.ar(raw,lo),hi);
 // Recorded excitation only. Broad resonances make a space, not a tonal alarm.
 var resonant=(BPF.ar(filtered,49,0.2)*1.5)+(BPF.ar(filtered,73.4,0.22)*1.2)+(BPF.ar(filtered,146.8,0.25)*0.7);
 var body=(filtered+(resonant*resonance))*amp;
 var controlled=Compander.ar(body,body,0.13,1,0.35,0.035,0.35)*env;
 var early=(DelayC.ar(controlled,0.6,[0.113,0.173])*0.27)+(DelayC.ar(controlled,0.6,[0.281,0.397])*0.18);
 var late=FreeVerb2.ar(controlled[0],controlled[1],1,0.93,0.65);
 var mixed=controlled+((early+(late*0.5))*wet);
 Out.ar(0,Balance2.ar(mixed[0],mixed[1],pan));
})];
defs.do({|d|add.value(0,[\d_recv,d.asBytes])});
sources.do({|path,i|add.value(0,[\b_allocRead,i,path])});
@EVENTS@
add.value(16,[\c_set,0,0]);
Score(score.sort({|a,b|a[0]<b[0]})).write(root++"/score.osc");
0.exit;
)
