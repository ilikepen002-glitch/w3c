from provider_compare import *
p=Path(sys.argv[1]);stage=sys.argv[2];m=Mpq(p.read_bytes());s=m.extract('war3map.j').decode();o=unit_objects(m.extract('war3map.w3u'))
if stage=='costs':out=[cost(s,o,n) for n in [0,4,10,40]]
else:out=globals()[stage](s,o)
print(json.dumps({'hash':hashlib.sha256(p.read_bytes()).hexdigest(),stage:out},indent=2))
