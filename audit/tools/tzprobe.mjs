// Reproduce the candidate's serialization expressions vs the WIB helper, per device timezone.
const value='2026-09-20T00:30';
const legacy=new Date(value).toISOString();               // ConnectedCuttingPage:272, ConnectedPickupPage:200, ConnectedBsResolutionPage:40
const m=/^(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2})$/.exec(value);
const wib=new Date(`${m[1]}-${m[2]}-${m[3]}T${m[4]}:${m[5]}:00+07:00`).toISOString(); // cp6BusinessTime.ts:16-25
console.log(JSON.stringify({TZ:process.env.TZ,input:value,legacy_expr:legacy,wib_helper:wib,equal:legacy===wib}));
