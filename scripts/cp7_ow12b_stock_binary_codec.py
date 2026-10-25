"""Independent test codec for the PG17 binary reference; no database access."""
from datetime import datetime,timezone
from hashlib import sha256
from struct import pack,unpack
from uuid import UUID

# Independently declared test layout. Never import the producer's serializer.
FIELDS=(('id',2950),('root_id',2950),('size_id',2950),('product_id',2950),
 ('lot_id',2950),('location_id',2950),('quality_grade',17),('qty_signed',17),
 ('physical_at',1184),('system_created_at',1184),('movement_type',17),
 ('source_type',17),('source_id',2950),('reversal_of_id',2950),('book_order',20))
EPOCH=datetime(2000,1,1,tzinfo=timezone.utc)
MIN64,MAX64=-(1<<63),(1<<63)-1


def timestamp(value):
 if value in('-infinity','infinity'):return MIN64 if value=='-infinity'else MAX64
 dt=datetime.fromisoformat(value.replace('Z','+00:00'))
 assert dt.tzinfo is not None
 delta=dt.astimezone(timezone.utc)-EPOCH
 return (delta.days*86400+delta.seconds)*1000000+delta.microseconds


def encode(values):
 assert set(values)=={k for k,_ in FIELDS},'BINARY_TEST_NATIVE_FIELD_SET_CHANGED'
 parts=[pack('!i',len(FIELDS))]
 for name,oid in FIELDS:
  value=values[name];parts.append(pack('!I',oid))
  if value is None:parts.append(pack('!i',-1));continue
  if oid==2950:raw=UUID(str(value)).bytes
  elif oid==17:raw=str(value).encode('utf8')
  elif oid==1184:raw=pack('!q',timestamp(value))
  else:raw=pack('!q',int(value))
  parts.extend((pack('!i',len(raw)),raw))
 return b''.join(parts)


def decode(data):
 view=memoryview(data);pos=0
 def take(n):
  nonlocal pos
  assert n>=0 and pos+n<=len(view),'BINARY_TEST_TRUNCATED_FRAME'
  answer=view[pos:pos+n].tobytes();pos+=n;return answer
 assert unpack('!i',take(4))[0]==15
 answer={}
 for name,oid in FIELDS:
  assert unpack('!I',take(4))[0]==oid
  size=unpack('!i',take(4))[0];assert size>=-1
  if size==-1:answer[name]=None;continue
  raw=take(size)
  if oid==2950:assert len(raw)==16;value=str(UUID(bytes=raw))
  elif oid==17:value=raw.decode('utf8',errors='strict')
  else:
   assert len(raw)==8;value=unpack('!q',raw)[0]
  answer[name]=value
 assert pos==len(view),'BINARY_TEST_TRAILING_FRAME_BYTES'
 return answer


def expected_values(row):
 return {name:None if row[name]is None else timestamp(row[name])if oid==1184
  else int(row[name])if oid==20 else str(row[name])for name,oid in FIELDS}


def digest(rows,contract,encoding,layout):
 ordered=sorted(rows,key=lambda r:UUID(r['id']).bytes)
 frames='\n'.join(sha256(encode(r)).hexdigest()for r in ordered)
 domain=contract+'\n'+encoding+'\n'+layout+'\n'+str(len(rows))+'\n'+frames
 return str(len(rows)),sha256(domain.encode('utf8')).hexdigest()
