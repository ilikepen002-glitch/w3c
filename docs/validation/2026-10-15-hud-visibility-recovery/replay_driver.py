import sys,json
from pathlib import Path
sys.path.insert(0,'tools')
from VerifyHudProjectionReplay import read_map,summary
from VerifyCompactHudReplay import scenarios,compare_clients
root=Path('docs/validation/2026-10-15-hud-visibility-recovery')
baseline,bmeta=read_map(Path(sys.argv[1]))
try:
    scenarios(baseline,0)
except ValueError as error:
    assert str(error)=='Refresh failed to restore the selected HUD mode',str(error)
    negative={'status':'EXPECTED_FAILURE','error':str(error),'map':bmeta}
else:
    raise AssertionError('Old map was not rejected')
(root/'baseline-expected-failure.json').write_text(json.dumps(negative,ensure_ascii=False,indent=2)+'\n')
print('PASS: baseline hidden-visibility defect rejected',flush=True)
script,meta=read_map(Path('ExampleMap.w3x'))
runs={}
for local in (0,1,2,3,15):
    runs[local]=scenarios(script,local)
    print('PASS: candidate local',local,'cases',len(runs[local][0]),flush=True)
compare_clients(runs)
result={'status':'PASS','map':meta,'clients':list(runs),'cases_per_client':len(runs[0][0]),'handle_skeletons_equal':True,'cases':{name:summary(snapshot) for name,snapshot in runs[0][0].items()},'boundary':'Actual candidate packed JASS; modeled native multiboard rendering and game fixtures. No Warcraft 1.27a render or network test.'}
(root/'candidate-replay.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
print('PASS: all five clients retain identical synchronized handle traces',flush=True)
